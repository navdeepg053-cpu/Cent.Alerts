from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import httpx
import asyncio
import resend
from twilio.rest import Client as TwilioClient
from bs4 import BeautifulSoup
from contextlib import asynccontextmanager

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

# Initialize Resend
resend_api_key = os.environ.get('RESEND_API_KEY')
if resend_api_key:
    resend.api_key = resend_api_key

# Initialize Twilio
twilio_account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
twilio_auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
twilio_phone_number = os.environ.get('TWILIO_PHONE_NUMBER')
twilio_whatsapp_number = os.environ.get('TWILIO_WHATSAPP_NUMBER')
twilio_client = None
if twilio_account_sid and twilio_auth_token:
    twilio_client = TwilioClient(twilio_account_sid, twilio_auth_token)

SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
CISIA_URL = "https://testcisia.it/calendario.php?tolc=cents&lingua=inglese"

# Background scraper state
scraper_running = False

# ========== MODELS ==========

class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    phone: Optional[str] = None
    alert_email: bool = True
    alert_sms: bool = False
    alert_whatsapp: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserSession(BaseModel):
    session_token: str
    user_id: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PhoneUpdateRequest(BaseModel):
    phone: str

class AlertSettingsRequest(BaseModel):
    alert_email: bool
    alert_sms: bool
    alert_whatsapp: bool

class AvailabilitySpot(BaseModel):
    spot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str  # CENT@CASA or CENT@UNI
    university: str
    region: str
    city: str
    registration_deadline: str
    spots: str  # number or "---"
    status: str  # "POSTI DISPONIBILI" or "POSTI ESAURITI"
    test_date: str

class AvailabilitySnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    spots: List[AvailabilitySpot]
    available_count: int = 0

class Notification(BaseModel):
    notification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    type: str  # email, sms, whatsapp
    message: str
    spot_info: Optional[dict] = None
    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "sent"

# ========== SCRAPER FUNCTIONS ==========

async def scrape_cisia_page() -> List[AvailabilitySpot]:
    """Scrape the CISIA calendar page for CENT@CASA availability"""
    spots = []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(CISIA_URL)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find the table with test dates
            table = soup.find('table')
            if not table:
                logger.warning("No table found on CISIA page")
                return spots
            
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 7:
                    # Parse the row data
                    test_type = cells[0].get_text(strip=True)
                    university = cells[1].get_text(strip=True)
                    region = cells[2].get_text(strip=True)
                    city = cells[3].get_text(strip=True)
                    reg_deadline = cells[4].get_text(strip=True)
                    spots_num = cells[5].get_text(strip=True)
                    status_cell = cells[6]
                    test_date = cells[7].get_text(strip=True) if len(cells) > 7 else ""
                    
                    # Determine status
                    status_link = status_cell.find('a')
                    if status_link:
                        status = "POSTI DISPONIBILI"
                    else:
                        status = status_cell.get_text(strip=True)
                    
                    # Only track CENT@CASA spots
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

async def send_email_notification(user: dict, spot: AvailabilitySpot):
    """Send email notification about available spot"""
    if not resend_api_key:
        logger.warning("Resend API key not configured, skipping email")
        return False
    
    try:
        html_content = f"""
        <div style="font-family: 'Inter', sans-serif; background-color: #050505; color: white; padding: 40px;">
            <h1 style="color: #00FF94; font-family: 'JetBrains Mono', monospace;">CEnT-S Spot Available!</h1>
            <p>A new spot has opened for the CEnT-S entrance test:</p>
            <div style="background-color: #0A0A0A; border: 1px solid #27272A; padding: 20px; margin: 20px 0;">
                <p><strong style="color: #00FF94;">University:</strong> {spot.university}</p>
                <p><strong style="color: #00FF94;">Location:</strong> {spot.city}, {spot.region}</p>
                <p><strong style="color: #00FF94;">Test Date:</strong> {spot.test_date}</p>
                <p><strong style="color: #00FF94;">Registration Deadline:</strong> {spot.registration_deadline}</p>
                <p><strong style="color: #00FF94;">Available Spots:</strong> {spot.spots}</p>
            </div>
            <p>Register now at: <a href="https://testcisia.it/studenti_tolc/login_sso.php" style="color: #00FF94;">CISIA Portal</a></p>
        </div>
        """
        
        params = {
            "from": SENDER_EMAIL,
            "to": [user['email']],
            "subject": f"🟢 CEnT-S Spot Available - {spot.university}",
            "html": html_content
        }
        
        await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Email sent to {user['email']}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

async def send_sms_notification(user: dict, spot: AvailabilitySpot):
    """Send SMS notification about available spot"""
    if not twilio_client or not twilio_phone_number:
        logger.warning("Twilio not configured, skipping SMS")
        return False
    
    if not user.get('phone'):
        logger.warning(f"User {user['user_id']} has no phone number")
        return False
    
    try:
        message = f"CEnT-S SPOT AVAILABLE!\n{spot.university}\n{spot.city}\nDeadline: {spot.registration_deadline}\nBook now: testcisia.it"
        
        await asyncio.to_thread(
            twilio_client.messages.create,
            body=message,
            from_=twilio_phone_number,
            to=user['phone']
        )
        logger.info(f"SMS sent to {user['phone']}")
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")
        return False

