"""
CEnT-S Alert System v3 - DUAL MODE (Webhook + Polling Fallback)
================================================================
- Primary: Webhook for instant responses
- Fallback: Polling activates if webhook fails for 2+ minutes
- Simplified webhook path for better reliability
- Aggressive health monitoring and auto-recovery
"""

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

# ========== CONFIGURATION ==========
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Simple webhook path using token hash for security
WEBHOOK_PATH = "/api/tg/wh"

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
logger = logging.getLogger("cents")

# ========== SYSTEM STATE ==========
class State:
    def __init__(self):
        # Webhook state
        self.webhook_url = None
        self.webhook_ok = False
        self.last_webhook_success = 0
        
        # Message tracking
        self.last_msg_received = 0
        self.last_msg_sent = 0
        self.msg_received_count = 0
        self.msg_sent_count = 0
        
        # Health
        self.health_checks = 0
        self.auto_recoveries = 0
        self.errors = 0
        
        # Mode
        self.mode = "webhook"  # "webhook" or "polling"
        self.polling_task = None
        
        # System
        self.bot_username = None
        self.start_time = time.time()
        self.scraper_running = False
        self.monitor_running = False

state = State()

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

# ========== TELEGRAM API ==========
async def tg_api(method: str, data: dict = None, retries: int = 3) -> dict:
    """Telegram API call with retries."""
    if not TELEGRAM_BOT_TOKEN:
        return {"ok": False, "error": "No token"}
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
    
    for i in range(retries):
        try:
            async with httpx.AsyncClient(timeout=15.0) as http:
                r = await http.post(url, json=data) if data else await http.get(url)
                result = r.json()
                
                if result.get("ok"):
                    return result
                
                # Rate limit
                if r.status_code == 429:
                    wait = result.get("parameters", {}).get("retry_after", 5)
                    await asyncio.sleep(wait)
                    continue
                    
        except Exception as e:
            logger.warning(f"API {method} failed ({i+1}/{retries}): {e}")
        
        await asyncio.sleep(1)
    
    state.errors += 1
    return {"ok": False}


