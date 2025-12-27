"""
AI-Powered Insights API

Endpoints for anomaly detection, forecasting, and intelligent recommendations.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.ai.insights_service import InsightsService

router = APIRouter(prefix="/api/v1/ai/insights", tags=["AI Insights"])


@router.get("/anomalies")
async def detect_anomalies(
    plugin_id: str = Query(..., description="Plugin ID"),
    metric_name: str = Query(..., description="Metric name"),
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    method: str = Query("zscore", description="Detection method: zscore or iqr"),
    db: Session = Depends(get_db)
):
    """Detect anomalies in a metric."""
    service = InsightsService(db)
    
    try:
        result = service.analyze_metric_anomalies(
            plugin_id=plugin_id,
            metric_name=metric_name,
            hours=hours,
            method=method
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/forecast")
async def forecast_metric(
    plugin_id: str = Query(..., description="Plugin ID"),
    metric_name: str = Query(..., description="Metric name"),
    hours: int = Query(24, ge=1, le=168, description="Historical time window"),
    periods: int = Query(5, ge=1, le=50, description="Forecast periods"),
    method: str = Query("linear", description="Forecast method: linear or moving_average"),
    db: Session = Depends(get_db)
):
    """Forecast future metric values."""
    service = InsightsService(db)
    
    try:
        result = service.forecast_metric(
            plugin_id=plugin_id,
            metric_name=metric_name,
            hours=hours,
            forecast_periods=periods,
            method=method
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecast failed: {str(e)}")


@router.get("/recommendations")
async def get_recommendations(
    plugin_id: str = Query(..., description="Plugin ID"),
    metric_name: str = Query(..., description="Metric name"),
    db: Session = Depends(get_db)
):
    """Get intelligent recommendations for a metric."""
    service = InsightsService(db)
    
    try:
        recommendations = service.generate_recommendations(
            plugin_id=plugin_id,
            metric_name=metric_name
        )
        return {
            "plugin_id": plugin_id,
            "metric_name": metric_name,
            "recommendations": recommendations,
            "count": len(recommendations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendations failed: {str(e)}")

