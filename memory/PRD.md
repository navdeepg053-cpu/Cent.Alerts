# CEnT-S Alert System v2 - Setup & Deployment Guide

## 🚀 SYSTEM OVERVIEW

A **bulletproof** monitoring system for CISIA CENT@CASA test spots with:
- **Webhook-based Telegram bot** (instant responses, no polling)
- **Auto-healing health checker** (repairs webhook every 30s if needed)
- **30-second scraper** (checks CISIA continuously)
- **Google OAuth** authentication
- **MongoDB** for data persistence

---

## 📋 ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                    CEnT-S Alert System v2                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   SCRAPER   │    │  TELEGRAM   │    │   HEALTH    │     │
│  │  (30s loop) │    │  WEBHOOK    │    │  CHECKER    │     │
│  │             │    │  (instant)  │    │  (30s loop) │     │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘     │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            │                                │
│                    ┌───────▼───────┐                        │
│                    │   FastAPI     │                        │
│                    │   Backend     │                        │
│                    └───────┬───────┘                        │
│                            │                                │
│         ┌──────────────────┼──────────────────┐             │
│         │                  │                  │             │
│  ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐     │
│  │   MongoDB   │    │  Telegram   │    │   React     │     │
│  │   Database  │    │   API       │    │  Frontend   │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 CONFIGURATION

### Environment Variables (backend/.env)

```env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="test_database"
CORS_ORIGINS="*"
TELEGRAM_BOT_TOKEN="your_bot_token_here"
WEBHOOK_SECRET="random_secret_string"
REACT_APP_BACKEND_URL="https://your-domain.com"
```

### Telegram Bot Setup

1. Message @BotFather on Telegram
2. Send `/newbot`
3. Name: `CEnT-S Alert` (or similar)
4. Username: Must end with `bot`, e.g., `cents_alert_bot`
5. Copy the token and add to `.env`

---

## 📡 WEBHOOK SYSTEM

### How It Works

1. **On Startup**: System registers webhook with Telegram
2. **When User Messages**: Telegram POSTs to our webhook endpoint
3. **Processing**: We handle message and respond instantly
4. **Health Check**: Every 30s, verifies webhook is working
5. **Auto-Repair**: If issues detected, re-registers webhook

### Webhook Endpoint

```
POST /api/telegram/webhook/{WEBHOOK_SECRET}
```

The secret path prevents unauthorized access.

---

## 🏥 HEALTH MONITORING

### What It Checks (every 30 seconds)

- ✅ Webhook URL is correct
- ✅ No error messages from Telegram
- ✅ Pending updates count is reasonable
- ✅ Webhook task is alive

### Auto-Recovery Actions

1. Delete old webhook
2. Wait 1 second
3. Set new webhook
4. Verify with `getWebhookInfo`
5. Log recovery attempt

### Health Endpoint

```bash
GET /api/health
```

Returns:
```json
{
  "status": "healthy",
  "version": "2.0-webhook",
  "uptime_seconds": 3600,
  "webhook": {
    "registered": true,
    "url": "https://...",
    "last_check_ago": 15.2
  },
  "health_checks": {
    "passed": 120,
    "failed": 0,
    "auto_recoveries": 1
  }
}
```

---

## 🤖 BOT COMMANDS

| Command | Description |
|---------|-------------|
| `/start` | Get your Chat ID (for connecting) |
| `/status` | Check bot status & uptime |
| `/id` | Show your Chat ID |
| `/help` | List all commands |
| `/stop` | Disable alerts |

---

## 🔍 SCRAPER

Checks CISIA every **30 seconds** for:
- CENT@CASA spots only (filters out CENT@UNI)
- Detects newly available spots
- Sends Telegram alerts to subscribed users

---

## 🚨 EMERGENCY ENDPOINTS

### Force Webhook Re-registration

```bash
POST /api/telegram/force-reregister
```

Use if bot stops responding despite health checks passing.

---

## 📊 DATABASE COLLECTIONS

| Collection | Purpose |
|------------|---------|
| `users` | User accounts, telegram_chat_id, alert preferences |
| `user_sessions` | Authentication sessions |
| `availability_snapshots` | Historical scraper data |
| `notifications` | Alert history |

---

## 🧪 TESTING

### Verify Webhook

```bash
# Check Telegram's view of webhook
curl "https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
```

### Verify Bot

1. Open Telegram
2. Search `@CISIA_MONITOR_BOT`
3. Send `/start`
4. Should receive Chat ID instantly

### Verify Health

```bash
curl https://your-domain.com/api/health
```

---

## 🐛 TROUBLESHOOTING

### Bot Not Responding

1. Check `/api/health` - is webhook registered?
2. Check Telegram webhook info - any errors?
3. Call `/api/telegram/force-reregister`
4. Check backend logs for errors

### Webhook 404 Errors

- Server may have restarted
- Health checker will auto-repair within 30s
- Or manually call force-reregister

### Rate Limiting (429)

- Bot handles automatically with retry_after
- Reduce message frequency if persistent

---

## ✅ SUCCESS CRITERIA

The system is healthy when:
- `health_checks.passed` increases every 30s
- `health_checks.failed` stays at 0
- `auto_recoveries` is low (< 10/hour)
- `/start` responds within 2 seconds
- Scraper runs every 30 seconds

---

## 📝 CURRENT STATUS

- **Bot**: @CISIA_MONITOR_BOT
- **Version**: 2.0-webhook
- **Scraper Interval**: 30 seconds
- **Health Check Interval**: 30 seconds
- **CENT@CASA Sessions**: 23 (all full currently)