async def send_msg(chat_id, text: str) -> bool:
    """Send Telegram message."""
    result = await tg_api("sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
    if result.get("ok"):
        state.last_msg_sent = time.time()
        state.msg_sent_count += 1
        logger.info(f"✉️ Sent to {chat_id}")
        return True
    logger.error(f"❌ Failed to send to {chat_id}")
    return False


# ========== WEBHOOK MANAGEMENT ==========
async def setup_webhook(base_url: str) -> bool:
    """Set up webhook with Telegram."""
    webhook_url = f"{base_url}{WEBHOOK_PATH}"
    
    logger.info(f"🔧 Setting webhook: {webhook_url}")
    
    # Delete old webhook
    await tg_api("deleteWebhook", {"drop_pending_updates": True})
    await asyncio.sleep(0.5)
    
    # Set new webhook
    result = await tg_api("setWebhook", {
        "url": webhook_url,
        "allowed_updates": ["message"],
        "drop_pending_updates": True
    })
    
    if not result.get("ok"):
        logger.error("❌ Failed to set webhook")
        return False
    
    # Verify
    await asyncio.sleep(0.5)
    info = await tg_api("getWebhookInfo")
    actual_url = info.get("result", {}).get("url", "")
    
    if actual_url == webhook_url:
        logger.info("✅ Webhook verified!")
        state.webhook_url = webhook_url
        state.webhook_ok = True
        state.last_webhook_success = time.time()
        return True
    
    logger.error(f"❌ Webhook mismatch: {actual_url}")
    return False


async def check_webhook_health(base_url: str):
    """Check if webhook is healthy, switch to polling if not."""
    info = await tg_api("getWebhookInfo")
    result = info.get("result", {})
    
    url = result.get("url", "")
    error = result.get("last_error_message", "")
    pending = result.get("pending_update_count", 0)
    
    issues = []
    
    if not url:
        issues.append("No webhook URL")
    elif url != state.webhook_url:
        issues.append(f"URL mismatch")
    
    if error:
        issues.append(f"Error: {error}")
    
    if pending > 5:
        issues.append(f"Pending: {pending}")
    
    state.health_checks += 1
    
    if issues:
        logger.warning(f"⚠️ Webhook issues: {issues}")
        
        # If webhook has been failing for 2+ minutes, switch to polling
        time_since_success = time.time() - state.last_webhook_success
        
        if time_since_success > 120 and state.mode == "webhook":
            logger.warning("🔄 Switching to POLLING mode!")
            state.mode = "polling"
            await tg_api("deleteWebhook", {"drop_pending_updates": False})
            start_polling()
            state.auto_recoveries += 1
        else:
            # Try to re-register webhook
            logger.info("🔄 Re-registering webhook...")
            await setup_webhook(base_url)
            state.auto_recoveries += 1
    else:
        state.last_webhook_success = time.time()
        logger.info(f"✅ Webhook healthy (pending: {pending})")
        
        # If we're in polling mode but webhook is now working, switch back
        if state.mode == "polling":
            logger.info("🔄 Switching back to WEBHOOK mode!")
            state.mode = "webhook"
            stop_polling()
            await setup_webhook(base_url)


# ========== POLLING FALLBACK ==========
async def polling_loop():
    """Polling loop as fallback when webhook fails."""
    logger.info("📡 Starting polling loop...")
    offset = 0
    
    while state.mode == "polling":
        try:
            result = await tg_api("getUpdates", {
                "offset": offset,
                "timeout": 5,
                "allowed_updates": ["message"]
            })
            
            updates = result.get("result", [])
            for update in updates:
                offset = update.get("update_id", 0) + 1
                if "message" in update:
                    await handle_message(update["message"])
                    
        except Exception as e:
            logger.error(f"Polling error: {e}")
        
        await asyncio.sleep(0.5)
    
    logger.info("📡 Polling loop stopped")


def start_polling():
    """Start polling task."""
    if state.polling_task is None or state.polling_task.done():
        state.polling_task = asyncio.create_task(polling_loop())


def stop_polling():
    """Stop polling task."""
    if state.polling_task and not state.polling_task.done():
        state.polling_task.cancel()


# ========== MESSAGE HANDLING ==========
async def handle_message(message: dict):
    """Handle incoming Telegram message."""
    try:
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        name = message.get("from", {}).get("first_name", "there")
        
        if not chat_id:
            return
        
        state.last_msg_received = time.time()
        state.msg_received_count += 1
        
        logger.info(f"📩 [{chat_id}] {text[:30]}")
        
        if text.startswith("/start"):
            response = (
                f"👋 <b>Welcome, {name}!</b>\n\n"
                f"🔑 Your Chat ID:\n<code>{chat_id}</code>\n\n"
                f"👆 Tap to copy, paste in app!"
            )
        elif text.startswith("/status"):
            uptime = int(time.time() - state.start_time)
            h, m = uptime // 3600, (uptime % 3600) // 60
            response = (
                f"🤖 <b>Status: ONLINE</b>\n"
                f"Mode: {state.mode.upper()}\n"
                f"Uptime: {h}h {m}m\n"
                f"Messages: {state.msg_received_count} in, {state.msg_sent_count} out\n"
                f"ID: <code>{chat_id}</code>"
            )
        elif text.startswith("/id"):
            response = f"🔑 <code>{chat_id}</code>"
        elif text.startswith("/help"):
            response = "/start - Get Chat ID\n/status - Bot status\n/id - Show ID"
        else:
            response = f"ID: <code>{chat_id}</code>\nSend /start for help"
        
        await send_msg(chat_id, response)
        
    except Exception as e:
        logger.error(f"Handle message error: {e}")


# ========== SCRAPER ==========
async def scrape_cisia() -> List[AvailabilitySpot]:
    """Scrape CISIA for CENT@CASA spots."""
    spots = []
    try:
        async with httpx.AsyncClient(timeout=30.0) as http:
            r = await http.get(CISIA_URL, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, 'lxml')
            table = soup.find('table')
            
            if table:
                for row in table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) >= 7:
                        test_type = cells[0].get_text(strip=True)
                        if "CASA" in test_type.upper():
                            status = "POSTI DISPONIBILI" if cells[6].find('a') else cells[6].get_text(strip=True)
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
        logger.error(f"Scrape error: {e}")
    return spots


