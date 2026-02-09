# CEnT-S Telegram Bot - Standalone Version
# Deploy this to Render.com for FREE 24/7 uptime

import os
import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import httpx
from bs4 import BeautifulSoup

# ========== CONFIGURATION ==========
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
MONGODB_URI = os.environ.get("MONGODB_URI", "")  # Optional - for storing subscribers
PORT = int(os.environ.get("PORT", 8080))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")  # e.g., https://your-app.onrender.com

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# In-memory subscriber storage (use MongoDB for persistence)
subscribers = set()

# ========== SCRAPER ==========
CISIA_URL = "https://testcisia.it/calendario.php?tolc=cents&lingua=inglese"

async def scrape_cisia():
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
                            has_link = cells[6].find('a') is not None
                            spots.append({
                                "university": cells[1].get_text(strip=True),
                                "city": cells[3].get_text(strip=True),
                                "deadline": cells[4].get_text(strip=True),
                                "spots": cells[5].get_text(strip=True),
                                "available": has_link,
                                "test_date": cells[7].get_text(strip=True) if len(cells) > 7 else ""
                            })
    except Exception as e:
        logger.error(f"Scrape error: {e}")
    return spots

# ========== BOT HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - send chat ID."""
    chat_id = update.effective_chat.id
    name = update.effective_user.first_name
    
    subscribers.add(chat_id)
    
    await update.message.reply_html(
        f"👋 <b>Welcome, {name}!</b>\n\n"
        f"🔑 Your Chat ID:\n<code>{chat_id}</code>\n\n"
        f"👆 Tap to copy, paste in the app!\n\n"
        f"✅ You're now subscribed to CENT@CASA alerts!"
    )
    logger.info(f"New subscriber: {chat_id}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    chat_id = update.effective_chat.id
    spots = await scrape_cisia()
    available = [s for s in spots if s["available"]]
    
    await update.message.reply_html(
        f"🤖 <b>Bot Status: ONLINE</b>\n\n"
        f"📊 CENT@CASA Sessions: {len(spots)}\n"
        f"✅ Available spots: {len(available)}\n"
        f"👥 Subscribers: {len(subscribers)}\n\n"
        f"Your ID: <code>{chat_id}</code>"
    )


async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /id command."""
    chat_id = update.effective_chat.id
    await update.message.reply_html(f"🔑 <code>{chat_id}</code>")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_html(
        "🤖 <b>CEnT-S Alert Bot</b>\n\n"
        "/start - Get your Chat ID & subscribe\n"
        "/status - Check bot & spot status\n"
        "/id - Show your Chat ID\n"
        "/check - Check for available spots now\n"
        "/stop - Unsubscribe from alerts"
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stop command."""
    chat_id = update.effective_chat.id
    subscribers.discard(chat_id)
    await update.message.reply_text("🔕 You've been unsubscribed. Send /start to re-subscribe.")


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /check command - check spots now."""
    await update.message.reply_text("🔍 Checking CISIA...")
    
    spots = await scrape_cisia()
    available = [s for s in spots if s["available"]]
    
    if available:
        msg = "🟢 <b>SPOTS AVAILABLE!</b>\n\n"
        for s in available:
            msg += f"🏫 {s['university']}\n📍 {s['city']}\n📅 {s['test_date']}\n🎫 {s['spots']}\n\n"
        msg += "👉 <a href='https://testcisia.it/studenti_tolc/login_sso.php'>BOOK NOW</a>"
    else:
        msg = f"🔴 No spots available.\n\nTotal CENT@CASA sessions: {len(spots)}\nAll currently full."
    
    await update.message.reply_html(msg)


async def handle_any(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any other message."""
    chat_id = update.effective_chat.id
    await update.message.reply_html(
        f"Your Chat ID: <code>{chat_id}</code>\n"
        f"Send /help for commands."
    )


# ========== BACKGROUND SCRAPER ==========
last_available = set()

async def check_and_alert(app):
    """Check for new spots and alert subscribers."""
    global last_available
    
    while True:
        try:
            spots = await scrape_cisia()
            available = {f"{s['university']}|{s['test_date']}" for s in spots if s["available"]}
            
            # Find NEW spots
            new_spots = available - last_available
            
            if new_spots and subscribers:
                # Get details of new spots
                for spot in spots:
                    key = f"{spot['university']}|{spot['test_date']}"
                    if key in new_spots:
                        msg = (
                            f"🟢 <b>NEW SPOT AVAILABLE!</b>\n\n"
                            f"🏫 {spot['university']}\n"
                            f"📍 {spot['city']}\n"
                            f"📅 {spot['test_date']}\n"
                            f"⏰ Deadline: {spot['deadline']}\n"
                            f"🎫 Spots: {spot['spots']}\n\n"
                            f"👉 <a href='https://testcisia.it/studenti_tolc/login_sso.php'>BOOK NOW!</a>"
                        )
                        
                        for chat_id in subscribers.copy():
                            try:
                                await app.bot.send_message(chat_id, msg, parse_mode="HTML")
                                logger.info(f"Alert sent to {chat_id}")
                            except Exception as e:
                                logger.error(f"Failed to send to {chat_id}: {e}")
                                subscribers.discard(chat_id)
            
            last_available = available
            logger.info(f"Check done: {len(available)} available, {len(subscribers)} subscribers")
            
        except Exception as e:
            logger.error(f"Check error: {e}")
        
        await asyncio.sleep(30)  # Check every 30 seconds


# ========== MAIN ==========
def main():
    """Start the bot."""
    logger.info("Starting CEnT-S Alert Bot...")
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_any))
    
    # Start background scraper
    async def post_init(application):
        asyncio.create_task(check_and_alert(application))
    
    app.post_init = post_init
    
    # Run with webhook or polling
    if WEBHOOK_URL:
        logger.info(f"Starting webhook mode: {WEBHOOK_URL}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
        )
    else:
        logger.info("Starting polling mode")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
