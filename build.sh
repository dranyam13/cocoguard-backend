#!/bin/bash
# Render Build Script for CocoGuard Backend
# This script is run during the build phase on Render

set -e  # Exit on any error

echo "=== CocoGuard Backend Build Script ==="

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "Creating directories..."
mkdir -p uploads/files
mkdir -p uploads/scans
mkdir -p app/model

# Copy model files if they exist in the repo
# Note: For Render, model files should be in the 'model' directory at repo root
if [ -d "model" ]; then
    echo "Copying model files..."
    cp -r model/* app/model/ 2>/dev/null || true
fi

# Initialize database
echo "Initializing database..."
python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)" || true

echo "=== Build complete ==="
