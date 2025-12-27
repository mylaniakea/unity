"""
Database Query Optimization Utilities

Helpers for optimizing database queries and reducing load.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, Query
from sqlalchemy import func, desc, asc
from datetime import datetime, timedelta


def optimize_metrics_query(
    query: Query,
    plugin_id: Optional[str] = None,
    metric_name: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 1000
) -> Query:
    """
    Optimize metrics query with proper filtering and limits.
    
    Args:
        query: Base query
        plugin_id: Filter by plugin
        metric_name: Filter by metric name
        start_time: Start time for time range
        end_time: End time for time range
        limit: Maximum results
        
    Returns:
        Optimized query
    """
    # Apply filters
    if plugin_id:
        query = query.filter_by(plugin_id=plugin_id)
    
    if metric_name:
        query = query.filter_by(metric_name=metric_name)
    
    # Time range filter
    if start_time:
        query = query.filter(func.time >= start_time)
    
    if end_time:
        query = query.filter(func.time <= end_time)
    
    # Order by time descending (newest first)
    query = query.order_by(desc("time"))
    
    # Limit results
    query = query.limit(limit)
    
    return query


def paginate_query(
    query: Query,
    skip: int = 0,
    limit: int = 50,
    max_limit: int = 1000
) -> tuple[Query, int]:
    """
    Apply pagination to a query.
    
    Args:
        query: Base query
        skip: Number of records to skip
        limit: Number of records to return
        max_limit: Maximum allowed limit
        
    Returns:
        Tuple of (paginated query, total count)
    """
    # Get total count before pagination
    total = query.count()
    
    # Enforce max limit
    limit = min(limit, max_limit)
    
    # Apply pagination
    paginated_query = query.offset(skip).limit(limit)
    
    return paginated_query, total


def batch_load_relationships(
    db: Session,
    objects: List[Any],
    relationship_name: str
) -> None:
    """
    Eagerly load relationships to avoid N+1 queries.
    
    Args:
        db: Database session
        objects: List of objects with relationships
        relationship_name: Name of relationship to load
    """
    if not objects:
        return
    
    # Use joinedload to eagerly load relationships
    from sqlalchemy.orm import joinedload
    
    # Get the class of the first object
    model_class = type(objects[0])
    
    # Get IDs
    ids = [obj.id for obj in objects]
    
    # Reload with relationships
    reloaded = db.query(model_class).options(
        joinedload(getattr(model_class, relationship_name))
    ).filter(model_class.id.in_(ids)).all()
    
    # Update original objects (this is a simplified approach)
    # In practice, you'd use SQLAlchemy's relationship loading


def get_time_buckets(
    start_time: datetime,
    end_time: datetime,
    bucket_size_minutes: int = 5
) -> List[tuple[datetime, datetime]]:
    """
    Generate time buckets for aggregating metrics.
    
    Args:
        start_time: Start time
        end_time: End time
        bucket_size_minutes: Size of each bucket in minutes
        
    Returns:
        List of (bucket_start, bucket_end) tuples
    """
    buckets = []
    current = start_time
    
    while current < end_time:
        bucket_end = min(
            current + timedelta(minutes=bucket_size_minutes),
            end_time
        )
        buckets.append((current, bucket_end))
        current = bucket_end
    
    return buckets


def aggregate_metrics_by_bucket(
    db: Session,
    plugin_id: str,
    metric_name: str,
    buckets: List[tuple[datetime, datetime]],
    aggregation: str = "avg"  # avg, min, max, sum
) -> Dict[datetime, float]:
    """
    Aggregate metrics by time buckets.
    
    Args:
        db: Database session
        plugin_id: Plugin ID
        metric_name: Metric name
        buckets: List of time buckets
        aggregation: Aggregation function
        
    Returns:
        Dict mapping bucket start time to aggregated value
    """
    from app.models.plugin import PluginMetric
    
    results = {}
    
    for bucket_start, bucket_end in buckets:
        query = db.query(PluginMetric).filter(
            PluginMetric.plugin_id == plugin_id,
            PluginMetric.metric_name == metric_name,
            PluginMetric.time >= bucket_start,
            PluginMetric.time < bucket_end
        )
        
        if aggregation == "avg":
            result = query.with_entities(func.avg(PluginMetric.value)).scalar()
        elif aggregation == "min":
            result = query.with_entities(func.min(PluginMetric.value)).scalar()
        elif aggregation == "max":
            result = query.with_entities(func.max(PluginMetric.value)).scalar()
        elif aggregation == "sum":
            result = query.with_entities(func.sum(PluginMetric.value)).scalar()
        else:
            result = None
        
        results[bucket_start] = result if result is not None else 0.0
    
    return results

