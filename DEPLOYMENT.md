# CocoGuard Deployment Guide

This guide explains how to deploy CocoGuard on **Render** (recommended) for both the backend API and web frontend.

## Overview

| Component | Service | URL Pattern |
|-----------|---------|-------------|
| Backend API | Render Web Service | `https://cocoguard-api.onrender.com` |
| Web Frontend | Render Static Site | `https://cocoguard-web.onrender.com` |

---

## Prerequisites

1. A [Render](https://render.com) account (free tier available)
2. A [GitHub](https://github.com) account
3. Two separate GitHub repositories:
   - One for `cocoguard-backend`
   - One for `cocoguard_web`

---

## Step 1: Push Code to GitHub

### Backend Repository

```bash
cd cocoguard-backend

# Initialize git (if not already)
git init
git add .
git commit -m "Initial commit - CocoGuard Backend"

# Create repo on GitHub and push
git remote add origin https://github.com/YOUR_USERNAME/cocoguard-backend.git
git push -u origin main
```

### Web Frontend Repository

```bash
cd cocoguard_web

# Initialize git (if not already)
git init
git add .
git commit -m "Initial commit - CocoGuard Web"

# Create repo on GitHub and push
git remote add origin https://github.com/YOUR_USERNAME/cocoguard-web.git
git push -u origin main
```

---

## Step 2: Deploy Backend on Render

### Option A: Using render.yaml (Recommended)

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Blueprint"**
3. Connect your `cocoguard-backend` GitHub repository
4. Render will detect `render.yaml` and auto-configure
5. Click **"Apply"**

### Option B: Manual Setup

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"**
3. Connect your `cocoguard-backend` GitHub repo
4. Configure:
   - **Name:** `cocoguard-api`
   - **Region:** `Singapore` (or nearest to you)
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** `Starter` (512MB RAM for TensorFlow)

5. Add Environment Variables:
   | Key | Value |
   |-----|-------|
   | `SECRET_KEY` | (click "Generate") |
   | `DATABASE_URL` | `sqlite:///./cocoguard.db` |
   | `ALGORITHM` | `HS256` |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` |
   | `UPLOAD_DIR` | `./uploads` |

6. Click **"Create Web Service"**

### After Backend Deployment

1. Copy your backend URL (e.g., `https://cocoguard-api.onrender.com`)
2. Test the health endpoint: `https://cocoguard-api.onrender.com/health`
3. **Important:** Note this URL for frontend configuration

---

## Step 3: Deploy Web Frontend on Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Static Site"**
3. Connect your `cocoguard-web` GitHub repo
4. Configure:
   - **Name:** `cocoguard-web`
   - **Branch:** `main`
   - **Build Command:** (leave empty)
   - **Publish Directory:** `.`

5. Click **"Create Static Site"**

---

## Step 4: Configure Frontend API URL

After both services are deployed, update the frontend to point to your backend:

### Option A: Update config.js (Recommended)

Edit `cocoguard_web/config.js`:

```javascript
const COCOGUARD_CONFIG = {
    // Update this to your actual Render backend URL
    API_URL: 'https://cocoguard-api.onrender.com',
    VERSION: '1.0.0',
    DEBUG: false
};
```

Then commit and push:

```bash
git add config.js
git commit -m "Update API URL for production"
git push
```

### Option B: Manual Configuration (Per Browser)

1. Open your deployed web frontend
2. Open browser DevTools (F12)
3. In Console, run:
   ```javascript
   localStorage.setItem('api_base_url', 'https://cocoguard-api.onrender.com');
   location.reload();
   ```

---

## Step 5: Create Admin User

After backend deployment, create an admin user:

1. Open your Render dashboard
2. Go to your `cocoguard-api` service
3. Click **"Shell"** tab
4. Run:
   ```bash
   python create_admin_user.py
   ```

Or use the API directly:

```bash
curl -X POST https://cocoguard-api.onrender.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cocoguard.com", "password": "your-secure-password", "full_name": "Admin", "role": "admin"}'
```

---

## Troubleshooting

### TensorFlow Memory Issues

If you see memory errors, upgrade to **Starter Plus** or **Standard** plan on Render (provides more RAM).

### CORS Errors

The backend is pre-configured to allow:
- `*.onrender.com`
- `*.pages.dev` (Cloudflare)
- `*.vercel.app`
- `localhost`

If using a custom domain, update `app/main.py` CORS regex.

### Model Not Loading

Ensure the `model/` directory is pushed to GitHub:
```bash
git add model/
git commit -m "Add TFLite model files"
git push
```

### Database Persistence

⚠️ **Important:** Render's free tier doesn't persist SQLite data between restarts. For production:

1. Use Render PostgreSQL add-on, OR
2. Use an external database service

Update `.env`:
```
DATABASE_URL=postgresql://user:password@host:5432/cocoguard
```

---

## Alternative: Cloudflare Pages (Web Frontend Only)

If you prefer Cloudflare Pages for the frontend:

1. Go to [Cloudflare Pages](https://pages.cloudflare.com)
2. Connect your `cocoguard-web` GitHub repo
3. Configure:
   - **Build command:** (leave empty)
   - **Build output directory:** `.`
4. Deploy

Then update `config.js` with your Render backend URL.

---

## URLs After Deployment

| Service | URL |
|---------|-----|
| Backend API | `https://cocoguard-api.onrender.com` |
| API Docs (Swagger) | `https://cocoguard-api.onrender.com/docs` |
| Health Check | `https://cocoguard-api.onrender.com/health` |
| Web Frontend | `https://cocoguard-web.onrender.com` |

---

## Cost Estimates (Render)

| Plan | Backend | Frontend | Total/Month |
|------|---------|----------|-------------|
| Free | $0 | $0 | $0 |
| Starter | $7 | $0 | $7 |
| Starter Plus | $15 | $0 | $15 |

**Note:** Free tier has cold starts (first request may take 30-60 seconds after inactivity).
