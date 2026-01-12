from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.dependencies import get_tenant_id
from app import models, schemas_settings

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=schemas_settings.Settings)
def get_settings(db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)):
    settings = db.query(models.Settings).filter(models.Settings.tenant_id == tenant_id).first()
    if not settings:
        # Initialize default settings if none exist
        settings = models.Settings(tenant_id=tenant_id, )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

@router.put("/", response_model=schemas_settings.Settings)
def update_settings(settings_in: schemas_settings.SettingsUpdate, db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)):
    settings = db.query(models.Settings).filter(models.Settings.tenant_id == tenant_id).first()
    if not settings:
        settings = models.Settings(tenant_id=tenant_id, )
        db.add(settings)
    
    # Update fields
    settings.providers = settings_in.providers
    settings.active_model = settings_in.active_model
    settings.primary_provider = settings_in.primary_provider
    settings.fallback_provider = settings_in.fallback_provider
    settings.system_prompt = settings_in.system_prompt
    settings.cron_24hr_report = settings_in.cron_24hr_report
    settings.cron_7day_report = settings_in.cron_7day_report
    settings.cron_monthly_report = settings_in.cron_monthly_report
    settings.polling_interval = settings_in.polling_interval
    settings.alert_sound_enabled = settings_in.alert_sound_enabled
    settings.maintenance_mode_until = settings_in.maintenance_mode_until
    
    db.commit()
    db.refresh(settings)
    return settings
