# Deployment Guide for Render.com

This guide explains how to deploy the Cent.Alerts application on Render.com.

## Overview

The application uses a **single-server architecture** where:
- The React frontend is built during the Docker build process
- The FastAPI backend serves both the API and the static frontend files
- Everything runs on a single port (configurable via the `PORT` environment variable)

## Prerequisites

1. A Render.com account
2. A MongoDB database (e.g., MongoDB Atlas)
3. A Telegram bot token (create one via [@BotFather](https://t.me/botfather))

## Deployment Steps

### 1. Prepare Your Environment Variables

You'll need to set the following environment variables in Render.com:

#### Required Variables:
- `MONGO_URL`: Your MongoDB connection string (e.g., `mongodb+srv://user:pass@cluster.mongodb.net/`)
- `DB_NAME`: Your MongoDB database name
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token from BotFather
- `REACT_APP_BACKEND_URL`: Your app's public URL (e.g., `https://your-app.onrender.com`)

#### Optional Variables:
- `PORT`: The port to run on (Render sets this automatically, default: 8000)
- `CORS_ORIGINS`: Comma-separated list of allowed CORS origins (default: `*`)

### 2. Create a New Web Service on Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: Choose a name for your app
   - **Environment**: `Docker`
   - **Region**: Choose your preferred region
   - **Branch**: Choose your deployment branch (e.g., `main`)
   - **Dockerfile Path**: Leave as default (it will find `./Dockerfile`)

### 3. Configure Environment Variables

In the "Environment" section, add all the required environment variables listed above.

**Important**: For `REACT_APP_BACKEND_URL`, use the URL that Render assigns to your service (e.g., `https://your-app.onrender.com`). You can get this after creating the service, then update the environment variable.

### 4. Deploy

1. Click "Create Web Service"
2. Render will automatically build and deploy your application
3. The build process will:
   - Build the React frontend
   - Install Python dependencies
   - Copy the built frontend to the backend
   - Start the FastAPI server with uvicorn

### 5. Update Telegram Bot Configuration

After deployment:
1. Visit `https://your-app.onrender.com/api/health` to verify the app is running
2. The webhook will be automatically registered with Telegram
3. Test by sending `/start` to your Telegram bot

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Render.com (Single Port)                 │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                 FastAPI Backend                       │   │
│  │  - Serves API routes (/api/*)                        │   │
│  │  - Serves static frontend files                      │   │
│  │  - Handles Telegram webhook                          │   │
│  │  - Runs background scraper                           │   │
│  └──────────────────────────────────────────────────────┘   │
│                         ↕                                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Frontend (React - Static Files)            │   │
│  │  - Served by FastAPI                                 │   │
│  │  - Built during Docker build                         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Local Testing

To test the Docker build locally:

```bash
# Build the Docker image
docker build -t cents-alerts .

# Run the container
docker run -p 8000:8000 \
  -e MONGO_URL="your-mongo-url" \
  -e DB_NAME="your-db-name" \
  -e TELEGRAM_BOT_TOKEN="your-token" \
  -e REACT_APP_BACKEND_URL="http://localhost:8000" \
  cents-alerts
```

Then visit `http://localhost:8000` in your browser.

## Troubleshooting

### Frontend not loading
- Check that the frontend build completed successfully in the logs
- Verify that `/api/health` returns a 200 status
- Check browser console for errors

### Telegram webhook not working
- Ensure `REACT_APP_BACKEND_URL` is set to your public Render URL
- Check `/api/health` endpoint to see webhook status
- Try the `/api/telegram/force-repair` endpoint to re-register the webhook

### Database connection issues
- Verify your MongoDB connection string is correct
- Ensure your MongoDB allows connections from Render's IP addresses
- Check MongoDB Atlas network access settings

## Monitoring

- **Health Check**: `GET /api/health` - Returns service status, uptime, and webhook info
- **Telegram Test**: Send `/status` to your bot to check if it's responding
- **Logs**: Check Render dashboard logs for detailed information

## Support

For issues with:
- **Render deployment**: Check [Render documentation](https://render.com/docs)
- **Application issues**: Check the application logs in Render dashboard
- **MongoDB**: Check [MongoDB Atlas documentation](https://docs.atlas.mongodb.com/)
