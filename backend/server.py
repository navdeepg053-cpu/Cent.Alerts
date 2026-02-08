from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, BackgroundTasks
from fastapi.responses import JSONResponse
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
import traceback
import time

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}" if TELEGRAM_BOT_TOKEN else None

CISIA_URL = "https://testcisia.it/calendario.php?tolc=cents&lingua=inglese"

# ========== GLOBAL STATE WITH HEARTBEAT ==========
class TelegramPollingState:
    def __init__(self):
        self.is_running = False
        self.last_heartbeat = 0
        self.restart_count = 0
        self.task = None
    
    def heartbeat(self):
        self.last_heartbeat = time.time()
    
    def is_alive(self) -> bool:
        # Consider dead if no heartbeat for 60 seconds
        return (time.time() - self.last_heartbeat) < 60
    
    def mark_started(self):
        self.is_running = True
        self.heartbeat()
    
    def mark_stopped(self):
        self.is_running = False

polling_state = TelegramPollingState()
scraper_running = False
watchdog_running = False

# ========== MODELS ==========

class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    alert_telegram: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserSession(BaseModel):
    session_token: str
    user_id: str
    expires_at: datetime
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

class AvailabilitySnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    spots: List[AvailabilitySpot]
    available_count: int = 0

class Notification(BaseModel):
    notification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    type: str
    message: str
    spot_info: Optional[dict] = None
    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "sent"

# ========== BULLETPROOF TELEGRAM FUNCTIONS ==========

async def telegram_send_message(chat_id, text: str) -> bool:
    """
    GUARANTEED message delivery - retries forever until success or gives up after 10 tries
    """
    if not TELEGRAM_BOT_TOKEN:
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    
    for attempt in range(10):
        try:
            async with httpx.AsyncClient(timeout=10.0) as http:
                response = await http.post(url, json=payload)
                data = response.json()
                
                if data.get("ok"):
                    logger.info(f"✅ Message sent to {chat_id}")
                    return True
                else:
                    logger.warning(f"Telegram error (attempt {attempt+1}): {data}")
        except Exception as e:
            logger.error(f"Send failed (attempt {attempt+1}): {type(e).__name__}: {e}")
        
        await asyncio.sleep(0.5)
    
    logger.error(f"❌ FAILED to send message to {chat_id} after 10 attempts")
    return False


async def telegram_get_updates(offset: int) -> tuple:
    """
    Get updates with SHORT timeout for reliability
    """
    if not TELEGRAM_BOT_TOKEN:
        return [], offset
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            response = await http.post(url, json={
                "offset": offset,
                "timeout": 3,  # Very short timeout
                "allowed_updates": ["message"]
            })
            data = response.json()
            
            if data.get("ok"):
                updates = data.get("result", [])
                if updates:
                    new_offset = max(u.get("update_id", 0) for u in updates) + 1
                    return updates, new_offset
    except httpx.TimeoutException:
        pass  # Normal for polling
    except Exception as e:
        logger.error(f"getUpdates error: {type(e).__name__}: {e}")
    
    return [], offset


async def handle_message(message: dict):
    """Handle incoming Telegram message - ALWAYS responds with chat ID"""
    try:
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        first_name = message.get("from", {}).get("first_name", "there")
        
        if not chat_id:
            return
        
        logger.info(f"📩 [{chat_id}] {text[:30]}")
        
        if text.startswith("/start"):
            response = (
                f"👋 <b>Welcome, {first_name}!</b>\n\n"
                f"🔑 Your Chat ID:\n\n"
                f"<code>{chat_id}</code>\n\n"
                f"👆 Tap to copy, then paste in the app!"
            )
        elif text.startswith("/help"):
            response = f"🤖 <b>Commands:</b>\n/start - Get Chat ID\n/id - Show ID\n\nYour ID: <code>{chat_id}</code>"
        elif text.startswith("/id"):
            response = f"🔑 <code>{chat_id}</code>"
        elif text.startswith("/status"):
            response = f"✅ Bot is ONLINE\nYour ID: <code>{chat_id}</code>"
        else:
            response = f"Your Chat ID: <code>{chat_id}</code>\nSend /start for help."
        
        await telegram_send_message(chat_id, response)
        
    except Exception as e:
        logger.error(f"Message handling error: {e}")


