from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.services.system_info import SystemInfoService
from app.database import get_db
from app.core.dependencies import get_tenant_id
from app import models

from app.core.k8s_autodiscovery import autodiscover_k8s_cluster
from app.core.docker_autodiscovery import autodiscover_docker_host

router = APIRouter(
    prefix="/system",
    tags=["system"],
    responses={404: {"description": "Not found"}},
)

@router.post("/scan")
async def scan_infrastructure(db: Session = Depends(get_db), tenant_id: str = Depends(get_tenant_id)):
    """
    Manually trigger auto-discovery for Docker hosts and K8s clusters.
    """
    results = {
        "docker": None,
        "kubernetes": None
    }
    
    # Docker
    docker_host = await autodiscover_docker_host(db, tenant_id)
    if docker_host:
        results["docker"] = f"Registered: {docker_host.name}"
    else:
        results["docker"] = "Not found or already registered"
        
    # Kubernetes
    k8s_cluster = await autodiscover_k8s_cluster(db, tenant_id)
    if k8s_cluster:
        results["kubernetes"] = f"Registered: {k8s_cluster.name}"
    else:
        results["kubernetes"] = "Not found or already registered"
        
    return results

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
    hardware = SystemInfoService.get_hardware_info()
    return {
        "hardware": hardware,
        "os": SystemInfoService.get_os_info(),
        "network": SystemInfoService.get_network_info(),
        "memory": hardware.get("memory", {}),  # Also expose at top level for compatibility
        "load_average": SystemInfoService.get_load_average(),
        "processes": SystemInfoService.get_process_info(),
        "file_descriptors": SystemInfoService.get_file_descriptors(),
        "uptime_seconds": SystemInfoService.get_uptime_seconds()
    }
