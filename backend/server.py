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

# Background task states
scraper_running = False
telegram_polling_running = False

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

# ========== IRONCLAD TELEGRAM FUNCTIONS ==========

async def telegram_send_message(chat_id, text: str, retries: int = 5) -> bool:
    """
    BULLETPROOF message sender - will retry until successful
    Uses simple HTTP POST, no complex libraries
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=10.0) as http:
                response = await http.post(url, json=payload)
                data = response.json()
                
                if data.get("ok"):
                    logger.info(f"✓ Message sent to {chat_id}")
                    return True
                else:
                    logger.warning(f"Telegram API error: {data}")
        except Exception as e:
            logger.error(f"Send attempt {attempt + 1} failed: {e}")
        
        await asyncio.sleep(0.5)  # Brief pause before retry
    
    logger.error(f"FAILED to send message to {chat_id} after {retries} attempts")
    return False


async def telegram_get_updates(offset: int = 0) -> tuple:
    """
    Get updates using SHORT polling (5 seconds) for reliability
    Returns (updates_list, new_offset)
    """
    if not TELEGRAM_BOT_TOKEN:
        return [], offset
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    payload = {
        "offset": offset,
        "timeout": 5,  # SHORT timeout - more reliable
        "allowed_updates": ["message"]
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as http:  # Timeout > polling timeout
            response = await http.post(url, json=payload)
            data = response.json()
            
            if data.get("ok"):
                updates = data.get("result", [])
                if updates:
                    # Calculate new offset
                    new_offset = max(u.get("update_id", 0) for u in updates) + 1
                    return updates, new_offset
                return [], offset
    except httpx.TimeoutException:
        # Timeout is NORMAL for long polling - not an error
        pass
    except Exception as e:
        logger.error(f"getUpdates error: {e}")
    
    return [], offset


async def handle_telegram_message(message: dict):
    """
    Handle ANY incoming message - ALWAYS responds with chat ID
    """
    try:
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        text = message.get("text", "")
        first_name = message.get("from", {}).get("first_name", "there")
        
        if not chat_id:
            return
        
        logger.info(f"📩 Message from {chat_id}: {text[:50]}")
        
        # ALWAYS include chat ID in response
        if text.startswith("/start"):
            response = (
                f"👋 <b>Welcome, {first_name}!</b>\n\n"
                f"🔑 Your Chat ID is:\n\n"
                f"<code>{chat_id}</code>\n\n"
                f"👆 <b>Tap the number above to copy it</b>\n\n"
                f"Then paste it in the CEnT-S Alert app to receive notifications when CENT@CASA spots open!"
            )
        elif text.startswith("/help"):
            response = (
                f"🤖 <b>CEnT-S Alert Bot</b>\n\n"
                f"Commands:\n"
                f"/start - Get your Chat ID\n"
                f"/help - Show this help\n"
                f"/id - Show your Chat ID again\n\n"
                f"Your Chat ID: <code>{chat_id}</code>"
            )
        elif text.startswith("/id"):
            response = f"🔑 Your Chat ID: <code>{chat_id}</code>"
        elif text.startswith("/status"):
            response = (
                f"✅ <b>Bot Status: ONLINE</b>\n\n"
                f"Monitoring CENT@CASA spots 24/7\n"
                f"Your Chat ID: <code>{chat_id}</code>"
            )
        else:
            # For ANY other message, still show chat ID
            response = (
                f"Your Chat ID: <code>{chat_id}</code>\n\n"
                f"Send /start for setup instructions."
            )
        
        await telegram_send_message(chat_id, response)
        
    except Exception as e:
        logger.error(f"Error handling message: {e}\n{traceback.format_exc()}")


async def telegram_polling_loop():
    """
    IRONCLAD polling loop - runs forever, handles all errors
    Uses short polling for maximum reliability
    """
    global telegram_polling_running
    telegram_polling_running = True
    offset = 0
    
    logger.info("🚀 Starting IRONCLAD Telegram polling...")
    
    # Delete any existing webhook first
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            await http.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook",
                json={"drop_pending_updates": False}
            )
        logger.info("✓ Webhook deleted, polling mode active")
    except Exception as e:
        logger.warning(f"Could not delete webhook: {e}")
    
    consecutive_errors = 0
    
    while telegram_polling_running:
        try:
            updates, new_offset = await telegram_get_updates(offset)
            
            if updates:
                offset = new_offset
                consecutive_errors = 0  # Reset error counter on success
                
                for update in updates:
                    if "message" in update:
                        await handle_telegram_message(update["message"])
            else:
                consecutive_errors = 0  # No updates is also success
                
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Polling error #{consecutive_errors}: {e}")
            
            # Back off if too many errors
            if consecutive_errors > 10:
                logger.warning("Too many errors, waiting 30 seconds...")
                await asyncio.sleep(30)
                consecutive_errors = 0
            else:
                await asyncio.sleep(2)
            continue
        
        # Small delay between polls
        await asyncio.sleep(0.5)
    
    logger.info("Telegram polling stopped")


# ========== SCRAPER FUNCTIONS ==========

async def scrape_cisia_page() -> List[AvailabilitySpot]:
    """Scrape the CISIA calendar page for CENT@CASA availability"""
    spots = []
    try:
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.get(CISIA_URL)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            table = soup.find('table')
            if not table:
                logger.warning("No table found on CISIA page")
                return spots
            
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 7:
                    test_type = cells[0].get_text(strip=True)
                    university = cells[1].get_text(strip=True)
                    region = cells[2].get_text(strip=True)
                    city = cells[3].get_text(strip=True)
                    reg_deadline = cells[4].get_text(strip=True)
                    spots_num = cells[5].get_text(strip=True)
                    status_cell = cells[6]
                    test_date = cells[7].get_text(strip=True) if len(cells) > 7 else ""
                    
                    status_link = status_cell.find('a')
                    if status_link:
                        status = "POSTI DISPONIBILI"
                    else:
                        status = status_cell.get_text(strip=True)
                    
                    if "CENT@CASA" in test_type.upper() or "CASA" in test_type.upper():
                        spot = AvailabilitySpot(
                            type=test_type,
                            university=university,
                            region=region,
                            city=city,
                            registration_deadline=reg_deadline,
                            spots=spots_num,
                            status=status,
                            test_date=test_date
                        )
                        spots.append(spot)
                        
    except Exception as e:
        logger.error(f"Error scraping CISIA page: {e}")
    
    return spots


async def send_spot_alert(chat_id: str, spot: AvailabilitySpot) -> bool:
    """Send alert about available spot"""
    alert_text = (
        f"🟢 <b>CENT@CASA SPOT AVAILABLE!</b>\n\n"
        f"🏫 <b>University:</b> {spot.university}\n"
        f"📍 <b>Location:</b> {spot.city}, {spot.region}\n"
        f"📅 <b>Test Date:</b> {spot.test_date}\n"
        f"⏰ <b>Deadline:</b> {spot.registration_deadline}\n"
        f"🎫 <b>Spots:</b> {spot.spots}\n\n"
        f"👉 <a href='https://testcisia.it/studenti_tolc/login_sso.php'>BOOK NOW</a>"
    )
    return await telegram_send_message(chat_id, alert_text)


async def notify_users_about_spot(spot: AvailabilitySpot):
    """Notify all users with Telegram alerts enabled"""
    users = await db.users.find({"alert_telegram": True}, {"_id": 0}).to_list(1000)
    
    for user in users:
        chat_id = user.get('telegram_chat_id')
        if chat_id and await send_spot_alert(chat_id, spot):
            notification = Notification(
                user_id=user['user_id'],
                type='telegram',
                message=f"Spot available at {spot.university}",
                spot_info=spot.model_dump()
            )
            notif_doc = notification.model_dump()
            notif_doc['sent_at'] = notif_doc['sent_at'].isoformat()
            await db.notifications.insert_one(notif_doc)


async def check_for_new_spots():
    """Background task to check for new CENT@CASA spots"""
    logger.info("Starting availability check...")
    
    spots = await scrape_cisia_page()
    available_spots = [s for s in spots if "DISPONIBILI" in s.status.upper()]
    
    last_snapshot = await db.availability_snapshots.find_one(
        {},
        {"_id": 0},
        sort=[("timestamp", -1)]
    )
    
    snapshot = AvailabilitySnapshot(
        spots=spots,
        available_count=len(available_spots)
    )
    snapshot_doc = snapshot.model_dump()
    snapshot_doc['timestamp'] = snapshot_doc['timestamp'].isoformat()
    snapshot_doc['spots'] = [s.model_dump() for s in spots]
    await db.availability_snapshots.insert_one(snapshot_doc)
    
    if last_snapshot:
        last_available_ids = set()
        for s in last_snapshot.get('spots', []):
            if "DISPONIBILI" in s.get('status', '').upper():
                last_available_ids.add(f"{s.get('university')}_{s.get('test_date')}")
        
        for spot in available_spots:
            spot_key = f"{spot.university}_{spot.test_date}"
            if spot_key not in last_available_ids:
                logger.info(f"🆕 New spot found: {spot.university}")
                await notify_users_about_spot(spot)
    else:
        for spot in available_spots:
            logger.info(f"Initial spot found: {spot.university}")
            await notify_users_about_spot(spot)
    
    logger.info(f"Check complete. Found {len(available_spots)} available CENT@CASA spots.")


async def run_scraper_scheduler():
    """Run the scraper every 10 minutes"""
    global scraper_running
    scraper_running = True
    
    while scraper_running:
        try:
            await check_for_new_spots()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        await asyncio.sleep(600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 50)
    logger.info("🚀 Starting CEnT-S Alert System")
    logger.info("=" * 50)
    
    # Start scraper
    asyncio.create_task(run_scraper_scheduler())
    logger.info("✓ Scraper scheduler started (10 min interval)")
    
    # Start Telegram polling
    if TELEGRAM_BOT_TOKEN:
        asyncio.create_task(telegram_polling_loop())
        logger.info("✓ Telegram polling started")
    else:
        logger.warning("⚠ TELEGRAM_BOT_TOKEN not set - bot disabled")
    
    yield
    
    global scraper_running, telegram_polling_running
    scraper_running = False
    telegram_polling_running = False
    client.close()
    logger.info("System shutdown complete")


app = FastAPI(lifespan=lifespan)
api_router = APIRouter(prefix="/api")

# ========== AUTH HELPERS ==========

async def get_current_user(request: Request) -> Optional[dict]:
    """Get current user from session token"""
    session_token = request.cookies.get('session_token')
    
    if not session_token:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            session_token = auth_header.split(' ')[1]
    
    if not session_token:
        return None
    
    session_doc = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if not session_doc:
        return None
    
    expires_at = session_doc.get('expires_at')
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        return None
    
    user = await db.users.find_one(
        {"user_id": session_doc['user_id']},
        {"_id": 0}
    )
    
    return user

# ========== AUTH ROUTES ==========

@api_router.post("/auth/session")
async def exchange_session(request: Request, response: Response):
    """Exchange session_id for session_token"""
    body = await request.json()
    session_id = body.get('session_id')
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    try:
        async with httpx.AsyncClient() as http_client:
            auth_response = await http_client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id}
            )
            auth_response.raise_for_status()
            auth_data = auth_response.json()
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail="Invalid session_id")
    
    email = auth_data.get('email')
    name = auth_data.get('name')
    picture = auth_data.get('picture')
    session_token = auth_data.get('session_token')
    
    existing_user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if existing_user:
        user_id = existing_user['user_id']
        await db.users.update_one(
            {"email": email},
            {"$set": {"name": name, "picture": picture}}
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        new_user = User(
            user_id=user_id,
            email=email,
            name=name,
            picture=picture
        )
        user_doc = new_user.model_dump()
        user_doc['created_at'] = user_doc['created_at'].isoformat()
        await db.users.insert_one(user_doc)
    
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    session = UserSession(
        session_token=session_token,
        user_id=user_id,
        expires_at=expires_at
    )
    session_doc = session.model_dump()
    session_doc['expires_at'] = session_doc['expires_at'].isoformat()
    session_doc['created_at'] = session_doc['created_at'].isoformat()
    await db.user_sessions.insert_one(session_doc)
    
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7*24*60*60
    )
    
    return {
        "user": user,
        "needs_telegram": not user.get('telegram_chat_id')
    }

@api_router.get("/auth/me")
async def get_me(request: Request):
    """Get current user"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user"""
    session_token = request.cookies.get('session_token')
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    
    response.delete_cookie(
        key="session_token",
        path="/",
        secure=True,
        samesite="none"
    )
    return {"status": "logged_out"}

