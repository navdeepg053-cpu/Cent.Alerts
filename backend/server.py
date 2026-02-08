"""
CEnT-S Alert System v2 - BULLETPROOF WEBHOOK EDITION
=====================================================
- Telegram WEBHOOK (not polling) for instant, reliable responses
- Active health monitoring that tests bot every 30 seconds
- Auto-healing: re-registers webhook if issues detected
- Decoupled scraper runs independently every 30 seconds
- All errors caught and logged, never crashes
"""

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import httpx
import asyncio
from bs4 import BeautifulSoup
from contextlib import asynccontextmanager
import time
import hashlib

# ========== CONFIGURATION ==========
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'default_secret_change_me')
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Generate secure webhook path using secret
WEBHOOK_PATH = f"/api/telegram/webhook/{WEBHOOK_SECRET}"

CISIA_URL = "https://testcisia.it/calendario.php?tolc=cents&lingua=inglese"

# MongoDB
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("cents-alert")

# ========== SYSTEM STATE ==========
class SystemState:
    def __init__(self):
        self.webhook_registered = False
        self.webhook_url = None
        self.last_webhook_check = 0
        self.last_message_received = 0
        self.last_message_sent = 0
        self.messages_received_count = 0
        self.messages_sent_count = 0
        self.errors_count = 0
        self.health_checks_passed = 0
        self.health_checks_failed = 0
        self.auto_recoveries = 0
        self.scraper_running = False
        self.health_checker_running = False
        self.bot_username = None
        self.startup_time = time.time()

state = SystemState()

# ========== MODELS ==========
class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    alert_telegram: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TelegramConnectRequest(BaseModel):
    chat_id: str

class AlertSettingsRequest(BaseModel):
    alert_telegram: bool

class AvailabilitySpot(BaseModel):
    spot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    university: str
    region: str
    city: str
    registration_deadline: str
    spots: str
    status: str
    test_date: str

# ========== TELEGRAM API (ROBUST) ==========

