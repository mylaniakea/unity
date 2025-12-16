from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app import models
from app.schemas.reports import Report as ReportSchema, ReportCreate
from app.services import report_generation
from fastapi.responses import Response, StreamingResponse # Import for file responses
import io # Import io for file-like objects
from datetime import datetime

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    responses={404: {"description": "Not found"}},
)

# Pydantic models for manual report creation/updates (used by Intelligence page)
class ManualReportCreate(BaseModel):
    title: str
    content: str
    type: str  # e.g., "system_summary"
    server_id: Optional[int] = None

class ManualReportUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    type: Optional[str] = None


# --- GET ALL REPORTS ---
@router.get("/", response_model=List[ReportSchema])
def get_all_reports(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all reports across all servers."""
    reports = db.query(models.Report)\
        .order_by(models.Report.generated_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    return reports


# --- GENERATE REPORT (automated) ---
@router.post("/generate/{server_id}/{report_type}", response_model=ReportSchema)
async def generate_report(
    server_id: int,
    report_type: str, # "24-hour", "7-day", "monthly"
    db: Session = Depends(get_db)
):
    server_profile = db.query(models.ServerProfile).filter(models.ServerProfile.id == server_id).first()
    if not server_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server profile not found")

    if report_type == "24-hour":
        report = await report_generation.generate_24_hour_report(db, server_id)
    elif report_type == "7-day":
        report = await report_generation.generate_7_day_report(db, server_id)
    elif report_type == "monthly":
        report = await report_generation.generate_monthly_report(db, server_id)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid report type")

    if not report:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate report")

    return report


# --- CREATE MANUAL REPORT (for saving summaries from Intelligence page) ---
@router.post("/")
def create_manual_report(
    report_data: ManualReportCreate,
    db: Session = Depends(get_db)
):
    """Create a manual report (e.g., AI-generated summary from Intelligence page)."""
    now = datetime.now()
    
    new_report = models.Report(
        server_id=report_data.server_id,  # Can be None for local system reports
        report_type=report_data.type,
        start_time=now,
        end_time=now,
        aggregated_data={
            "title": report_data.title,
            "content": report_data.content,
            "is_manual": True
        }
    )
    
    db.add(new_report)
    db.commit()
    db.refresh(new_report)
    
    return {"id": new_report.id, "title": report_data.title, "status": "created"}


# --- UPDATE REPORT ---
@router.put("/{report_id}")
def update_report(
    report_id: int,
    report_data: ManualReportUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing report."""
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    
    # Update aggregated_data with new content
    current_data = dict(report.aggregated_data) if report.aggregated_data else {}
    
    if report_data.title is not None:
        current_data["title"] = report_data.title
    if report_data.content is not None:
        current_data["content"] = report_data.content
    if report_data.type is not None:
        report.report_type = report_data.type
    
    current_data["updated_at"] = datetime.now().isoformat()
    report.aggregated_data = current_data
    
    db.add(report)
    db.commit()
    db.refresh(report)
    
    return {"id": report.id, "status": "updated"}


# --- GET REPORTS BY SERVER (renamed route to avoid conflict) ---
@router.get("/server/{server_id}", response_model=List[ReportSchema])
def get_reports_for_server(
    server_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all reports for a specific server."""
    server_profile = db.query(models.ServerProfile).filter(models.ServerProfile.id == server_id).first()
    if not server_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server profile not found")

    reports = db.query(models.Report)\
        .filter(models.Report.server_id == server_id)\
        .order_by(models.Report.generated_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    return reports


# --- GET SINGLE REPORT BY ID ---
@router.get("/{report_id}", response_model=ReportSchema)
def get_report_by_id(
    report_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific report by its ID."""
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


# --- EXPORT REPORT ---
@router.get("/export/{report_id}")
async def export_report(
    report_id: int,
    format: str, # "csv" or "pdf"
    db: Session = Depends(get_db)
):
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if format == "csv":
        csv_data = report_generation.export_report_to_csv(report.aggregated_data)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=report_{report.id}.csv"
            }
        )
    elif format == "pdf":
        pdf_data = report_generation.export_report_to_pdf(report.aggregated_data)
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=report_{report.id}.pdf"
            }
        )
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid export format. Choose 'csv' or 'pdf'.")


# --- DELETE REPORT ---
@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    db.delete(report)
    db.commit()
    return {"ok": True}