async def polling_loop():
    """
    THE CORE POLLING LOOP - runs forever, handles ALL errors
    """
    global polling_state
    offset = 0
    
    logger.info("🔄 Polling loop STARTED")
    polling_state.mark_started()
    
    # Delete webhook first
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            await http.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook")
        logger.info("✅ Webhook deleted")
    except:
        pass
    
    while polling_state.is_running:
        try:
            # Update heartbeat EVERY iteration
            polling_state.heartbeat()
            
            # Get updates
            updates, new_offset = await telegram_get_updates(offset)
            
            if updates:
                offset = new_offset
                for update in updates:
                    if "message" in update:
                        # Handle each message in a separate try-catch
                        try:
                            await handle_message(update["message"])
                        except Exception as e:
                            logger.error(f"Message error: {e}")
            
            # Brief pause
            await asyncio.sleep(0.3)
            
        except asyncio.CancelledError:
            logger.info("Polling loop cancelled")
            break
        except Exception as e:
            logger.error(f"Polling loop error: {type(e).__name__}: {e}")
            await asyncio.sleep(1)
    
    polling_state.mark_stopped()
    logger.info("🛑 Polling loop STOPPED")


async def start_polling():
    """Start the polling loop as a task"""
    global polling_state
    
    if polling_state.task and not polling_state.task.done():
        logger.info("Polling already running")
        return
    
    polling_state.is_running = True
    polling_state.task = asyncio.create_task(polling_loop())
    polling_state.restart_count += 1
    logger.info(f"🚀 Polling task created (restart #{polling_state.restart_count})")


async def watchdog_loop():
    """
    WATCHDOG - monitors polling and restarts if dead
    Runs every 10 seconds, checks heartbeat, restarts if needed
    """
    global watchdog_running, polling_state
    watchdog_running = True
    
    logger.info("🐕 WATCHDOG STARTED - will monitor polling 24/7")
    
    while watchdog_running:
        try:
            await asyncio.sleep(10)  # Check every 10 seconds
            
            # Check if polling is alive
            if not polling_state.is_alive():
                logger.warning("⚠️ WATCHDOG: Polling appears DEAD! Restarting...")
                
                # Cancel old task if exists
                if polling_state.task:
                    polling_state.task.cancel()
                    try:
                        await polling_state.task
                    except:
                        pass
                
                # Restart polling
                await start_polling()
                logger.info("✅ WATCHDOG: Polling restarted!")
            
            # Also check if task died unexpectedly
            if polling_state.task and polling_state.task.done():
                logger.warning("⚠️ WATCHDOG: Polling task DIED! Restarting...")
                await start_polling()
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Watchdog error: {e}")
    
    logger.info("🐕 WATCHDOG STOPPED")


# ========== SCRAPER FUNCTIONS ==========

async def scrape_cisia_page() -> List[AvailabilitySpot]:
    """Scrape CISIA for CENT@CASA spots"""
    spots = []
    try:
        async with httpx.AsyncClient(timeout=30.0) as http:
            response = await http.get(CISIA_URL)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            table = soup.find('table')
            if not table:
                return spots
            
            for row in table.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 7:
                    test_type = cells[0].get_text(strip=True)
                    
                    if "CENT@CASA" in test_type.upper() or "CASA" in test_type.upper():
                        status_cell = cells[6]
                        status = "POSTI DISPONIBILI" if status_cell.find('a') else status_cell.get_text(strip=True)
                        
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


