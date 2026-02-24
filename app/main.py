from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import logging
import traceback

logger = logging.getLogger(__name__)


from .database import engine, Base
from .config import settings
from .routers import auth, users, pest_types, scans, farms, uploads, feedback, knowledge, analytics, verification, settings as settings_router, prediction, password_reset, notifications, two_factor, management_strategies, survey, admin_register, backup

# Create tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    Base.metadata.create_all(bind=engine)
    # Create uploads directory
    os.makedirs(settings.upload_dir, exist_ok=True)
    
    # Pre-load prediction model
    try:
        from .services.prediction_service import get_prediction_service
        service = get_prediction_service()
        logger.info(f"Prediction model loaded: {service.model_loaded}")
        logger.info(f"Available pest classes: {service.labels}")
    except Exception as e:
        logger.warning(f"Failed to pre-load prediction model: {e}")
    
    yield
    # Shutdown: cleanup if needed

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=lifespan
)

# Rate limiting: 60 requests/minute per IP for general endpoints
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Allow frontends to call this API - dynamic CORS using regex
# Matches: localhost, 127.0.0.1, private IPs, Render, Cloudflare Pages, and Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|[\w-]+\.onrender\.com|[\w-]+\.pages\.dev|[\w-]+\.vercel\.app)(:\d+)?(/.*)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Global exception handler — CORS is handled by middleware, not here
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all exceptions and return proper JSON. CORS headers are added by CORSMiddleware."""
    logger.error(f"Unhandled exception: {exc}")
    logger.debug(f"Traceback: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": "Internal Server Error"
        }
    )

# Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(farms.router)
app.include_router(pest_types.router)
app.include_router(scans.router)
app.include_router(uploads.router)
app.include_router(feedback.router)
app.include_router(knowledge.router)
app.include_router(analytics.router)
app.include_router(verification.router)
app.include_router(settings_router.router)
app.include_router(prediction.router)
app.include_router(password_reset.router)
app.include_router(notifications.router)
app.include_router(two_factor.router)
app.include_router(management_strategies.router)
app.include_router(survey.router)
app.include_router(admin_register.router)
app.include_router(backup.router)


# Mount /test_static after imports so os is defined
test_static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../test_static'))
if os.path.isdir(test_static_dir):
    logger.debug(f"Mounting /test_static from: {test_static_dir}")
    app.mount(
        "/test_static",
        StaticFiles(directory=test_static_dir),
        name="test_static"
    )



# Always use the correct absolute path for static serving

# Serve static files from the backend's own uploads directory
uploads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../uploads/files'))
logger.debug(f"Uploads dir path: {uploads_dir}")
os.makedirs(uploads_dir, exist_ok=True)  # Create if not exists
if os.path.isdir(uploads_dir):
    logger.info(f"Serving /uploads/files from: {uploads_dir}")
    from fastapi.staticfiles import StaticFiles as _StaticFiles
    
    class CORSStaticFiles(_StaticFiles):
        """Static files handler with CORS headers for cross-origin image loading"""
        async def get_response(self, path: str, scope):
            response = await super().get_response(path, scope)
            # Add CORS headers to all static file responses
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Cache-Control"] = "public, max-age=3600"
            return response
    
    app.mount(
        "/uploads/files",
        CORSStaticFiles(directory=uploads_dir),
        name="uploads"
    )
else:
    logger.warning(f"uploads/files directory not found at {uploads_dir}")

# Serve scan images from uploads/scans directory
scans_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../uploads/scans'))
logger.debug(f"Scans dir path: {scans_dir}")
os.makedirs(scans_dir, exist_ok=True)  # Create if not exists
if os.path.isdir(scans_dir):
    logger.info(f"Serving /uploads/scans from: {scans_dir}")
    app.mount(
        "/uploads/scans",
        CORSStaticFiles(directory=scans_dir),
        name="scans"
    )
else:
    logger.warning(f"uploads/scans directory not found at {scans_dir}")


@app.get("/")
def read_root():
    return {"message": "CocoGuard API is running"}


@app.get("/health")
def health_check():
    """Health check endpoint for connectivity testing"""
    return {"status": "healthy", "service": "CocoGuard API"}