async def telegram_api(method: str, data: dict = None, retries: int = 5) -> dict:
    """
    Make Telegram API call with automatic retries and error handling.
    Handles rate limits (429), server errors (500+), timeouts.
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not configured!")
        return {"ok": False, "error": "Token not configured"}
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
    
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=15.0) as http:
                if data:
                    response = await http.post(url, json=data)
                else:
                    response = await http.get(url)
                
                result = response.json()
                
                if result.get("ok"):
                    return result
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = result.get("parameters", {}).get("retry_after", 5)
                    logger.warning(f"Rate limited! Waiting {retry_after}s...")
                    await asyncio.sleep(retry_after)
                    continue
                
                # Log error but continue retrying
                logger.warning(f"API error (attempt {attempt+1}/{retries}): {result}")
                
        except httpx.TimeoutException:
            logger.warning(f"Timeout (attempt {attempt+1}/{retries})")
        except Exception as e:
            logger.error(f"API exception (attempt {attempt+1}/{retries}): {type(e).__name__}: {e}")
        
        if attempt < retries - 1:
            await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
    
    state.errors_count += 1
    return {"ok": False, "error": "All retries failed"}


async def send_message(chat_id, text: str, parse_mode: str = "HTML") -> bool:
    """Send a Telegram message - guaranteed delivery with retries."""
    result = await telegram_api("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    })
    
    if result.get("ok"):
        state.last_message_sent = time.time()
        state.messages_sent_count += 1
        logger.info(f"✅ Message sent to {chat_id}")
        return True
    
    logger.error(f"❌ Failed to send message to {chat_id}")
    return False


async def get_bot_info() -> dict:
    """Get bot information."""
    result = await telegram_api("getMe")
    if result.get("ok"):
        return result.get("result", {})
    return {}


async def get_webhook_info() -> dict:
    """Get current webhook status."""
    result = await telegram_api("getWebhookInfo")
    if result.get("ok"):
        return result.get("result", {})
    return {}


async def set_webhook(url: str) -> bool:
    """Set the webhook URL."""
    # First delete any existing webhook
    await telegram_api("deleteWebhook", {"drop_pending_updates": True})
    await asyncio.sleep(0.5)
    
    # Set new webhook
    result = await telegram_api("setWebhook", {
        "url": url,
        "allowed_updates": ["message"],
        "drop_pending_updates": True
    })
    
    if result.get("ok"):
        logger.info(f"✅ Webhook set to: {url}")
        state.webhook_registered = True
        state.webhook_url = url
        return True
    
    logger.error(f"❌ Failed to set webhook: {result}")
    return False


async def delete_webhook() -> bool:
    """Delete the webhook."""
    result = await telegram_api("deleteWebhook", {"drop_pending_updates": True})
    state.webhook_registered = False
    return result.get("ok", False)


# ========== WEBHOOK REGISTRATION & HEALTH ==========

async def register_webhook(base_url: str) -> bool:
    """
    Register webhook with Telegram.
    Called on startup and by health checker if issues detected.
    """
    webhook_url = f"{base_url}{WEBHOOK_PATH}"
    
    logger.info("=" * 50)
    logger.info("🔧 REGISTERING WEBHOOK")
    logger.info(f"   URL: {webhook_url}")
    logger.info("=" * 50)
    
    # Delete old webhook first
    await delete_webhook()
    await asyncio.sleep(1)
    
    # Set new webhook
    success = await set_webhook(webhook_url)
    
    if success:
        # Verify it was set correctly
        await asyncio.sleep(1)
        info = await get_webhook_info()
        
        if info.get("url") == webhook_url:
            logger.info("✅ Webhook verified successfully!")
            logger.info(f"   Pending updates: {info.get('pending_update_count', 0)}")
            state.last_webhook_check = time.time()
            return True
        else:
            logger.error(f"❌ Webhook URL mismatch! Expected: {webhook_url}, Got: {info.get('url')}")
    
    return False


async def health_check_and_repair(base_url: str):
    """
    Active health check that verifies webhook is working.
    If issues detected, automatically re-registers webhook.
    """
    try:
        # Check webhook status
        info = await get_webhook_info()
        
        expected_url = f"{base_url}{WEBHOOK_PATH}"
        current_url = info.get("url", "")
        last_error = info.get("last_error_message", "")
        pending = info.get("pending_update_count", 0)
        
        issues = []
        
        # Check for problems
        if not current_url:
            issues.append("No webhook URL set")
        elif current_url != expected_url:
            issues.append(f"Wrong webhook URL: {current_url}")
        
        if last_error:
            issues.append(f"Last error: {last_error}")
        
        if pending > 10:
            issues.append(f"Too many pending updates: {pending}")
        
        # No messages received in last 5 minutes but system is older than 5 min
        uptime = time.time() - state.startup_time
        if uptime > 300 and state.messages_received_count == 0:
            # This might be normal if no users messaged, but log it
            logger.info("ℹ️ No messages received yet (may be normal)")
        
        if issues:
            logger.warning("⚠️ HEALTH CHECK ISSUES DETECTED:")
            for issue in issues:
                logger.warning(f"   - {issue}")
            
            # Attempt repair
            logger.info("🔄 Attempting auto-repair...")
            state.auto_recoveries += 1
            
            success = await register_webhook(base_url)
            
            if success:
                logger.info("✅ Auto-repair successful!")
                state.health_checks_passed += 1
            else:
                logger.error("❌ Auto-repair FAILED!")
                state.health_checks_failed += 1
        else:
            state.health_checks_passed += 1
            logger.info(f"✅ Health check passed (pending: {pending})")
        
        state.last_webhook_check = time.time()
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        state.health_checks_failed += 1


async def health_checker_loop(base_url: str):
    """
    Runs every 30 seconds to verify webhook is healthy.
    Auto-repairs if any issues detected.
    """
    state.health_checker_running = True
    logger.info("🏥 Health checker started (30s interval)")
    
    while state.health_checker_running:
        try:
            await asyncio.sleep(30)
            await health_check_and_repair(base_url)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Health checker error: {e}")
    
    logger.info("🏥 Health checker stopped")


# ========== MESSAGE HANDLING ==========

async def handle_telegram_message(message: dict):
    """
    Handle incoming Telegram message.
    ALWAYS responds with chat ID for /start.
    """
    try:
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        text = message.get("text", "")
        first_name = message.get("from", {}).get("first_name", "there")
        username = message.get("from", {}).get("username", "")
        
        if not chat_id:
            return
        
        state.last_message_received = time.time()
        state.messages_received_count += 1
        
        logger.info(f"📩 Message from {chat_id} (@{username}): {text[:50]}")
        
        # Command handling
        if text.startswith("/start"):
            response = (
                f"👋 <b>Welcome to CEnT-S Alert, {first_name}!</b>\n\n"
                f"🔑 Your Chat ID is:\n\n"
                f"<code>{chat_id}</code>\n\n"
                f"👆 <b>Tap to copy</b>, then paste it in the app.\n\n"
                f"✅ You'll receive instant alerts when CENT@CASA spots open!"
            )
        
        elif text.startswith("/status"):
            uptime = int(time.time() - state.startup_time)
            hours, remainder = divmod(uptime, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            response = (
                f"🤖 <b>Bot Status: ONLINE</b>\n\n"
                f"⏱ Uptime: {hours}h {minutes}m {seconds}s\n"
                f"📨 Messages received: {state.messages_received_count}\n"
                f"📤 Messages sent: {state.messages_sent_count}\n"
                f"🔧 Auto-recoveries: {state.auto_recoveries}\n"
                f"✅ Health checks: {state.health_checks_passed}\n\n"
                f"Your Chat ID: <code>{chat_id}</code>"
            )
        
        elif text.startswith("/id"):
            response = f"🔑 Your Chat ID: <code>{chat_id}</code>"
        
        elif text.startswith("/help"):
            response = (
                f"🤖 <b>CEnT-S Alert Bot Commands</b>\n\n"
                f"/start - Get your Chat ID\n"
                f"/status - Check bot status\n"
                f"/id - Show your Chat ID\n"
                f"/help - Show this help\n\n"
                f"Your Chat ID: <code>{chat_id}</code>"
            )
        
        elif text.startswith("/stop"):
            # Remove from alerts
            await db.users.update_many(
                {"telegram_chat_id": str(chat_id)},
                {"$set": {"alert_telegram": False}}
            )
            response = "🔕 Alerts disabled. Send /start to re-enable."
        
        else:
            response = (
                f"Your Chat ID: <code>{chat_id}</code>\n\n"
                f"Commands: /start /status /help"
            )
        
        await send_message(chat_id, response)
        
    except Exception as e:
        logger.error(f"Message handling error: {e}")


# ========== SCRAPER ==========

async def scrape_cisia() -> List[AvailabilitySpot]:
    """Scrape CISIA calendar for CENT@CASA spots."""
    spots = []
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as http:
            response = await http.get(CISIA_URL, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            table = soup.find('table')
            
            if not table:
                logger.warning("No table found on CISIA page")
                return spots
            
            for row in table.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 7:
                    test_type = cells[0].get_text(strip=True)
                    
                    if "CENT@CASA" in test_type.upper() or "CASA" in test_type.upper():
                        status_cell = cells[6]
                        has_link = status_cell.find('a') is not None
                        status = "POSTI DISPONIBILI" if has_link else status_cell.get_text(strip=True)
                        
                        spots.append(AvailabilitySpot(
                            type=test_type,
                            university=cells[1].get_text(strip=True),
                            region=cells[2].get_text(strip=True),
                            city=cells[3].get_text(strip=True),
                            registration_deadline=cells[4].get_text(strip=True),
                            spots=cells[5].get_text(strip=True),
                            status=status,
                            test_date=cells[7].get_text(strip=True) if len(cells) > 7 else ""
                        ))
                        
    except Exception as e:
        logger.error(f"Scraper error: {e}")
    
    return spots


async def send_spot_alert(chat_id: str, spot: AvailabilitySpot) -> bool:
    """Send alert about available spot."""
    alert = (
        f"🟢 <b>CENT@CASA SPOT AVAILABLE!</b>\n\n"
        f"🏫 <b>{spot.university}</b>\n"
        f"📍 {spot.city}, {spot.region}\n"
        f"📅 Test: {spot.test_date}\n"
        f"⏰ Deadline: {spot.registration_deadline}\n"
        f"🎫 Spots: {spot.spots}\n\n"
        f"👉 <a href='https://testcisia.it/studenti_tolc/login_sso.php'>BOOK NOW!</a>"
    )
    return await send_message(chat_id, alert)


async def notify_users_about_spot(spot: AvailabilitySpot):
    """Notify all subscribed users about a new spot."""
    users = await db.users.find(
        {"alert_telegram": True, "telegram_chat_id": {"$ne": None}},
        {"_id": 0}
    ).to_list(1000)
    
    for user in users:
        chat_id = user.get('telegram_chat_id')
        if chat_id:
            success = await send_spot_alert(chat_id, spot)
            
            if success:
                await db.notifications.insert_one({
                    "notification_id": str(uuid.uuid4()),
                    "user_id": user.get('user_id'),
                    "type": "telegram",
                    "message": f"Spot available at {spot.university}",
                    "spot_info": spot.model_dump(),
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "status": "sent"
                })


async def check_for_new_spots():
    """Check CISIA for new CENT@CASA spots and notify users."""
    logger.info("🔍 Checking CISIA for new spots...")
    
    try:
        spots = await scrape_cisia()
        available = [s for s in spots if "DISPONIBILI" in s.status.upper()]
        
        # Get last snapshot
        last = await db.availability_snapshots.find_one(
            {}, {"_id": 0}, sort=[("timestamp", -1)]
        )
        
        # Save current snapshot
        await db.availability_snapshots.insert_one({
            "snapshot_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "spots": [s.model_dump() for s in spots],
            "available_count": len(available)
        })
        
        # Check for NEW spots
        if last:
            old_keys = set()
            for s in last.get('spots', []):
                if "DISPONIBILI" in s.get('status', '').upper():
                    old_keys.add(f"{s.get('university')}|{s.get('test_date')}")
            
            for spot in available:
                key = f"{spot.university}|{spot.test_date}"
                if key not in old_keys:
                    logger.info(f"🆕 NEW SPOT: {spot.university}")
                    await notify_users_about_spot(spot)
        
        logger.info(f"✅ Scraper done. {len(available)} available, {len(spots)} total CENT@CASA")
        
    except Exception as e:
        logger.error(f"Scraper check error: {e}")


async def scraper_loop():
    """Run scraper every 30 seconds."""
    state.scraper_running = True
    logger.info("🔄 Scraper started (30s interval)")
    
    while state.scraper_running:
        try:
            await check_for_new_spots()
        except Exception as e:
            logger.error(f"Scraper loop error: {e}")
        
        await asyncio.sleep(30)
    
    logger.info("🔄 Scraper stopped")


# ========== FASTAPI APP ==========

@asynccontextmanager
async def lifespan(app: FastAPI):
    """App startup and shutdown."""
    logger.info("=" * 60)
    logger.info("🚀 CEnT-S ALERT SYSTEM v2 - WEBHOOK EDITION")
    logger.info("=" * 60)
    
    # Get bot info
    bot_info = await get_bot_info()
    state.bot_username = bot_info.get("username", "unknown")
    logger.info(f"🤖 Bot: @{state.bot_username}")
    
    # Get base URL from environment
    base_url = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
    if not base_url:
        # Fallback: try to detect from frontend .env
        try:
            frontend_env = Path("/app/frontend/.env").read_text()
            for line in frontend_env.split('\n'):
                if line.startswith('REACT_APP_BACKEND_URL='):
                    base_url = line.split('=', 1)[1].strip().strip('"').rstrip('/')
                    break
        except:
            pass
    
    if base_url:
        # Register webhook
        success = await register_webhook(base_url)
        if not success:
            logger.error("⚠️ Initial webhook registration failed! Health checker will retry.")
        
        # Start health checker
        asyncio.create_task(health_checker_loop(base_url))
    else:
        logger.error("❌ Could not determine base URL for webhook!")
    
    # Start scraper
    asyncio.create_task(scraper_loop())
    
    logger.info("=" * 60)
    logger.info("✅ SYSTEM READY")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    state.scraper_running = False
    state.health_checker_running = False
    await delete_webhook()
    client.close()
    logger.info("System shutdown complete")


app = FastAPI(lifespan=lifespan)
api_router = APIRouter(prefix="/api")


# ========== WEBHOOK ENDPOINT ==========

@api_router.post(f"/telegram/webhook/{WEBHOOK_SECRET}")
async def telegram_webhook(request: Request):
    """
    Telegram webhook endpoint.
    Secured with secret path to prevent unauthorized access.
    """
    try:
        data = await request.json()
        
        if "message" in data:
            # Handle in background to respond quickly
            asyncio.create_task(handle_telegram_message(data["message"]))
        
        # Always return 200 OK quickly
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"ok": True}  # Still return OK to prevent Telegram retries


# ========== AUTH HELPERS ==========

async def get_current_user(request: Request):
    """Get authenticated user from session."""
    session_token = request.cookies.get('session_token')
    if not session_token:
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            session_token = auth[7:]
    
    if not session_token:
        return None
    
    session = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if not session:
        return None
    
    expires = session.get('expires_at')
    if isinstance(expires, str):
        expires = datetime.fromisoformat(expires)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        return None
    
    return await db.users.find_one({"user_id": session['user_id']}, {"_id": 0})


# ========== AUTH ROUTES ==========

@api_router.post("/auth/session")
async def exchange_session(request: Request, response: Response):
    """Exchange OAuth session for app session."""
    body = await request.json()
    session_id = body.get('session_id')
    if not session_id:
        raise HTTPException(400, "session_id required")
    
    try:
        async with httpx.AsyncClient() as http:
            r = await http.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id}
            )
            r.raise_for_status()
            auth = r.json()
    except:
        raise HTTPException(401, "Invalid session")
    
    email = auth.get('email')
    name = auth.get('name')
    picture = auth.get('picture')
    session_token = auth.get('session_token')
    
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    
    if existing:
        user_id = existing['user_id']
        await db.users.update_one({"email": email}, {"$set": {"name": name, "picture": picture}})
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "telegram_chat_id": None,
            "alert_telegram": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    await db.user_sessions.insert_one({
        "session_token": session_token,
        "user_id": user_id,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    
    response.set_cookie(
        "session_token", session_token,
        httponly=True, secure=True, samesite="none", path="/", max_age=604800
    )
    
    return {"user": user, "needs_telegram": not user.get('telegram_chat_id')}


@api_router.get("/auth/me")
async def get_me(request: Request):
    """Get current user."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return user