async def send_spot_alert(chat_id: str, spot: AvailabilitySpot) -> bool:
    """Send spot alert"""
    alert = (
        f"🟢 <b>SPOT AVAILABLE!</b>\n\n"
        f"🏫 {spot.university}\n"
        f"📍 {spot.city}, {spot.region}\n"
        f"📅 {spot.test_date}\n"
        f"⏰ Deadline: {spot.registration_deadline}\n"
        f"🎫 Spots: {spot.spots}\n\n"
        f"👉 <a href='https://testcisia.it/studenti_tolc/login_sso.php'>BOOK NOW</a>"
    )
    return await telegram_send_message(chat_id, alert)


async def notify_users(spot: AvailabilitySpot):
    """Notify all subscribed users"""
    users = await db.users.find({"alert_telegram": True}, {"_id": 0}).to_list(1000)
    
    for user in users:
        chat_id = user.get('telegram_chat_id')
        if chat_id and await send_spot_alert(chat_id, spot):
            await db.notifications.insert_one({
                "notification_id": str(uuid.uuid4()),
                "user_id": user['user_id'],
                "type": "telegram",
                "message": f"Spot at {spot.university}",
                "spot_info": spot.model_dump(),
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "status": "sent"
            })


async def check_spots():
    """Check for new spots"""
    logger.info("🔍 Checking CISIA...")
    
    spots = await scrape_cisia_page()
    available = [s for s in spots if "DISPONIBILI" in s.status.upper()]
    
    last = await db.availability_snapshots.find_one({}, {"_id": 0}, sort=[("timestamp", -1)])
    
    # Save snapshot
    await db.availability_snapshots.insert_one({
        "snapshot_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "spots": [s.model_dump() for s in spots],
        "available_count": len(available)
    })
    
    # Check for NEW spots
    if last:
        old_ids = {f"{s.get('university')}_{s.get('test_date')}" 
                   for s in last.get('spots', []) 
                   if "DISPONIBILI" in s.get('status', '').upper()}
        
        for spot in available:
            if f"{spot.university}_{spot.test_date}" not in old_ids:
                logger.info(f"🆕 NEW SPOT: {spot.university}")
                await notify_users(spot)
    
    logger.info(f"✅ Check done. {len(available)} available spots.")


async def scraper_loop():
    """Scraper loop - every 30 seconds"""
    global scraper_running
    scraper_running = True
    
    while scraper_running:
        try:
            await check_spots()
        except Exception as e:
            logger.error(f"Scraper error: {e}")
        await asyncio.sleep(30)


# ========== APP LIFECYCLE ==========

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 50)
    logger.info("🚀 CEnT-S ALERT SYSTEM STARTING")
    logger.info("=" * 50)
    
    # Start scraper
    asyncio.create_task(scraper_loop())
    logger.info("✅ Scraper started (30s interval)")
    
    # Start Telegram polling
    if TELEGRAM_BOT_TOKEN:
        await start_polling()
        # Start watchdog to monitor polling
        asyncio.create_task(watchdog_loop())
        logger.info("✅ Telegram polling + watchdog started")
    else:
        logger.warning("⚠️ No TELEGRAM_BOT_TOKEN")
    
    logger.info("=" * 50)
    
    yield
    
    # Shutdown
    global scraper_running, watchdog_running, polling_state
    scraper_running = False
    watchdog_running = False
    polling_state.is_running = False
    
    if polling_state.task:
        polling_state.task.cancel()
    
    client.close()
    logger.info("System shutdown complete")


app = FastAPI(lifespan=lifespan)
api_router = APIRouter(prefix="/api")

# ========== AUTH ==========

async def get_current_user(request: Request) -> Optional[dict]:
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