async def check_spots():
    """Check for new spots and notify users."""
    logger.info("🔍 Checking CISIA...")
    
    spots = await scrape_cisia()
    available = [s for s in spots if "DISPONIBILI" in s.status.upper()]
    
    last = await db.availability_snapshots.find_one({}, {"_id": 0}, sort=[("timestamp", -1)])
    
    await db.availability_snapshots.insert_one({
        "snapshot_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "spots": [s.model_dump() for s in spots],
        "available_count": len(available)
    })
    
    if last:
        old_keys = {f"{s.get('university')}|{s.get('test_date')}" 
                    for s in last.get('spots', []) if "DISPONIBILI" in s.get('status', '').upper()}
        
        for spot in available:
            if f"{spot.university}|{spot.test_date}" not in old_keys:
                logger.info(f"🆕 NEW: {spot.university}")
                # Notify users
                users = await db.users.find({"alert_telegram": True}, {"_id": 0}).to_list(1000)
                for user in users:
                    cid = user.get('telegram_chat_id')
                    if cid:
                        alert = (
                            f"🟢 <b>SPOT AVAILABLE!</b>\n\n"
                            f"🏫 {spot.university}\n📍 {spot.city}\n"
                            f"📅 {spot.test_date}\n🎫 {spot.spots}\n\n"
                            f"<a href='https://testcisia.it/studenti_tolc/login_sso.php'>BOOK NOW</a>"
                        )
                        await send_msg(cid, alert)
    
    logger.info(f"✅ Done: {len(available)} available")


async def scraper_loop():
    """Scraper loop."""
    state.scraper_running = True
    while state.scraper_running:
        try:
            await check_spots()
        except Exception as e:
            logger.error(f"Scraper error: {e}")
        await asyncio.sleep(30)


async def monitor_loop(base_url: str):
    """Health monitor loop."""
    state.monitor_running = True
    while state.monitor_running:
        try:
            await asyncio.sleep(30)
            await check_webhook_health(base_url)
        except Exception as e:
            logger.error(f"Monitor error: {e}")


# ========== FASTAPI ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 50)
    logger.info("🚀 CEnT-S ALERT v3 - DUAL MODE")
    logger.info("=" * 50)
    
    # Get bot info
    info = await tg_api("getMe")
    state.bot_username = info.get("result", {}).get("username", "unknown")
    logger.info(f"🤖 Bot: @{state.bot_username}")
    
    # Get base URL
    base_url = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
    if not base_url:
        try:
            env = Path("/app/frontend/.env").read_text()
            for line in env.split('\n'):
                if line.startswith('REACT_APP_BACKEND_URL='):
                    base_url = line.split('=', 1)[1].strip().strip('"').rstrip('/')
        except:
            pass
    
    if base_url:
        await setup_webhook(base_url)
        asyncio.create_task(monitor_loop(base_url))
    
    asyncio.create_task(scraper_loop())
    
    logger.info("=" * 50)
    yield
    
    state.scraper_running = False
    state.monitor_running = False
    stop_polling()
    await tg_api("deleteWebhook")
    client.close()


app = FastAPI(lifespan=lifespan)
api = APIRouter(prefix="/api")


# ========== WEBHOOK ENDPOINT (SIMPLE PATH) ==========
@api.post("/tg/wh")
async def telegram_webhook(request: Request):
    """Telegram webhook - simple path for reliability."""
    try:
        data = await request.json()
        if "message" in data:
            asyncio.create_task(handle_message(data["message"]))
        return {"ok": True}
    except:
        return {"ok": True}


# ========== AUTH ==========
async def get_user(request: Request):
    token = request.cookies.get('session_token')
    if not token:
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            token = auth[7:]
    if not token:
        return None
    
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        return None
    
    exp = session.get('expires_at')
    if isinstance(exp, str):
        exp = datetime.fromisoformat(exp)
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < datetime.now(timezone.utc):
        return None
    
    return await db.users.find_one({"user_id": session['user_id']}, {"_id": 0})