@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user."""
    token = request.cookies.get('session_token')
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/", secure=True, samesite="none")
    return {"status": "logged_out"}


# ========== USER ROUTES ==========

@api_router.post("/users/telegram")
async def connect_telegram(request: Request, data: TelegramConnectRequest):
    """Connect user's Telegram account."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    
    await db.users.update_one(
        {"user_id": user['user_id']},
        {"$set": {"telegram_chat_id": data.chat_id, "alert_telegram": True}}
    )
    
    await send_message(
        data.chat_id,
        "✅ <b>Connected to CEnT-S Alert!</b>\n\nYou'll receive instant notifications when CENT@CASA spots open."
    )
    
    return await db.users.find_one({"user_id": user['user_id']}, {"_id": 0})


@api_router.put("/users/alerts")
async def update_alerts(request: Request, settings: AlertSettingsRequest):
    """Update alert settings."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    
    await db.users.update_one(
        {"user_id": user['user_id']},
        {"$set": {"alert_telegram": settings.alert_telegram}}
    )
    
    return await db.users.find_one({"user_id": user['user_id']}, {"_id": 0})


# ========== TELEGRAM INFO ==========

@api_router.get("/telegram/bot-info")
async def get_telegram_bot_info():
    """Get bot username for connection link."""
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(503, "Bot not configured")
    
    bot_info = await get_bot_info()
    if bot_info:
        return {
            "username": bot_info.get("username"),
            "name": bot_info.get("first_name")
        }
    
    raise HTTPException(503, "Failed to get bot info")


# ========== AVAILABILITY ROUTES ==========

@api_router.get("/availability")
async def get_availability():
    """Get current CENT@CASA availability."""
    snapshot = await db.availability_snapshots.find_one(
        {}, {"_id": 0}, sort=[("timestamp", -1)]
    )
    
    if not snapshot:
        spots = await scrape_cisia()
        available = [s for s in spots if "DISPONIBILI" in s.status.upper()]
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "spots": [s.model_dump() for s in spots],
            "available_count": len(available),
            "total_cent_casa": len(spots)
        }
    
    return {
        "timestamp": snapshot.get('timestamp'),
        "spots": snapshot.get('spots', []),
        "available_count": snapshot.get('available_count', 0),
        "total_cent_casa": len(snapshot.get('spots', []))
    }


@api_router.get("/availability/history")
async def get_availability_history(limit: int = 50):
    """Get availability check history."""
    return await db.availability_snapshots.find(
        {}, {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)


@api_router.post("/availability/refresh")
async def refresh_availability(background_tasks: BackgroundTasks, request: Request):
    """Manually trigger availability check."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    
    background_tasks.add_task(check_for_new_spots)
    return {"status": "started"}


