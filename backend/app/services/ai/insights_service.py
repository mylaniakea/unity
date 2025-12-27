"""
AI-Powered Insights Service

Provides anomaly detection, predictive analytics, and intelligent recommendations.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import numpy as np

from app.models.plugin import PluginMetric

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detects anomalies in time-series metrics."""
    
    @staticmethod
    def detect_anomalies_zscore(
        values: List[float],
        threshold: float = 2.5
    ) -> List[Tuple[int, float, str]]:
        """
        Detect anomalies using Z-score method.
        
        Args:
            values: List of metric values
            threshold: Z-score threshold (default: 2.5)
            
        Returns:
            List of (index, value, severity) tuples
        """
        if len(values) < 3:
            return []
        
        mean = np.mean(values)
        std = np.std(values)
        
        if std == 0:
            return []
        
        anomalies = []
        for i, value in enumerate(values):
            z_score = abs((value - mean) / std)
            if z_score > threshold:
                severity = "critical" if z_score > 3.5 else "warning"
                anomalies.append((i, value, severity))
        
        return anomalies
    
    @staticmethod
    def detect_anomalies_iqr(
        values: List[float],
        factor: float = 1.5
    ) -> List[Tuple[int, float, str]]:
        """
        Detect anomalies using Interquartile Range (IQR) method.
        
        Args:
            values: List of metric values
            factor: IQR factor (default: 1.5)
            
        Returns:
            List of (index, value, severity) tuples
        """
        if len(values) < 4:
            return []
        
        sorted_values = sorted(values)
        q1_idx = len(sorted_values) // 4
        q3_idx = 3 * len(sorted_values) // 4
        
        q1 = sorted_values[q1_idx]
        q3 = sorted_values[q3_idx]
        iqr = q3 - q1
        
        lower_bound = q1 - factor * iqr
        upper_bound = q3 + factor * iqr
        
        anomalies = []
        for i, value in enumerate(values):
            if value < lower_bound or value > upper_bound:
                # Determine severity based on distance from bounds
                distance = min(abs(value - lower_bound), abs(value - upper_bound))
                severity = "critical" if distance > 2 * iqr else "warning"
                anomalies.append((i, value, severity))
        
        return anomalies


class PredictiveAnalytics:
    """Provides predictive analytics for metrics."""
    
    @staticmethod
    def simple_linear_forecast(
        values: List[float],
        periods: int = 5
    ) -> List[float]:
        """
        Simple linear regression forecast.
        
        Args:
            values: Historical values
            periods: Number of periods to forecast
            
        Returns:
            Forecasted values
        """
        if len(values) < 2:
            return []
        
        x = np.arange(len(values))
        y = np.array(values)
        
        # Simple linear regression: y = mx + b
        n = len(x)
        m = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - np.sum(x)**2)
        b = np.mean(y) - m * np.mean(x)
        
        # Forecast future values
        forecast = []
        for i in range(periods):
            future_x = len(values) + i
            forecast.append(m * future_x + b)
        
        return forecast
    
    @staticmethod
    def moving_average_forecast(
        values: List[float],
        window: int = 5,
        periods: int = 5
    ) -> List[float]:
        """
        Moving average forecast.
        
        Args:
            values: Historical values
            window: Moving average window size
            periods: Number of periods to forecast
            
        Returns:
            Forecasted values
        """
        if len(values) < window:
            return []
        
        # Calculate moving average
        ma = np.convolve(values, np.ones(window)/window, mode='valid')
        last_ma = ma[-1]
        
        # Forecast using last moving average
        forecast = [last_ma] * periods
        
        return forecast


