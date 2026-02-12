#!/bin/bash
# Build script for production deployment
# This script builds the frontend with environment variables

# Set default backend URL to empty string for same-origin deployment
export REACT_APP_BACKEND_URL=${REACT_APP_BACKEND_URL:-""}

echo "Building frontend with REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL"

# Navigate to frontend directory
cd /app/frontend

# Build the frontend
yarn build

echo "Frontend build complete!"
