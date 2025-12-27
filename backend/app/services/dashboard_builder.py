"""
Dashboard Builder Service

Manages custom dashboard creation, editing, and widget management.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.dashboard import Dashboard, DashboardWidget

logger = logging.getLogger(__name__)


class DashboardBuilderService:
    """Service for managing custom dashboards."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_dashboard(
        self,
        name: str,
        user_id: Optional[str] = None,
        description: Optional[str] = None,
        is_shared: bool = False,
        refresh_interval: int = 30
    ) -> Dashboard:
        """Create a new dashboard."""
        dashboard = Dashboard(
            name=name,
            description=description,
            user_id=user_id,
            is_shared=is_shared,
            refresh_interval=refresh_interval,
            layout={
                "columns": 12,
                "rowHeight": 30,
                "margin": [10, 10]
            },
            widgets=[]
        )
        
        self.db.add(dashboard)
        self.db.commit()
        self.db.refresh(dashboard)
        
        logger.info(f"Created dashboard: {dashboard.id} ({name})")
        return dashboard
    
    def get_dashboard(self, dashboard_id: int, user_id: Optional[str] = None) -> Optional[Dashboard]:
        """Get a dashboard by ID."""
        query = self.db.query(Dashboard).filter(Dashboard.id == dashboard_id)
        
        # If user_id provided, check access
        if user_id:
            query = query.filter(
                (Dashboard.user_id == user_id) | (Dashboard.is_shared == True)
            )
        else:
            query = query.filter(Dashboard.is_shared == True)
        
        return query.first()
    
    def list_dashboards(
        self,
        user_id: Optional[str] = None,
        include_shared: bool = True
    ) -> List[Dashboard]:
        """List dashboards accessible to user."""
        query = self.db.query(Dashboard)
        
        if user_id:
            conditions = [Dashboard.user_id == user_id]
            if include_shared:
                conditions.append(Dashboard.is_shared == True)
            query = query.filter(and_(*conditions))
        else:
            query = query.filter(Dashboard.is_shared == True)
        
        return query.order_by(Dashboard.created_at.desc()).all()
    
    def update_dashboard(
        self,
        dashboard_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        layout: Optional[Dict[str, Any]] = None,
        widgets: Optional[List[Dict[str, Any]]] = None,
        refresh_interval: Optional[int] = None
    ) -> Optional[Dashboard]:
        """Update dashboard configuration."""
        dashboard = self.db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
        
        if not dashboard:
            return None
        
        if name is not None:
            dashboard.name = name
        if description is not None:
            dashboard.description = description
        if layout is not None:
            dashboard.layout = layout
        if widgets is not None:
            dashboard.widgets = widgets
        if refresh_interval is not None:
            dashboard.refresh_interval = refresh_interval
        
        dashboard.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(dashboard)
        
        return dashboard
    
    def add_widget(
        self,
        dashboard_id: int,
        widget_type: str,
        x: int,
        y: int,
        w: int,
        h: int,
        config: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None
    ) -> DashboardWidget:
        """Add a widget to a dashboard."""
        # Generate widget ID
        existing_widgets = self.db.query(DashboardWidget).filter(
            DashboardWidget.dashboard_id == dashboard_id
        ).all()
        
        widget_id = f"{widget_type}_{len(existing_widgets) + 1}"
        
        widget = DashboardWidget(
            dashboard_id=dashboard_id,
            widget_type=widget_type,
            widget_id=widget_id,
            x=x,
            y=y,
            w=w,
            h=h,
            config=config or {},
            title=title or widget_type.replace("_", " ").title()
        )
        
        self.db.add(widget)
        
        # Update dashboard widgets list
        dashboard = self.db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
        if dashboard:
            widgets_list = dashboard.widgets or []
            widgets_list.append({
                "id": widget_id,
                "type": widget_type,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "config": config or {},
                "title": title
            })
            dashboard.widgets = widgets_list
        
        self.db.commit()
        self.db.refresh(widget)
        
        return widget
    
    def update_widget(
        self,
        widget_id: int,
        x: Optional[int] = None,
        y: Optional[int] = None,
        w: Optional[int] = None,
        h: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None
    ) -> Optional[DashboardWidget]:
        """Update widget position or configuration."""
        widget = self.db.query(DashboardWidget).filter(DashboardWidget.id == widget_id).first()
        
        if not widget:
            return None
        
        if x is not None:
            widget.x = x
        if y is not None:
            widget.y = y
        if w is not None:
            widget.w = w
        if h is not None:
            widget.h = h
        if config is not None:
            widget.config = config
        if title is not None:
            widget.title = title
        
        widget.updated_at = datetime.utcnow()
        
        # Update in dashboard widgets list
        dashboard = self.db.query(Dashboard).filter(Dashboard.id == widget.dashboard_id).first()
        if dashboard:
            widgets_list = dashboard.widgets or []
            for w in widgets_list:
                if w.get("id") == widget.widget_id:
                    if x is not None:
                        w["x"] = x
                    if y is not None:
                        w["y"] = y
                    if w is not None:
                        w["w"] = w
                    if h is not None:
                        w["h"] = h
                    if config is not None:
                        w["config"] = config
                    if title is not None:
                        w["title"] = title
                    break
            dashboard.widgets = widgets_list
        
        self.db.commit()
        self.db.refresh(widget)
        
        return widget
    
    def delete_widget(self, widget_id: int) -> bool:
        """Delete a widget from dashboard."""
        widget = self.db.query(DashboardWidget).filter(DashboardWidget.id == widget_id).first()
        
        if not widget:
            return False
        
        dashboard_id = widget.dashboard_id
        widget_widget_id = widget.widget_id
        
        # Remove from dashboard widgets list
        dashboard = self.db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
        if dashboard:
            widgets_list = dashboard.widgets or []
            dashboard.widgets = [w for w in widgets_list if w.get("id") != widget_widget_id]
        
        # Delete widget
        self.db.delete(widget)
        self.db.commit()
        
        return True
    
    def delete_dashboard(self, dashboard_id: int) -> bool:
        """Delete a dashboard."""
        dashboard = self.db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
        
        if not dashboard:
            return False
        
        # Delete all widgets
        self.db.query(DashboardWidget).filter(
            DashboardWidget.dashboard_id == dashboard_id
        ).delete()
        
        # Delete dashboard
        self.db.delete(dashboard)
        self.db.commit()
        
        return True
    
    def get_widget_templates(self) -> List[Dict[str, Any]]:
        """Get available widget templates."""
        return [
            {
                "type": "stat_card",
                "name": "Stat Card",
                "description": "Display a single metric value",
                "default_size": {"w": 3, "h": 2},
                "config_schema": {
                    "metric_name": {"type": "string", "required": True},
                    "title": {"type": "string"},
                    "unit": {"type": "string"},
                    "color": {"type": "string"}
                }
            },
            {
                "type": "metric_chart",
                "name": "Metric Chart",
                "description": "Time-series chart for a metric",
                "default_size": {"w": 6, "h": 4},
                "config_schema": {
                    "plugin_id": {"type": "string", "required": True},
                    "metric_name": {"type": "string", "required": True},
                    "time_range": {"type": "string", "default": "1h"},
                    "chart_type": {"type": "string", "default": "line"}
                }
            },
            {
                "type": "alert_list",
                "name": "Alert List",
                "description": "List of active alerts",
                "default_size": {"w": 6, "h": 5},
                "config_schema": {
                    "severity": {"type": "string"},
                    "limit": {"type": "number", "default": 10}
                }
            },
            {
                "type": "plugin_health",
                "name": "Plugin Health",
                "description": "Plugin status grid",
                "default_size": {"w": 12, "h": 4},
                "config_schema": {
                    "category": {"type": "string"}
                }
            },
            {
                "type": "infrastructure_overview",
                "name": "Infrastructure Overview",
                "description": "Servers, storage, databases summary",
                "default_size": {"w": 12, "h": 3},
                "config_schema": {}
            }
        ]

