"""
Unity - Homelab Monitoring Platform

FastAPI application with integrated plugin scheduler and WebSocket streaming.
"""
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text, select, func, Integer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Plugin
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware

from app.api import plugins, websocket
from app.services.plugin_scheduler import PluginScheduler
from app.services.cache import cache
from app.middleware.cache_middleware import CacheMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: PluginScheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown logic:
    - Start plugin scheduler
    - Connect to Redis cache
    - Register cleanup handlers
    """
    global scheduler
    
    logger.info("🚀 Starting Unity application...")
    
    # Connect to Redis cache (graceful fallback if unavailable)
    try:
        await cache.connect()
    except Exception as e:
        logger.warning(f"Cache connection failed (will operate without cache): {e}")
    
    # Initialize and start scheduler
    try:
        scheduler = PluginScheduler()
        await scheduler.start()
        logger.info("✅ Plugin scheduler started")
    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {e}")
        scheduler = None
    
    logger.info("🎉 Unity application ready!")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("🛑 Shutting down Unity application...")
    
    if scheduler:
        await scheduler.stop()
        logger.info("✅ Plugin scheduler stopped")
    
    await cache.disconnect()
    logger.info("✅ Cache disconnected")
    
    logger.info("👋 Unity application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Unity API",
    description="Homelab Monitoring Platform - Plugin Management and Metrics API",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
from app.core.config import settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add response caching middleware
app.add_middleware(
    CacheMiddleware,
    cache_ttl=60,  # Default 60 seconds
    excluded_paths=["/docs", "/openapi.json", "/health", "/ws/"]
)

# Include routers
app.include_router(plugins.router)
# Authentication routers
from app.routers import auth, api_keys, users, audit_logs, notifications, oauth
from app.routers.plugins import marketplace
from app.routers import dashboard_builder
from app.routers import ai_insights
from app.routers import orchestration
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(api_keys.router, prefix="/api/v1", tags=["API Keys"])
app.include_router(users.router, prefix="/api/v1", tags=["Users"])
app.include_router(audit_logs.router, prefix="/api/v1", tags=["Audit Logs"])
app.include_router(notifications.router)
app.include_router(oauth.router)
app.include_router(websocket.router)
# app.include_router(deployments.router)
app.include_router(marketplace.router)
app.include_router(dashboard_builder.router)
app.include_router(ai_insights.router)

app.include_router(orchestration.router)

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Unity API",
        "version": "1.0.0",
        "description": "Homelab Monitoring Platform",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "openapi": "/openapi.json",
            "plugins": "/api/plugins",
            "websocket": "/ws/metrics"
        }
    }


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }
    
    # Check scheduler
    scheduler_running = scheduler and scheduler._running
    health_status["components"]["scheduler"] = {
        "status": "running" if scheduler_running else "stopped"
    }
    
    # Check cache
    cache_available = cache.is_available
    health_status["components"]["cache"] = {
        "status": "connected" if cache_available else "disconnected"
    }
    if not cache_available:
        health_status["status"] = "degraded"
    
    # Check database
    try:
        db.execute(text("SELECT 1"))
        health_status["components"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Get plugin stats
    try:
        result = db.execute(
            select(
                func.count().label("total"),
                func.sum(func.cast(Plugin.enabled, Integer)).label("enabled")
            ).select_from(Plugin)
        )
        row = result.one()
        health_status["components"]["plugins"] = {
            "total": row.total or 0,
            "enabled": row.enabled or 0
        }
    except Exception:
        pass
    
    return health_status
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

# Enable core monitoring routers (after fixing imports)
# from app.routers import infrastructure, system
# 
# # Register monitoring routers
# app.include_router(infrastructure.router, prefix="/api/v1", tags=["Infrastructure"])
# app.include_router(system.router, prefix="/api/v1", tags=["System"])