@api.post("/auth/session")
async def auth_session(request: Request, response: Response):
    body = await request.json()
    sid = body.get('session_id')
    if not sid:
        raise HTTPException(400, "session_id required")
    
    try:
        async with httpx.AsyncClient() as http:
            r = await http.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": sid}
            )
            auth = r.json()
    except:
        raise HTTPException(401, "Invalid session")
    
    email = auth.get('email')
    name = auth.get('name')
    picture = auth.get('picture')
    token = auth.get('session_token')
    
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    
    if existing:
        uid = existing['user_id']
        await db.users.update_one({"email": email}, {"$set": {"name": name, "picture": picture}})
    else:
        uid = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": uid, "email": email, "name": name, "picture": picture,
            "telegram_chat_id": None, "alert_telegram": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    await db.user_sessions.insert_one({
        "session_token": token, "user_id": uid,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    user = await db.users.find_one({"user_id": uid}, {"_id": 0})
    response.set_cookie("session_token", token, httponly=True, secure=True, samesite="none", path="/", max_age=604800)
    
    return {"user": user, "needs_telegram": not user.get('telegram_chat_id')}


@api.get("/auth/me")
async def auth_me(request: Request):
    user = await get_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return user


@api.post("/auth/logout")
async def auth_logout(request: Request, response: Response):
    token = request.cookies.get('session_token')
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/", secure=True, samesite="none")
    return {"status": "ok"}


# ========== USER ==========
@api.post("/users/telegram")
async def connect_telegram(request: Request, data: TelegramConnectRequest):
    user = await get_user(request)
    if not user:
        raise HTTPException(401)
    
    await db.users.update_one(
        {"user_id": user['user_id']},
        {"$set": {"telegram_chat_id": data.chat_id, "alert_telegram": True}}
    )
    await send_msg(data.chat_id, "✅ <b>Connected!</b> You'll get alerts when spots open.")
    return await db.users.find_one({"user_id": user['user_id']}, {"_id": 0})


@api.put("/users/alerts")
async def update_alerts(request: Request, settings: AlertSettingsRequest):
    user = await get_user(request)
    if not user:
        raise HTTPException(401)
    
    await db.users.update_one({"user_id": user['user_id']}, {"$set": {"alert_telegram": settings.alert_telegram}})
    return await db.users.find_one({"user_id": user['user_id']}, {"_id": 0})


# ========== TELEGRAM INFO ==========
@api.get("/telegram/bot-info")
async def bot_info():
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(503)
    info = await tg_api("getMe")
    if info.get("ok"):
        return {"username": info["result"]["username"], "name": info["result"]["first_name"]}
    raise HTTPException(503)


# ========== AVAILABILITY ==========
@api.get("/availability")
async def get_availability():
    snap = await db.availability_snapshots.find_one({}, {"_id": 0}, sort=[("timestamp", -1)])
    if snap:
        return {
            "timestamp": snap.get('timestamp'),
            "spots": snap.get('spots', []),
            "available_count": snap.get('available_count', 0),
            "total_cent_casa": len(snap.get('spots', []))
        }
    spots = await scrape_cisia()
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "spots": [s.model_dump() for s in spots],
        "available_count": len([s for s in spots if "DISPONIBILI" in s.status.upper()]),
        "total_cent_casa": len(spots)
    }


@api.get("/availability/history")
async def availability_history(limit: int = 50):
    return await db.availability_snapshots.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)


@api.post("/availability/refresh")
async def refresh(background_tasks: BackgroundTasks, request: Request):
    user = await get_user(request)
    if not user:
        raise HTTPException(401)
    background_tasks.add_task(check_spots)
    return {"status": "started"}


# ========== NOTIFICATIONS ==========
@api.get("/notifications/history")
async def notif_history(request: Request, limit: int = 50):
    user = await get_user(request)
    if not user:
        raise HTTPException(401)
    return await db.notifications.find({"user_id": user['user_id']}, {"_id": 0}).sort("sent_at", -1).limit(limit).to_list(limit)


# ========== HEALTH ==========
@api.get("/")
async def root():
    return {"status": "ok", "service": "cents-alert-v3"}


@api.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "3.0-dual",
        "mode": state.mode,
        "uptime": int(time.time() - state.start_time),
        "bot": state.bot_username,
        "webhook_ok": state.webhook_ok,
        "messages": {"in": state.msg_received_count, "out": state.msg_sent_count},
        "health_checks": state.health_checks,
        "auto_recoveries": state.auto_recoveries,
        "errors": state.errors
    }


@api.post("/telegram/force-repair")
async def force_repair():
    """Force webhook re-registration."""
    base_url = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
    if base_url:
        await setup_webhook(base_url)
        return {"status": "done", "mode": state.mode}
    return {"status": "error", "msg": "No base URL"}


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== STATIC FILES ==========
# Serve frontend static files in production
FRONTEND_BUILD_DIR = Path(__file__).parent.parent / "frontend" / "build"

if FRONTEND_BUILD_DIR.exists():
    # Mount static files (CSS, JS, images, etc.)
    app.mount("/static", StaticFiles(directory=FRONTEND_BUILD_DIR / "static"), name="static")
    
    # Serve index.html for all non-API routes (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the React app for all non-API routes."""
        # If the path starts with 'api', it should be handled by API routes
        if full_path.startswith("api"):
            raise HTTPException(404, "Not found")
        
        # Check if the requested file exists
        file_path = FRONTEND_BUILD_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        
        # Otherwise, serve index.html (for SPA routing)
        index_path = FRONTEND_BUILD_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        
        raise HTTPException(404, "Frontend build not found")
else:
    logger.warning(f"Frontend build directory not found: {FRONTEND_BUILD_DIR}")
