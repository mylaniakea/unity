from fastapi import FastAPI
import app.models as models
from fastapi.middleware.cors import CORSMiddleware
from app.routers import (
    profiles, ai, settings, reports, knowledge, system, 
    terminal, plugins, thresholds, alerts, push, auth, users, credentials
)
# Import new plugin routers
from app.routers import plugins_v2_secure, plugin_keys

from app.database import engine, Base, get_db
from app.services import report_generation
from app.services.snapshot_service import SnapshotService
from app.services.ssh import SSHService
from app.services.threshold_monitor import ThresholdMonitor
from app.services.plugin_manager import PluginManager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
import logging
from datetime import datetime
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.getLogger('apscheduler').setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

print("Python sys.path:", sys.path, flush=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Unity - Homelab Intelligence Hub")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize APScheduler
scheduler = AsyncIOScheduler()

# Global plugin manager (initialized on startup)
plugin_manager: PluginManager = None


async def generate_all_server_reports_for_type(report_type: str):
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        print(f"Running {report_type} report generation job...", flush=True)
        profiles = db.query(models.ServerProfile).all()
        for profile in profiles:
            print(f"Generating {report_type} report for server: {profile.name} (ID: {profile.id})", flush=True)
            if report_type == "24-hour":
                await report_generation.generate_24_hour_report(db, profile.id)
            elif report_type == "7-day":
                await report_generation.generate_7_day_report(db, profile.id)
            elif report_type == "monthly":
                await report_generation.generate_monthly_report(db, profile.id)
        print(f"{report_type} report generation job completed.", flush=True)
    except Exception as e:
        print(f"Error during {report_type} report generation: {e}", flush=True)
    finally:
        db.close()


async def take_all_server_snapshots():
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        print("Running server snapshot job...", flush=True)
        profiles = db.query(models.ServerProfile).all()
        for profile in profiles:
            print(f"Taking snapshot for server: {profile.name} (ID: {profile.id})", flush=True)
            
            ssh_test_service = SSHService(profile)
            ssh_test_result = await ssh_test_service.verify_connection()
            print(f"SSH Connection Test for {profile.name} (ID: {profile.id}): {ssh_test_result}", flush=True)
            
            if ssh_test_result["success"]:
                await SnapshotService.take_remote_snapshot(db, profile)
            else:
                print(f"Skipping snapshot for {profile.name} due to SSH connection failure: {ssh_test_result['message']}", flush=True)
        print("Server snapshot job completed.", flush=True)
    except Exception as e:
        print(f"Error during server snapshot generation: {e}", flush=True)
    finally:
        db.close()


async def check_thresholds():
    """Check all threshold rules and trigger alerts if needed"""
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        print("Running threshold monitoring job...", flush=True)
        monitor = ThresholdMonitor(db)
        await monitor.check_all_thresholds()
        print("Threshold monitoring job completed.", flush=True)
    except Exception as e:
        print(f"Error during threshold monitoring: {e}", flush=True)
    finally:
        db.close()


async def execute_enabled_plugins():
    """Execute all enabled plugins and store metrics"""
    global plugin_manager
    
    if not plugin_manager:
        logger.warning("Plugin manager not initialized, skipping plugin execution")
        return
    
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        # Recreate plugin manager with current db session
        pm = PluginManager(db)
        
        logger.info("Running plugin execution job...")
        
        # Get all enabled plugins
        plugins = db.query(models.Plugin).filter(models.Plugin.enabled == True).all()
        
        for plugin in plugins:
            try:
                logger.info(f"Executing plugin: {plugin.id}")
                result = await pm.execute_plugin(plugin.id)
                
                if result.get("success"):
                    logger.info(f"Plugin {plugin.id} executed successfully")
                else:
                    logger.warning(f"Plugin {plugin.id} execution failed: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Error executing plugin {plugin.id}: {e}")
        
        logger.info("Plugin execution job completed")
        
    except Exception as e:
        logger.error(f"Error during plugin execution: {e}")
    finally:
        db.close()


# Include Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(profiles.router)
app.include_router(system.router)
app.include_router(ai.router)
app.include_router(settings.router)
app.include_router(reports.router)
app.include_router(knowledge.router)
app.include_router(terminal.router)
app.include_router(plugins.router)  # Old plugin system (legacy)
app.include_router(plugins_v2_secure.router)  # New secure plugin system
app.include_router(plugin_keys.router)  # API key management
app.include_router(credentials.router)  # Credential management
app.include_router(thresholds.router)
app.include_router(alerts.router)
app.include_router(push.router)


@app.on_event("startup")
async def startup_event():
    global plugin_manager
    
    print("=" * 60, flush=True)
    print("Unity - Homelab Intelligence Hub Starting...", flush=True)
    print("=" * 60, flush=True)
    
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        # Initialize settings
        settings = db.query(models.Settings).first()
        if not settings:
            settings = models.Settings()
            db.add(settings)
            db.commit()
            db.refresh(settings)
        
        # ============================================
        # Initialize Plugin System
        # ============================================
        print("\n🔌 Initializing Plugin System...", flush=True)
        try:
            plugin_manager = PluginManager(db)
            await plugin_manager.initialize()
            print("✅ Plugin system initialized successfully", flush=True)
            
            # List discovered plugins
            plugins = plugin_manager.list_plugins()
            print(f"📦 Discovered {len(plugins)} plugin(s):", flush=True)
            for p in plugins:
                status = "✓ enabled" if p.get("enabled") else "○ disabled"
                print(f"   - {p.get('name')} ({p.get('id')}) [{status}]", flush=True)
                
        except Exception as e:
            print(f"❌ Error initializing plugin system: {e}", flush=True)
            logger.exception("Plugin system initialization failed")

        # ============================================
        # Schedule Jobs
        # ============================================
        print("\n⏰ Configuring scheduled jobs...", flush=True)
        
        # Clear existing jobs
        scheduler.remove_all_jobs()
        
        # Schedule 24-hour report
        scheduler.add_job(
            generate_all_server_reports_for_type, 
            'cron', 
            minute=settings.cron_24hr_report.split(' ')[0], 
            hour=settings.cron_24hr_report.split(' ')[1], 
            id='daily_24hr_reports', 
            args=["24-hour"]
        )
        print(f"   - 24-hour reports: {settings.cron_24hr_report}", flush=True)
        
        # Schedule 7-day report
        scheduler.add_job(
            generate_all_server_reports_for_type, 
            'cron', 
            minute=settings.cron_7day_report.split(' ')[0], 
            hour=settings.cron_7day_report.split(' ')[1], 
            day_of_week=settings.cron_7day_report.split(' ')[4],
            id='weekly_7day_reports', 
            args=["7-day"]
        )
        print(f"   - 7-day reports: {settings.cron_7day_report}", flush=True)

        # Schedule Monthly report
        scheduler.add_job(
            generate_all_server_reports_for_type, 
            'cron', 
            minute=settings.cron_monthly_report.split(' ')[0],
            hour=settings.cron_monthly_report.split(' ')[1],
            day=settings.cron_monthly_report.split(' ')[2],
            id='monthly_reports',
            args=["monthly"]
        )
        print(f"   - Monthly reports: {settings.cron_monthly_report}", flush=True)

        # Schedule server snapshots (every 30 minutes)
        scheduler.add_job(
            take_all_server_snapshots,
            'cron',
            minute='*/30',
            id='server_snapshots'
        )
        print(f"   - Server snapshots: every 30 minutes", flush=True)

        # Schedule threshold monitoring (every 1 minute)
        scheduler.add_job(
            check_thresholds,
            'cron',
            minute='*',
            id='threshold_monitoring'
        )
        print(f"   - Threshold monitoring: every minute", flush=True)
        
        # Schedule plugin execution (every 5 minutes)
        scheduler.add_job(
            execute_enabled_plugins,
            'cron',
            minute='*/5',
            id='plugin_execution'
        )
        print(f"   - Plugin execution: every 5 minutes", flush=True)

        scheduler.start()
        print("\n✅ Scheduler started successfully", flush=True)

        # Take immediate snapshot on startup (for debugging)
        print("\n📸 Taking immediate snapshots...", flush=True)
        await take_all_server_snapshots()
        print("✅ Immediate snapshots completed", flush=True)
        
        print("\n" + "=" * 60, flush=True)
        print("🚀 Unity is ready!", flush=True)
        print("=" * 60, flush=True)

    except Exception as e:
        print(f"\n❌ Error during startup: {e}", flush=True)
        logger.exception("Startup failed")
    finally:
        db.close()


@app.on_event("shutdown")
async def shutdown_event():
    global plugin_manager
    
    print("\n" + "=" * 60, flush=True)
    print("Shutting down Unity...", flush=True)
    print("=" * 60, flush=True)
    
    # Shutdown plugin manager
    if plugin_manager:
        print("🔌 Shutting down plugin system...", flush=True)
        try:
            await plugin_manager.shutdown()
            print("✅ Plugin system shut down", flush=True)
        except Exception as e:
            print(f"❌ Error shutting down plugin system: {e}", flush=True)
    
    # Shutdown scheduler
    print("⏰ Shutting down scheduler...", flush=True)
    scheduler.shutdown()
    print("✅ Scheduler shut down", flush=True)
    
    print("=" * 60, flush=True)
    print("👋 Unity shut down complete", flush=True)
    print("=" * 60, flush=True)


@app.get("/")
def read_root():
    return {"message": "Welcome to Unity - Homelab Intelligence Hub API"}


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": "Unity",
        "version": "1.0.0"
    }