# ========== USER ROUTES ==========

@api_router.post("/users/telegram")
async def connect_telegram(request: Request, telegram_data: TelegramConnectRequest):
    """Connect user's Telegram account"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    await db.users.update_one(
        {"user_id": user['user_id']},
        {"$set": {"telegram_chat_id": telegram_data.chat_id, "alert_telegram": True}}
    )
    
    # Send welcome message
    welcome_text = (
        "✅ <b>Connected to CEnT-S Alert!</b>\n\n"
        "You will now receive instant notifications when CENT@CASA spots become available.\n\n"
        "Use /status to check bot status anytime."
    )
    await telegram_send_message(telegram_data.chat_id, welcome_text)
    
    updated_user = await db.users.find_one({"user_id": user['user_id']}, {"_id": 0})
    return updated_user

@api_router.put("/users/alerts")
async def update_alert_settings(request: Request, settings: AlertSettingsRequest):
    """Update user alert preferences"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    await db.users.update_one(
        {"user_id": user['user_id']},
        {"$set": {"alert_telegram": settings.alert_telegram}}
    )
    
    updated_user = await db.users.find_one({"user_id": user['user_id']}, {"_id": 0})
    return updated_user

# ========== TELEGRAM BOT INFO ==========

@api_router.get("/telegram/bot-info")
async def get_bot_info():
    """Get Telegram bot username for connection link"""
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Telegram bot not configured")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            response = await http.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe")
            data = response.json()
            
            if data.get("ok"):
                bot = data.get("result", {})
                return {
                    "username": bot.get("username"),
                    "name": bot.get("first_name")
                }
    except Exception as e:
        logger.error(f"Failed to get bot info: {e}")
    
    raise HTTPException(status_code=503, detail="Failed to get bot info")

