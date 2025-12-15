from fastapi import FastAPI
import app.models as models
from fastapi.middleware.cors import CORSMiddleware
from app.routers import profiles, ai, settings, reports, knowledge, system, terminal, plugins, thresholds, alerts, push, auth, users
from app.database import engine, Base, get_db
from app.services import report_generation
from app.services.snapshot_service import SnapshotService
from app.services.ssh import SSHService # Added for SSH debugging
from app.services.threshold_monitor import ThresholdMonitor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
import logging
from datetime import datetime
import sys

# Configure logging for APScheduler
logging.basicConfig(level=logging.INFO)
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

print("Python sys.path:", sys.path, flush=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Homelab Intelligence")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize APScheduler
scheduler = AsyncIOScheduler()

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
            
            # Temporarily verify SSH connection here for debugging
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
app.include_router(plugins.router)
app.include_router(thresholds.router)
app.include_router(alerts.router)
app.include_router(push.router)

@app.on_event("startup")
async def startup_event():
    print("Starting scheduler...", flush=True)
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        settings = db.query(models.Settings).first()
        if not settings:
            # Initialize default settings if none exist
            settings = models.Settings()
            db.add(settings)
            db.commit()
            db.refresh(settings)

        # Clear all existing jobs before adding new ones to prevent duplicates on restart
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
        
        # Schedule 7-day report
        scheduler.add_job(
            generate_all_server_reports_for_type, 
            'cron', 
            minute=settings.cron_7day_report.split(' ')[0], 
            hour=settings.cron_7day_report.split(' ')[1], 
            day_of_week=settings.cron_7day_report.split(' ')[4], # day of week (0=Mon, 6=Sun)
            id='weekly_7day_reports', 
            args=["7-day"]
        )

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

        # Schedule server snapshots (e.g., every 30 minutes)
        scheduler.add_job(
            take_all_server_snapshots,
            'cron',
            minute='*/30', # Every 30 minutes
            id='server_snapshots'
        )

        # Schedule threshold monitoring (every 1 minute)
        scheduler.add_job(
            check_thresholds,
            'cron',
            minute='*', # Every minute
            id='threshold_monitoring'
        )

        scheduler.start()
        print("Scheduler started with dynamic cron settings.", flush=True)

        # FOR DEBUGGING: Force immediate snapshot on startup
        print("Attempting to take immediate snapshots...", flush=True)
        await take_all_server_snapshots()
        print("Immediate snapshots attempt completed.", flush=True)

    except Exception as e:
        print(f"Error initializing scheduler: {e}", flush=True)
    finally:
        db.close()

@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down scheduler...")
    scheduler.shutdown()
    print("Scheduler shut down.")

@app.get("/")
def read_root():
    return {"message": "Welcome to Homelab Intelligence Hub API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