async def send_whatsapp_notification(user: dict, spot: AvailabilitySpot):
    """Send WhatsApp notification about available spot"""
    if not twilio_client or not twilio_whatsapp_number:
        logger.warning("Twilio WhatsApp not configured, skipping")
        return False
    
    if not user.get('phone'):
        logger.warning(f"User {user['user_id']} has no phone number")
        return False
    
    try:
        message = f"🟢 *CEnT-S SPOT AVAILABLE!*\n\n*University:* {spot.university}\n*Location:* {spot.city}, {spot.region}\n*Test Date:* {spot.test_date}\n*Deadline:* {spot.registration_deadline}\n*Spots:* {spot.spots}\n\n➡️ Book now: testcisia.it"
        
        await asyncio.to_thread(
            twilio_client.messages.create,
            body=message,
            from_=f"whatsapp:{twilio_whatsapp_number}",
            to=f"whatsapp:{user['phone']}"
        )
        logger.info(f"WhatsApp sent to {user['phone']}")
        return True
    except Exception as e:
        logger.error(f"Failed to send WhatsApp: {e}")
        return False

async def notify_users_about_spot(spot: AvailabilitySpot):
    """Notify all users with alerts enabled about an available spot"""
    users = await db.users.find({"_id": 0}).to_list(1000)
    
    for user in users:
        notifications_sent = []
        
        if user.get('alert_email', True):
            if await send_email_notification(user, spot):
                notifications_sent.append('email')
        
        if user.get('alert_sms', False):
            if await send_sms_notification(user, spot):
                notifications_sent.append('sms')
        
        if user.get('alert_whatsapp', False):
            if await send_whatsapp_notification(user, spot):
                notifications_sent.append('whatsapp')
        
        # Log notifications
        for notif_type in notifications_sent:
            notification = Notification(
                user_id=user['user_id'],
                type=notif_type,
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
    
    # Get the last snapshot
    last_snapshot = await db.availability_snapshots.find_one(
        {},
        {"_id": 0},
        sort=[("timestamp", -1)]
    )
    
    # Store current snapshot
    snapshot = AvailabilitySnapshot(
        spots=spots,
        available_count=len(available_spots)
    )
    snapshot_doc = snapshot.model_dump()
    snapshot_doc['timestamp'] = snapshot_doc['timestamp'].isoformat()
    snapshot_doc['spots'] = [s.model_dump() for s in spots]
    await db.availability_snapshots.insert_one(snapshot_doc)
    
    # Check for newly available spots
    if last_snapshot:
        last_available_ids = set()
        for s in last_snapshot.get('spots', []):
            if "DISPONIBILI" in s.get('status', '').upper():
                last_available_ids.add(f"{s.get('university')}_{s.get('test_date')}")
        
        for spot in available_spots:
            spot_key = f"{spot.university}_{spot.test_date}"
            if spot_key not in last_available_ids:
                # New spot available! Notify users
                logger.info(f"New spot found: {spot.university}")
                await notify_users_about_spot(spot)
    else:
        # First run - notify about all available spots
        for spot in available_spots:
            logger.info(f"Initial spot found: {spot.university}")
            await notify_users_about_spot(spot)
    
    logger.info(f"Check complete. Found {len(available_spots)} available CENT@CASA spots.")

# Background scheduler
async def run_scheduler():
    """Run the scraper every 10 minutes"""
    global scraper_running
    scraper_running = True
    
    while scraper_running:
        try:
            await check_for_new_spots()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        
        # Wait 10 minutes
        await asyncio.sleep(600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting CEnT-S Alert System...")
    # Start background scraper
    asyncio.create_task(run_scheduler())
    yield
    # Shutdown
    global scraper_running
    scraper_running = False
    client.close()

# Create the main app
app = FastAPI(lifespan=lifespan)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ========== AUTH HELPERS ==========

async def get_current_user(request: Request) -> Optional[dict]:
    """Get current user from session token"""
    # Check cookie first
    session_token = request.cookies.get('session_token')
    
    # Fallback to Authorization header
    if not session_token:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            session_token = auth_header.split(' ')[1]
    
    if not session_token:
        return None
    
    # Find session
    session_doc = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if not session_doc:
        return None
    
    # Check expiry
    expires_at = session_doc.get('expires_at')
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        return None
    
    # Get user
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
    
    # Call Emergent auth to get user data
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
    
    # Check if user exists
    existing_user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if existing_user:
        user_id = existing_user['user_id']
        # Update user info
        await db.users.update_one(
            {"email": email},
            {"$set": {"name": name, "picture": picture}}
        )
    else:
        # Create new user
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
    
    # Store session
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
    
    # Get updated user
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    
    # Set cookie
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
        "needs_phone": not user.get('phone')
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

@api_router.post("/users/phone")
async def update_phone(request: Request, phone_data: PhoneUpdateRequest):
    """Update user phone number"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    await db.users.update_one(
        {"user_id": user['user_id']},
        {"$set": {"phone": phone_data.phone}}
    )
    
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
        {"$set": {
            "alert_email": settings.alert_email,
            "alert_sms": settings.alert_sms,
            "alert_whatsapp": settings.alert_whatsapp
        }}
    )
    
    updated_user = await db.users.find_one({"user_id": user['user_id']}, {"_id": 0})
    return updated_user

# ========== AVAILABILITY ROUTES ==========

@api_router.get("/availability")
async def get_current_availability():
    """Get current CENT@CASA availability"""
    # Get the latest snapshot
    snapshot = await db.availability_snapshots.find_one(
        {},
        {"_id": 0},
        sort=[("timestamp", -1)]
    )
    
    if not snapshot:
        # No data yet, do a fresh scrape
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
    return {"status": "healthy", "scraper_running": scraper_running}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
