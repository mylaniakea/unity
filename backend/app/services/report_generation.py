from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app import models
import json
import io
import csv
import logging
from fastapi import HTTPException

def _aggregate_system_info(profiles_data: list[models.ServerProfile]):
    # This is a simplified aggregation. In a real scenario, you'd have
    # more granular historical metrics (e.g., from Prometheus, InfluxDB)
    # rather than just the latest snapshot in ServerProfile.

    if not profiles_data:
        return {
            "cpu_usage_percent_avg": 0,
            "memory_percent_avg": 0,
            "disk_percent_avg": 0,
            "total_servers": 0
        }

    total_cpu_percent = 0
    total_memory_percent = 0
    total_disk_percent = 0
    active_servers = 0

    for profile in profiles_data:
        hardware = profile.hardware_info
        if hardware:
            cpu = hardware.get("cpu", {})
            memory = hardware.get("memory", {})
            disk = hardware.get("disk", {})

            if "usage_percent" in cpu:
                total_cpu_percent += cpu["usage_percent"]
            if "percent" in memory:
                total_memory_percent += memory["percent"]
            if "percent" in disk:
                total_disk_percent += disk["percent"]
            
            active_servers += 1

    if active_servers == 0:
        return {
            "cpu_usage_percent_avg": 0,
            "memory_percent_avg": 0,
            "disk_percent_avg": 0,
            "total_servers": 0
        }

    return {
        "cpu_usage_percent_avg": round(total_cpu_percent / active_servers, 2),
        "memory_percent_avg": round(total_memory_percent / active_servers, 2),
        "disk_percent_avg": round(total_disk_percent / active_servers, 2),
        "total_servers": active_servers
    }

