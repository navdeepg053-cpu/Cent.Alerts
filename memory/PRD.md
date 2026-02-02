# CEnT-S Alert - Product Requirements Document

## Original Problem Statement
Build a website that alerts whenever there's an opening for the CEnT-S Italian university entrance test available. Monitor https://testcisia.it/calendario.php?tolc=cents&lingua=inglese and only track CENT@CASA (home-based) spots. Users sign up and receive real-time alerts when spots become available.

## User Personas
1. **International Students** - Students from various countries applying to Italian universities who need CENT@CASA test spots
2. **Italian Students** - Local students preferring home-based testing options

## Core Requirements
- Monitor CISIA calendar page every 10 minutes
- Filter only CENT@CASA sessions (not CENT@UNI)
- Detect newly available spots
- Send instant Telegram notifications to subscribed users
- Google OAuth authentication
- Notification history tracking

## What's Been Implemented (Feb 2, 2026)

### Backend (FastAPI + MongoDB)
- ✅ Web scraper for CISIA calendar page (Beautiful Soup + lxml)
- ✅ Background scheduler running every 10 minutes
- ✅ Google OAuth via Emergent Auth
- ✅ Telegram Bot integration for instant alerts
- ✅ User management (create, update, alert settings)
- ✅ Notification logging and history
- ✅ Session management with secure cookies

### Frontend (React + Tailwind)
- ✅ Landing page with value proposition
- ✅ Google OAuth login flow
- ✅ Dashboard showing all CENT@CASA sessions
- ✅ Real-time status display (available vs full)
- ✅ Telegram connection setup flow
- ✅ Alert toggle settings
- ✅ Notification history page
- ✅ Dark neon theme (Electric aesthetic)

### Integrations
- ✅ Telegram Bot (@centstest_alert_bot) - FREE instant notifications
- ✅ Emergent Google OAuth

## Database Schema
- `users`: user_id, email, name, picture, telegram_chat_id, alert_telegram
- `user_sessions`: session_token, user_id, expires_at
- `availability_snapshots`: timestamp, spots[], available_count
- `notifications`: user_id, type, message, spot_info, sent_at, status

## API Endpoints
- `GET /api/health` - Health check
- `POST /api/auth/session` - OAuth exchange
- `GET /api/auth/me` - Get current user
- `POST /api/auth/logout` - Logout
- `POST /api/users/telegram` - Connect Telegram
- `PUT /api/users/alerts` - Update alert settings
- `GET /api/availability` - Current availability
- `POST /api/availability/refresh` - Manual refresh
- `GET /api/notifications/history` - User's notification history
- `GET /api/telegram/bot-info` - Get bot username

## Prioritized Backlog

### P0 (Done)
- [x] Core scraping functionality
- [x] User authentication
- [x] Telegram notifications
- [x] Dashboard UI

### P1 (Future)
- [ ] Email notifications (add Resend when needed)
- [ ] Multiple alert channels per user
- [ ] Specific university/location filters

### P2 (Future)
- [ ] Browser push notifications
- [ ] Mobile app
- [ ] Alert scheduling (quiet hours)

## Next Tasks
1. Test real Telegram notifications when spots actually open
2. Consider adding email as backup channel
3. Add user preferences for specific universities
