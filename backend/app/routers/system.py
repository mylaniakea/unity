from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.services.system_info import SystemInfoService
from app.database import get_db
from app.core.dependencies import get_tenant_id
from app import models

router = APIRouter(
    prefix="/system",
    tags=["system"],
    responses={404: {"description": "Not found"}},
)

@router.get("/dashboard-stats")
def get_dashboard_stats(db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)):
    profile_count = db.query(models.ServerProfile).filter(models.ServerProfile.tenant_id == tenant_id).count()
    report_count = db.query(models.Report).filter(models.Report.tenant_id == tenant_id).count()
    knowledge_count = db.query(models.KnowledgeItem).filter(models.KnowledgeItem.tenant_id == tenant_id).count()
    
    # Get last 5 reports
    recent_reports = db.query(models.Report).filter(models.Report.tenant_id == tenant_id).order_by(models.Report.generated_at.desc()).limit(5).all()
    
    return {
        "counts": {
            "profiles": profile_count,
            "reports": report_count,
            "knowledge": knowledge_count
        },
        "recent_reports": recent_reports
    }

@router.get("/hardware")
async def get_hardware():
    return SystemInfoService.get_hardware_info()

@router.get("/os")
async def get_os():
    return SystemInfoService.get_os_info()

@router.get("/network")
async def get_network():
    return SystemInfoService.get_network_info()

@router.get("/full")
async def get_full_report():
    return {
        "hardware": SystemInfoService.get_hardware_info(),
        "os": SystemInfoService.get_os_info(),
        "network": SystemInfoService.get_network_info()
    }
