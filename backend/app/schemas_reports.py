from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime

class StorageChange(BaseModel):
    mountpoint: str
    from_used_gb: float
    to_used_gb: float
    change_gb: float

class PackageUpdate(BaseModel):
    package: str
    from_version: Optional[str] = None
    to_version: str

class ReportAggregatedData(BaseModel):
    period_start: str
    period_end: str
    server_name: str
    # Current values from latest snapshot
    cpu_current: float = 0
    memory_current: float = 0
    disk_current: float = 0
    snapshot_count: int = 1
    # Averages over period
    cpu_usage_percent_avg: float
    memory_percent_avg: float
    disk_percent_avg: float
    storage_changes: List[StorageChange] = []
    package_updates_available: List[PackageUpdate] = []
    package_updates_recent: List[PackageUpdate] = []
    average_temps_celsius: Dict[str, float] = {}
    current_temps_celsius: Dict[str, float] = {}
    syslog_summary: str = "Not yet implemented."
    docker_log_summary: str = "Not yet implemented."
    container_updates_available: List[str] = []
    # Plugin data
    plugin_data: Dict[str, Any] = {}

class ReportBase(BaseModel):
    server_id: int
    report_type: str # e.g., "24-hour", "7-day", "monthly"
    start_time: datetime
    end_time: datetime
    aggregated_data: ReportAggregatedData = ReportAggregatedData(period_start="", period_end="", server_name="", cpu_usage_percent_avg=0, memory_percent_avg=0, disk_percent_avg=0)

class ReportCreate(ReportBase):
    pass

class Report(ReportBase):
    id: int
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)
