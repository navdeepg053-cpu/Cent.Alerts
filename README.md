# Cent.Alerts

A real-time alert system for CISIA CENT@CASA exam spot availability. Get instant notifications when exam spots open up!

## Features

- 🔔 **Real-time Alerts**: Get notified instantly when exam spots become available
- 📱 **Telegram Integration**: Receive alerts directly in Telegram
- 🔐 **Google OAuth**: Secure authentication
- 📊 **Dashboard**: View available spots and notification history
- 🤖 **Dual-mode Bot**: Webhook with automatic polling fallback
- 📈 **Historical Data**: Track spot availability over time

## Quick Start

### Deploy to Render.com

This application is ready for one-click deployment on Render.com!

👉 **[See Deployment Guide](DEPLOYMENT.md)** for detailed instructions.

### Prerequisites

- MongoDB database (e.g., MongoDB Atlas)
- Telegram bot token (create via [@BotFather](https://t.me/botfather))
- Render.com account (or Docker)

### Environment Variables

See [backend/.env.example](backend/.env.example) and [frontend/.env.example](frontend/.env.example) for required configuration.

## Development

### Local Development

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env  # Edit with your values
uvicorn server:app --reload

# Frontend (in another terminal)
cd frontend
yarn install
cp .env.example .env  # Edit with your values
yarn start
```

### Docker

```bash
# Build and run
docker build -t cents-alerts .
docker run -p 8000:8000 \
  -e MONGO_URL="your-mongo-url" \
  -e DB_NAME="your-db" \
  -e TELEGRAM_BOT_TOKEN="your-token" \
  -e REACT_APP_BACKEND_URL="http://localhost:8000" \
  cents-alerts
```

## Architecture

- **Frontend**: React with Tailwind CSS
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Deployment**: Docker + Render.com

## Documentation

- [Deployment Guide](DEPLOYMENT.md) - Deploy to Render.com
- [Deployment Summary](DEPLOYMENT_SUMMARY.md) - Technical details and changes

## License

MIT License

