# CEnT-S Alert Bot - Deploy to Render.com (FREE)

## 🚀 5-Minute Deployment Guide

### Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Name it `cisia-alert-bot`
3. Make it **Private** (recommended)
4. Click "Create repository"

### Step 2: Upload Bot Files

Upload these 3 files to your repo:
- `bot.py` (the main bot code)
- `requirements.txt` (dependencies)
- `Procfile` (tells Render how to run it)

Or use GitHub's "Add file" → "Upload files"

### Step 3: Deploy on Render.com

1. Go to https://render.com and sign up (free)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account
4. Select your `cisia-alert-bot` repository
5. Configure:
   - **Name**: `cisia-alert-bot`
   - **Region**: Frankfurt (EU) or closest to you
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Instance Type**: **Free**

### Step 4: Add Environment Variables

In Render dashboard, go to "Environment" and add:

| Key | Value |
|-----|-------|
| `TELEGRAM_BOT_TOKEN` | `8217615355:AAG7elm2EnMZk6SEaX4fstugYdM1jhm6dbo` |
| `WEBHOOK_URL` | `https://cisia-alert-bot.onrender.com` (your Render URL) |

### Step 5: Deploy!

1. Click **"Create Web Service"**
2. Wait 2-3 minutes for deployment
3. Your bot is now running 24/7!

---

## ✅ Test Your Bot

1. Open Telegram
2. Search for `@CISIA_MONITOR_BOT`
3. Send `/start`
4. You should get your Chat ID **instantly, every time**

---

## 🔧 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Get Chat ID + Subscribe to alerts |
| `/status` | Check bot status & available spots |
| `/check` | Manually check for spots now |
| `/id` | Show your Chat ID |
| `/stop` | Unsubscribe from alerts |
| `/help` | Show all commands |

---

## 🆓 Why Render.com?

- **Free tier**: 750 hours/month (enough for 24/7)
- **Always on**: No sleeping like Heroku
- **Auto-deploy**: Push to GitHub = automatic update
- **SSL included**: HTTPS works out of the box

---

## ⚠️ Important Notes

1. **Free tier spins down after 15 min of inactivity** - but incoming webhooks wake it up instantly (< 1 second)

2. **For truly zero-downtime**, upgrade to $7/mo "Starter" plan

3. **Subscribers are stored in memory** - they'll reset if bot restarts. For persistence, add MongoDB (instructions below)

---

## 📦 Optional: Add MongoDB for Persistence

1. Go to https://mongodb.com/atlas (free tier)
2. Create a cluster
3. Get connection string
4. Add to Render environment: `MONGODB_URI=mongodb+srv://...`
5. Update bot.py to use MongoDB instead of in-memory set

---

## 🆘 Troubleshooting

**Bot not responding?**
- Check Render logs for errors
- Verify `TELEGRAM_BOT_TOKEN` is correct
- Make sure `WEBHOOK_URL` matches your Render URL exactly

**Webhook errors?**
- Render free tier may take 1-2 seconds to wake up
- This is normal and Telegram will retry automatically

---

## 📞 Support

If issues persist after deploying to Render:
1. Check Render logs (Dashboard → Logs)
2. Verify environment variables are set
3. Test with `/status` command first
