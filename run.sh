#!/bin/bash

# CocoGuard Backend Startup Script for Linux/Mac

echo ""
echo "================================================"
echo "     CocoGuard Backend - Startup Script"
echo "================================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "[!] Virtual environment not found!"
    echo "[*] Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment"
        exit 1
    fi
    echo "[+] Virtual environment created"
fi

# Activate virtual environment
echo "[*] Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to activate virtual environment"
    exit 1
fi

# Check if requirements are installed
echo "[*] Checking dependencies..."
pip show fastapi > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "[*] Installing dependencies..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to install dependencies"
        exit 1
    fi
    echo "[+] Dependencies installed"
fi

# Create .env if not exists
if [ ! -f ".env" ]; then
    echo "[*] Creating .env file from template..."
    cp .env.example .env
    echo "[+] Created .env file - please review and update if needed"
fi

# Create uploads directory
if [ ! -d "uploads" ]; then
    echo "[*] Creating uploads directory..."
    mkdir -p uploads
    echo "[+] Uploads directory created"
fi

# Start the server
echo ""
echo "[+] Starting CocoGuard Backend API..."
echo "[+] API will be available at: http://localhost:8000"
echo "[+] API Documentation at: http://localhost:8000/docs"
echo ""
echo "[*] Press Ctrl+C to stop the server"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