@api_router.post("/auth/session")
async def exchange_session(request: Request, response: Response):
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
    
    email, name, picture = auth.get('email'), auth.get('name'), auth.get('picture')
    session_token = auth.get('session_token')
    
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    
    if existing:
        user_id = existing['user_id']
        await db.users.update_one({"email": email}, {"$set": {"name": name, "picture": picture}})
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id, "email": email, "name": name, "picture": picture,
            "telegram_chat_id": None, "alert_telegram": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    await db.user_sessions.insert_one({
        "session_token": session_token, "user_id": user_id,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    
    response.set_cookie("session_token", session_token, httponly=True, secure=True, samesite="none", path="/", max_age=604800)
    
    return {"user": user, "needs_telegram": not user.get('telegram_chat_id')}


@api_router.get("/auth/me")
async def get_me(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return user


@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get('session_token')
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/", secure=True, samesite="none")
    return {"status": "logged_out"}


# ========== USER ROUTES ==========

@api_router.post("/users/telegram")
async def connect_telegram(request: Request, data: TelegramConnectRequest):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    
    await db.users.update_one(
        {"user_id": user['user_id']},
        {"$set": {"telegram_chat_id": data.chat_id, "alert_telegram": True}}
    )
    
    await telegram_send_message(data.chat_id, "✅ <b>Connected!</b>\n\nYou'll receive alerts when spots open.")
    
    return await db.users.find_one({"user_id": user['user_id']}, {"_id": 0})


@api_router.put("/users/alerts")
async def update_alerts(request: Request, settings: AlertSettingsRequest):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    
    await db.users.update_one({"user_id": user['user_id']}, {"$set": {"alert_telegram": settings.alert_telegram}})
    return await db.users.find_one({"user_id": user['user_id']}, {"_id": 0})


# ========== TELEGRAM INFO ==========

@api_router.get("/telegram/bot-info")
async def get_bot_info():
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(503, "Bot not configured")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            r = await http.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe")
            data = r.json()
            if data.get("ok"):
                return {"username": data["result"]["username"], "name": data["result"]["first_name"]}
    except:
        pass
    raise HTTPException(503, "Failed to get bot info")


# ========== AVAILABILITY ==========

@api_router.get("/availability")
async def get_availability():
    snapshot = await db.availability_snapshots.find_one({}, {"_id": 0}, sort=[("timestamp", -1)])
    
    if not snapshot:
        spots = await scrape_cisia_page()
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "spots": [s.model_dump() for s in spots],
            "available_count": len([s for s in spots if "DISPONIBILI" in s.status.upper()]),
            "total_cent_casa": len(spots)
        }
    
    return {
        "timestamp": snapshot.get('timestamp'),
        "spots": snapshot.get('spots', []),
        "available_count": snapshot.get('available_count', 0),
        "total_cent_casa": len(snapshot.get('spots', []))
    }


@api_router.get("/availability/history")
async def get_history(limit: int = 50):
    return await db.availability_snapshots.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)


@api_router.post("/availability/refresh")
async def refresh(background_tasks: BackgroundTasks, request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    background_tasks.add_task(check_spots)
    return {"status": "started"}


# ========== NOTIFICATIONS ==========

@api_router.get("/notifications/history")
async def get_notif_history(request: Request, limit: int = 50):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return await db.notifications.find({"user_id": user['user_id']}, {"_id": 0}).sort("sent_at", -1).limit(limit).to_list(limit)


# ========== HEALTH ==========

@api_router.get("/")
async def root():
    return {"message": "CEnT-S Alert API", "status": "running"}


@api_router.get("/health")
async def health():
    return {
        "status": "healthy",
        "scraper_running": scraper_running,
        "telegram_polling": polling_state.is_running,
        "telegram_alive": polling_state.is_alive(),
        "watchdog_running": watchdog_running,
        "polling_restarts": polling_state.restart_count,
        "last_heartbeat_ago": round(time.time() - polling_state.last_heartbeat, 1) if polling_state.last_heartbeat else None
    }


# Force restart polling endpoint (emergency use)
@api_router.post("/telegram/restart-polling")
async def restart_polling():
    global polling_state
    
    if polling_state.task:
        polling_state.task.cancel()
        try:
            await polling_state.task
        except:
            pass
    
    await start_polling()
    return {"status": "restarted", "restart_count": polling_state.restart_count}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
