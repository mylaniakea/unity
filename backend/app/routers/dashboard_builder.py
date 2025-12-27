"""
Dashboard Builder API

Endpoints for creating and managing custom dashboards.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.services.dashboard_builder import DashboardBuilderService
from app.models.dashboard import Dashboard, DashboardWidget

router = APIRouter(prefix="/api/v1/dashboards", tags=["Dashboard Builder"])


# Request/Response Models
class DashboardCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_shared: bool = False
    refresh_interval: int = Field(30, ge=5, le=3600)


class DashboardUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    layout: Optional[dict] = None
    widgets: Optional[List[dict]] = None
    refresh_interval: Optional[int] = Field(None, ge=5, le=3600)


class DashboardResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    user_id: Optional[str]
    layout: dict
    widgets: List[dict]
    is_default: bool
    is_shared: bool
    refresh_interval: int
    created_at: str
    updated_at: Optional[str]
    
    class Config:
        from_attributes = True


class WidgetAdd(BaseModel):
    widget_type: str
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    w: int = Field(..., ge=1, le=12)
    h: int = Field(..., ge=1, le=20)
    config: Optional[dict] = None
    title: Optional[str] = None


class WidgetUpdate(BaseModel):
    x: Optional[int] = Field(None, ge=0)
    y: Optional[int] = Field(None, ge=0)
    w: Optional[int] = Field(None, ge=1, le=12)
    h: Optional[int] = Field(None, ge=1, le=20)
    config: Optional[dict] = None
    title: Optional[str] = None


@router.post("", response_model=DashboardResponse)
async def create_dashboard(
    dashboard: DashboardCreate,
    user_id: str = "system",  # TODO: Get from auth
    db: Session = Depends(get_db)
):
    """Create a new custom dashboard."""
    service = DashboardBuilderService(db)
    
    created = service.create_dashboard(
        name=dashboard.name,
        user_id=user_id,
        description=dashboard.description,
        is_shared=dashboard.is_shared,
        refresh_interval=dashboard.refresh_interval
    )
    
    return DashboardResponse.from_orm(created)


@router.get("", response_model=List[DashboardResponse])
async def list_dashboards(
    user_id: Optional[str] = None,
    include_shared: bool = True,
    db: Session = Depends(get_db)
):
    """List dashboards accessible to user."""
    service = DashboardBuilderService(db)
    dashboards = service.list_dashboards(user_id=user_id, include_shared=include_shared)
    
    return [DashboardResponse.from_orm(d) for d in dashboards]


@router.get("/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: int,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get a specific dashboard."""
    service = DashboardBuilderService(db)
    dashboard = service.get_dashboard(dashboard_id, user_id=user_id)
    
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    return DashboardResponse.from_orm(dashboard)


@router.put("/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(
    dashboard_id: int,
    dashboard: DashboardUpdate,
    db: Session = Depends(get_db)
):
    """Update dashboard configuration."""
    service = DashboardBuilderService(db)
    
    updated = service.update_dashboard(
        dashboard_id=dashboard_id,
        name=dashboard.name,
        description=dashboard.description,
        layout=dashboard.layout,
        widgets=dashboard.widgets,
        refresh_interval=dashboard.refresh_interval
    )
    
    if not updated:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    return DashboardResponse.from_orm(updated)


@router.delete("/{dashboard_id}")
async def delete_dashboard(
    dashboard_id: int,
    db: Session = Depends(get_db)
):
    """Delete a dashboard."""
    service = DashboardBuilderService(db)
    
    success = service.delete_dashboard(dashboard_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    return {"success": True, "message": "Dashboard deleted"}


@router.post("/{dashboard_id}/widgets")
async def add_widget(
    dashboard_id: int,
    widget: WidgetAdd,
    db: Session = Depends(get_db)
):
    """Add a widget to a dashboard."""
    service = DashboardBuilderService(db)
    
    created = service.add_widget(
        dashboard_id=dashboard_id,
        widget_type=widget.widget_type,
        x=widget.x,
        y=widget.y,
        w=widget.w,
        h=widget.h,
        config=widget.config,
        title=widget.title
    )
    
    return {
        "id": created.id,
        "widget_id": created.widget_id,
        "widget_type": created.widget_type,
        "x": created.x,
        "y": created.y,
        "w": created.w,
        "h": created.h,
        "config": created.config,
        "title": created.title
    }


@router.put("/widgets/{widget_id}")
async def update_widget(
    widget_id: int,
    widget: WidgetUpdate,
    db: Session = Depends(get_db)
):
    """Update widget position or configuration."""
    service = DashboardBuilderService(db)
    
    updated = service.update_widget(
        widget_id=widget_id,
        x=widget.x,
        y=widget.y,
        w=widget.w,
        h=widget.h,
        config=widget.config,
        title=widget.title
    )
    
    if not updated:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    return {
        "id": updated.id,
        "widget_id": updated.widget_id,
        "widget_type": updated.widget_type,
        "x": updated.x,
        "y": updated.y,
        "w": updated.w,
        "h": updated.h,
        "config": updated.config,
        "title": updated.title
    }


@router.delete("/widgets/{widget_id}")
async def delete_widget(
    widget_id: int,
    db: Session = Depends(get_db)
):
    """Delete a widget from dashboard."""
    service = DashboardBuilderService(db)
    
    success = service.delete_widget(widget_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    return {"success": True, "message": "Widget deleted"}


@router.get("/templates/widgets")
async def get_widget_templates(db: Session = Depends(get_db)):
    """Get available widget templates."""
    service = DashboardBuilderService(db)
    templates = service.get_widget_templates()
    
    return {"templates": templates}