async def generate_24_hour_report(db: Session, server_id: int, tenant_id: str = "default"):
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)

        snapshots = db.query(models.ServerSnapshot) \
            .filter(models.ServerSnapshot.server_id == server_id) \
            .filter(models.ServerSnapshot.timestamp >= start_time) \
            .filter(models.ServerSnapshot.timestamp <= end_time) \
            .order_by(models.ServerSnapshot.timestamp.asc()) \
            .all()

        if not snapshots:
            # If no snapshots, no report can be generated from historical data
            return None

        server_profile = db.query(models.ServerProfile).filter(models.ServerProfile.tenant_id == tenant_id).filter(models.ServerProfile.id == server_id).first()
        if not server_profile:
            # This case should ideally not happen if snapshots exist for the server_id
            raise HTTPException(status_code=404, detail="Server profile not found for snapshot data")

        first_snapshot_data = snapshots[0].data
        latest_snapshot_data = snapshots[-1].data

        # Initialize aggregated data structure
        aggregated_data = {
            "period_start": start_time.isoformat(),
            "period_end": end_time.isoformat(),
            "server_name": server_profile.name,
            # Current values from latest snapshot
            "cpu_current": 0,
            "memory_current": 0,
            "disk_current": 0,
            # Averages over the period
            "cpu_usage_percent_avg": 0,
            "memory_percent_avg": 0,
            "disk_percent_avg": 0,
            "snapshot_count": len(snapshots),
            "storage_changes": [],
            "package_updates_available": [],
            "package_updates_recent": [],
            "average_temps_celsius": {},
            "current_temps_celsius": {},
            "syslog_summary": "Not yet implemented.",
            "docker_log_summary": "Not yet implemented.",
            "container_updates_available": [],
            # Plugin data from latest snapshot
            "plugin_data": {},
        }

        # Helper to calculate disk percent from bytes
        def calc_disk_percent(disk_data):
            total = disk_data.get("root_total_bytes", 0)
            used = disk_data.get("root_used_bytes", 0)
            if total > 0:
                return round((used / total) * 100, 2)
            return 0

        # Helper to calculate memory percent from bytes
        def calc_memory_percent(mem_data):
            total = mem_data.get("total_bytes", 0)
            used = mem_data.get("used_bytes", 0)
            if total > 0 and used > 0:
                return round((used / total) * 100, 2)
            return 0

        # Extract CURRENT values from the latest snapshot
        # Snapshot stores keys at root level: cpu, memory, disk (not nested under hardware_info)
        latest_cpu = latest_snapshot_data.get("cpu", {})
        latest_memory = latest_snapshot_data.get("memory", {})
        latest_disk = latest_snapshot_data.get("disk", {})
        
        # Calculate current values
        aggregated_data["cpu_current"] = latest_cpu.get("usage_percent", 0)
        aggregated_data["memory_current"] = calc_memory_percent(latest_memory)
        aggregated_data["disk_current"] = calc_disk_percent(latest_disk)
        
        # Extract current temps from latest snapshot (key is "temperatures" not "temp_sensors")
        latest_temps = latest_snapshot_data.get("temperatures", {})
        for sensor_name, sensor_data in latest_temps.items():
            if isinstance(sensor_data, dict):
                for sub_sensor, readings in sensor_data.items():
                    if isinstance(readings, dict):
                        for key, value in readings.items():
                            if "input" in key.lower():
                                aggregated_data["current_temps_celsius"][f"{sensor_name}.{sub_sensor}"] = value
                                break

        # Calculate averages for CPU, Memory, Disk from snapshots
        total_cpu_percent = 0
        total_memory_percent = 0
        total_disk_percent = 0
        snapshot_count = len(snapshots)

        temp_sums = {}
        temp_counts = {}

        for snap in snapshots:
            # Snapshot stores keys at root level
            cpu = snap.data.get("cpu", {})
            memory = snap.data.get("memory", {})
            disk = snap.data.get("disk", {})

            if "usage_percent" in cpu:
                total_cpu_percent += cpu["usage_percent"]
            
            mem_pct = calc_memory_percent(memory)
            if mem_pct > 0:
                total_memory_percent += mem_pct
            
            disk_pct = calc_disk_percent(disk)
            if disk_pct > 0:
                total_disk_percent += disk_pct
            
            # Aggregate temperatures (key is "temperatures")
            temperatures = snap.data.get("temperatures", {})
            for sensor_name, sensor_data in temperatures.items():
                if isinstance(sensor_data, dict):
                    for sub_sensor, readings in sensor_data.items():
                        if isinstance(readings, dict):
                            for key, value in readings.items():
                                if "input" in key.lower():
                                    temp_key = f"{sensor_name}.{sub_sensor}"
                                    if temp_key not in temp_sums: 
                                        temp_sums[temp_key] = 0
                                        temp_counts[temp_key] = 0
                                    temp_sums[temp_key] += value
                                    temp_counts[temp_key] += 1
                                    break

        if snapshot_count > 0:
            aggregated_data["cpu_usage_percent_avg"] = round(total_cpu_percent / snapshot_count, 2)
            aggregated_data["memory_percent_avg"] = round(total_memory_percent / snapshot_count, 2)
            aggregated_data["disk_percent_avg"] = round(total_disk_percent / snapshot_count, 2)
        
        for sensor_type, total_temp in temp_sums.items():
            if temp_counts[sensor_type] > 0:
                aggregated_data["average_temps_celsius"][sensor_type] = round(total_temp / temp_counts[sensor_type], 2)

        # Storage Changes (from -> to)
        first_disks = first_snapshot_data.get("disk_partitions", [])
        latest_disks = latest_snapshot_data.get("disk_partitions", [])

        for l_disk in latest_disks:
            f_disk = next((d for d in first_disks if d["mountpoint"] == l_disk["mountpoint"]), None)
            if f_disk and f_disk["used"] != l_disk["used"]:
                aggregated_data["storage_changes"].append({
                    "mountpoint": l_disk["mountpoint"],
                    "from_used_gb": round(f_disk["used"] / (1024**3), 2),
                    "to_used_gb": round(l_disk["used"] / (1024**3), 2),
                    "change_gb": round((l_disk["used"] - f_disk["used"]) / (1024**3), 2)
                })

        # Package Updates (available and recent)
        # This assumes `packages` in snapshot.data is a list of strings like "package_name version"
        first_packages = {p.split(" ")[0]: p.split(" ")[1] for p in first_snapshot_data.get("packages", []) if " " in p}
        latest_packages = {p.split(" ")[0]: p.split(" ")[1] for p in latest_snapshot_data.get("packages", []) if " " in p}

        for pkg_name, latest_version in latest_packages.items():
            if pkg_name in first_packages:
                if first_packages[pkg_name] != latest_version: # Package was updated
                    aggregated_data["package_updates_recent"].append({
                        "package": pkg_name,
                        "from_version": first_packages[pkg_name],
                        "to_version": latest_version
                    })
            # Logic for 'available' updates would typically involve checking a package manager API or a different snapshot
            # For now, we'll assume packages not in the first snapshot but in the latest are 'newly available' or installed
            elif pkg_name not in first_packages:
                aggregated_data["package_updates_available"].append({"package": pkg_name, "version": latest_version})

        # Extract plugin data from latest snapshot
        latest_plugins = latest_snapshot_data.get("plugins", {})
        for plugin_id, plugin_output in latest_plugins.items():
            if isinstance(plugin_output, dict) and plugin_output.get("error"):
                # Skip plugins that had errors
                continue
            
            # Parse nvidia-smi CSV data into structured format
            if plugin_id == "nvidia-smi" and isinstance(plugin_output, list):
                gpus = []
                for gpu_row in plugin_output:
                    if isinstance(gpu_row, list) and len(gpu_row) >= 7:
                        gpus.append({
                            "index": gpu_row[0].strip() if gpu_row[0] else "0",
                            "name": gpu_row[1].strip() if gpu_row[1] else "Unknown",
                            "temp_c": int(gpu_row[2].strip()) if gpu_row[2] and gpu_row[2].strip().isdigit() else 0,
                            "utilization_pct": int(gpu_row[3].strip()) if gpu_row[3] and gpu_row[3].strip().isdigit() else 0,
                            "memory_used_mb": int(gpu_row[4].strip()) if gpu_row[4] and gpu_row[4].strip().isdigit() else 0,
                            "memory_total_mb": int(gpu_row[5].strip()) if gpu_row[5] and gpu_row[5].strip().isdigit() else 0,
                            "power_draw_w": float(gpu_row[6].strip()) if gpu_row[6] and gpu_row[6].strip().replace('.', '').isdigit() else 0
                        })
                aggregated_data["plugin_data"]["nvidia-smi"] = {"gpus": gpus}
            
            # docker-stats is already parsed as JSONL
            elif plugin_id == "docker-stats" and isinstance(plugin_output, list):
                containers = []
                for container in plugin_output:
                    if isinstance(container, dict):
                        containers.append({
                            "name": container.get("Name", "unknown"),
                            "cpu_pct": container.get("CPUPerc", "0%"),
                            "mem_pct": container.get("MemPerc", "0%"),
                            "mem_usage": container.get("MemUsage", "0B / 0B"),
                            "net_io": container.get("NetIO", "0B / 0B"),
                            "block_io": container.get("BlockIO", "0B / 0B")
                        })
                aggregated_data["plugin_data"]["docker-stats"] = {"containers": containers}
            
            # For other plugins, just include the raw data
            else:
                aggregated_data["plugin_data"][plugin_id] = plugin_output

        report = models.Report(
            server_id=server_id,
            report_type="24-hour",
            start_time=start_time,
            end_time=end_time,
            aggregated_data=aggregated_data,
            generated_at=datetime.utcnow()
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report
    except Exception as e:
        logging.exception(f"Error generating 24-hour report for server {server_id}")
        raise HTTPException(status_code=500, detail="Failed to generate report")

async def generate_7_day_report(db: Session, server_id: int, tenant_id: str = "default"):
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)

    # Aggregate from 24-hour reports
    # In a fully hierarchical system, this would query the `Report` table
    # for "24-hour" reports within the last 7 days and aggregate their `aggregated_data`.
    # For now, we'll fetch the latest server profile for simplification,
    # but the structure is here for future expansion.
    server_profile = db.query(models.ServerProfile).filter(models.ServerProfile.tenant_id == tenant_id).filter(models.ServerProfile.id == server_id).first()
    if not server_profile:
        return None

    aggregated_data = _aggregate_system_info([server_profile]) # Aggregate for this single server

    report = models.Report(
        server_id=server_id,
        report_type="7-day",
        start_time=start_time,
        end_time=end_time,
        aggregated_data=aggregated_data,
        generated_at=datetime.utcnow()
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report

async def generate_monthly_report(db: Session, server_id: int, tenant_id: str = "default"):
    end_time = datetime.utcnow()
    # Calculate start of the current month
    start_time = datetime(end_time.year, end_time.month, 1)

    # Aggregate from 7-day reports (or directly from profiles for now)
    server_profile = db.query(models.ServerProfile).filter(models.ServerProfile.tenant_id == tenant_id).filter(models.ServerProfile.id == server_id).first()
    if not server_profile:
        return None

    aggregated_data = _aggregate_system_info([server_profile]) # Aggregate for this single server

    report = models.Report(
        server_id=server_id,
        report_type="monthly",
        start_time=start_time,
        end_time=end_time,
        aggregated_data=aggregated_data,
        generated_at=datetime.utcnow()
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report

def export_report_to_csv(report_data: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(report_data.keys())
    # Write data
    writer.writerow(report_data.values())

    return output.getvalue()

def export_report_to_pdf(report_data: dict) -> bytes:
    # Placeholder for PDF generation. Requires a library like ReportLab or fpdf2.
    # Example with a simple text message for now.
    return b"PDF generation not implemented. Report data: " + json.dumps(report_data, indent=2).encode('utf-8')