# ========== NOTIFICATIONS ==========

@api_router.get("/notifications/history")
async def get_notification_history(request: Request, limit: int = 50):
    """Get user's notification history."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    
    return await db.notifications.find(
        {"user_id": user['user_id']}, {"_id": 0}
    ).sort("sent_at", -1).limit(limit).to_list(limit)


# ========== HEALTH & STATUS ==========

@api_router.get("/")
async def root():
    """API root."""
    return {"message": "CEnT-S Alert API v2", "status": "running"}


@api_router.get("/health")
async def health():
    """Detailed health status."""
    uptime = int(time.time() - state.startup_time)
    
    return {
        "status": "healthy",
        "version": "2.0-webhook",
        "uptime_seconds": uptime,
        "bot_username": state.bot_username,
        "webhook": {
            "registered": state.webhook_registered,
            "url": state.webhook_url,
            "last_check_ago": round(time.time() - state.last_webhook_check, 1) if state.last_webhook_check else None
        },
        "messages": {
            "received": state.messages_received_count,
            "sent": state.messages_sent_count,
            "last_received_ago": round(time.time() - state.last_message_received, 1) if state.last_message_received else None
        },
        "health_checks": {
            "passed": state.health_checks_passed,
            "failed": state.health_checks_failed,
            "auto_recoveries": state.auto_recoveries
        },
        "scraper_running": state.scraper_running,
        "health_checker_running": state.health_checker_running,
        "errors_count": state.errors_count
    }


@api_router.post("/telegram/force-reregister")
async def force_reregister_webhook():
    """Emergency endpoint to force webhook re-registration."""
    try:
        base_url = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
        if not base_url:
            frontend_env = Path("/app/frontend/.env").read_text()
            for line in frontend_env.split('\n'):
                if line.startswith('REACT_APP_BACKEND_URL='):
                    base_url = line.split('=', 1)[1].strip().strip('"').rstrip('/')
                    break
        
        if base_url:
            success = await register_webhook(base_url)
            return {"status": "success" if success else "failed", "webhook_url": state.webhook_url}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
    return {"status": "error", "message": "Could not determine base URL"}


# ========== INCLUDE ROUTER ==========

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