class InsightsService:
    """Main service for AI-powered insights."""
    
    def __init__(self, db: Session):
        self.db = db
        self.anomaly_detector = AnomalyDetector()
        self.predictive = PredictiveAnalytics()
    
    def analyze_metric_anomalies(
        self,
        plugin_id: str,
        metric_name: str,
        hours: int = 24,
        method: str = "zscore"
    ) -> Dict[str, Any]:
        """
        Analyze metric for anomalies.
        
        Args:
            plugin_id: Plugin identifier
            metric_name: Metric name
            hours: Time window in hours
            method: Detection method (zscore or iqr)
            
        Returns:
            Analysis results with anomalies
        """
        # Get recent metrics
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        metrics = self.db.query(PluginMetric).filter(
            PluginMetric.plugin_id == plugin_id,
            PluginMetric.metric_name == metric_name,
            PluginMetric.time >= start_time
        ).order_by(PluginMetric.time).all()
        
        if len(metrics) < 3:
            return {
                "plugin_id": plugin_id,
                "metric_name": metric_name,
                "anomalies": [],
                "message": "Insufficient data for analysis"
            }
        
        # Extract values
        values = []
        timestamps = []
        for metric in metrics:
            # Handle JSON values
            value = metric.value
            if isinstance(value, dict):
                value = value.get("value", 0)
            elif isinstance(value, list):
                value = value[0] if value else 0
            
            try:
                values.append(float(value))
                timestamps.append(metric.time.isoformat())
            except (ValueError, TypeError):
                continue
        
        if len(values) < 3:
            return {
                "plugin_id": plugin_id,
                "metric_name": metric_name,
                "anomalies": [],
                "message": "Insufficient valid data"
            }
        
        # Detect anomalies
        if method == "iqr":
            anomalies = self.anomaly_detector.detect_anomalies_iqr(values)
        else:
            anomalies = self.anomaly_detector.detect_anomalies_zscore(values)
        
        # Format results
        anomaly_results = []
        for idx, value, severity in anomalies:
            anomaly_results.append({
                "timestamp": timestamps[idx],
                "value": value,
                "severity": severity,
                "index": idx
            })
        
        return {
            "plugin_id": plugin_id,
            "metric_name": metric_name,
            "time_window_hours": hours,
            "total_data_points": len(values),
            "anomalies": anomaly_results,
            "anomaly_count": len(anomaly_results),
            "anomaly_rate": len(anomaly_results) / len(values) if values else 0
        }
    
    def forecast_metric(
        self,
        plugin_id: str,
        metric_name: str,
        hours: int = 24,
        forecast_periods: int = 5,
        method: str = "linear"
    ) -> Dict[str, Any]:
        """
        Forecast future metric values.
        
        Args:
            plugin_id: Plugin identifier
            metric_name: Metric name
            hours: Historical time window
            forecast_periods: Number of periods to forecast
            method: Forecast method (linear or moving_average)
            
        Returns:
            Forecast results
        """
        # Get historical metrics
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        metrics = self.db.query(PluginMetric).filter(
            PluginMetric.plugin_id == plugin_id,
            PluginMetric.metric_name == metric_name,
            PluginMetric.time >= start_time
        ).order_by(PluginMetric.time).all()
        
        if len(metrics) < 2:
            return {
                "plugin_id": plugin_id,
                "metric_name": metric_name,
                "forecast": [],
                "message": "Insufficient data for forecasting"
            }
        
        # Extract values
        values = []
        for metric in metrics:
            value = metric.value
            if isinstance(value, dict):
                value = value.get("value", 0)
            elif isinstance(value, list):
                value = value[0] if value else 0
            
            try:
                values.append(float(value))
            except (ValueError, TypeError):
                continue
        
        if len(values) < 2:
            return {
                "plugin_id": plugin_id,
                "metric_name": metric_name,
                "forecast": [],
                "message": "Insufficient valid data"
            }
        
        # Generate forecast
        if method == "moving_average":
            forecast_values = self.predictive.moving_average_forecast(values, periods=forecast_periods)
        else:
            forecast_values = self.predictive.simple_linear_forecast(values, periods=forecast_periods)
        
        # Generate future timestamps
        last_time = metrics[-1].time
        forecast_timestamps = []
        for i in range(forecast_periods):
            # Assume metrics are collected every minute (adjust as needed)
            future_time = last_time + timedelta(minutes=i + 1)
            forecast_timestamps.append(future_time.isoformat())
        
        forecast_data = [
            {"timestamp": ts, "value": val}
            for ts, val in zip(forecast_timestamps, forecast_values)
        ]
        
        return {
            "plugin_id": plugin_id,
            "metric_name": metric_name,
            "historical_points": len(values),
            "forecast_periods": forecast_periods,
            "forecast": forecast_data,
            "method": method
        }
    
    def generate_recommendations(
        self,
        plugin_id: str,
        metric_name: str
    ) -> List[Dict[str, Any]]:
        """
        Generate intelligent recommendations based on metrics.
        
        Args:
            plugin_id: Plugin identifier
            metric_name: Metric name
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Analyze recent trends
        analysis = self.analyze_metric_anomalies(plugin_id, metric_name, hours=24)
        
        if analysis.get("anomaly_count", 0) > 5:
            recommendations.append({
                "type": "warning",
                "title": "High Anomaly Rate Detected",
                "message": f"Found {analysis['anomaly_count']} anomalies in the last 24 hours. Consider investigating system stability.",
                "action": "Review system logs and check for underlying issues"
            })
        
        # Forecast analysis
        forecast = self.forecast_metric(plugin_id, metric_name, hours=24, forecast_periods=5)
        
        if forecast.get("forecast"):
            forecast_values = [f["value"] for f in forecast["forecast"]]
            current_trend = forecast_values[-1] - forecast_values[0]
            
            if current_trend > 10:  # Increasing trend
                recommendations.append({
                    "type": "info",
                    "title": "Increasing Trend Detected",
                    "message": f"{metric_name} is trending upward. Monitor closely for potential capacity issues.",
                    "action": "Consider scaling resources if trend continues"
                })
            elif current_trend < -10:  # Decreasing trend
                recommendations.append({
                    "type": "info",
                    "title": "Decreasing Trend Detected",
                    "message": f"{metric_name} is trending downward. System may be recovering.",
                    "action": "Continue monitoring to confirm stability"
                })
        
        return recommendations