# ========== AVAILABILITY ROUTES ==========

@api_router.get("/availability")
async def get_current_availability():
    """Get current CENT@CASA availability"""
    snapshot = await db.availability_snapshots.find_one(
        {},
        {"_id": 0},
        sort=[("timestamp", -1)]
    )
    
    if not snapshot:
        spots = await scrape_cisia_page()
        available_spots = [s for s in spots if "DISPONIBILI" in s.status.upper()]
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "spots": [s.model_dump() for s in spots],
            "available_count": len(available_spots),
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
    """Get availability check history"""
    snapshots = await db.availability_snapshots.find(
        {},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return snapshots

@api_router.post("/availability/refresh")
async def refresh_availability(background_tasks: BackgroundTasks, request: Request):
    """Manually trigger availability check"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    background_tasks.add_task(check_for_new_spots)
    return {"status": "refresh_started"}

# ========== NOTIFICATION ROUTES ==========

@api_router.get("/notifications/history")
async def get_notification_history(request: Request, limit: int = 50):
    """Get user's notification history"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    notifications = await db.notifications.find(
        {"user_id": user['user_id']},
        {"_id": 0}
    ).sort("sent_at", -1).limit(limit).to_list(limit)
    
    return notifications

# ========== HEALTH CHECK ==========

@api_router.get("/")
async def root():
    return {"message": "CEnT-S Alert API", "status": "running"}

@api_router.get("/health")
async def health():
    return {
        "status": "healthy", 
        "scraper_running": scraper_running,
        "telegram_polling": telegram_polling_running,
        "telegram_configured": TELEGRAM_BOT_TOKEN is not None
    }

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
