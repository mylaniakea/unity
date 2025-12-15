from sqlalchemy.orm import Session
from datetime import datetime
from app import models
from app.services.system_info import SystemInfoService
from app.services.ssh import SSHService # Assuming an existing SSH service
import json
import asyncio
import platform
import logging

logger = logging.getLogger(__name__)

class SnapshotService:
    @staticmethod
    async def take_local_snapshot(db: Session, server_id: int):
        # For the backend's own system information
        snapshot_data = SystemInfoService.get_full_system_snapshot()
        new_snapshot = models.ServerSnapshot(
            server_id=server_id,
            timestamp=datetime.utcnow(),
            data=snapshot_data
        )
        db.add(new_snapshot)
        db.commit()
        db.refresh(new_snapshot)
        return new_snapshot

    @staticmethod
    async def take_remote_snapshot(db: Session, server_profile: models.ServerProfile):
        # This method will connect to a remote server via SSH and gather information
        # using commands. This is a more realistic scenario for Homelab Intelligence.
        
        ssh_service = SSHService(server_profile)
        try:
            # Gather OS info
            os_name, _, _ = await ssh_service.execute_command("uname -s")
            os_name = os_name.strip()
            os_release, _, _ = await ssh_service.execute_command("uname -r")
            os_release = os_release.strip()
            hostname, _, _ = await ssh_service.execute_command("hostname")
            hostname = hostname.strip()
            arch, _, _ = await ssh_service.execute_command("uname -m")
            arch = arch.strip()

            # Gather CPU info (simplified)
            cpu_info_raw, _, _ = await ssh_service.execute_command("lscpu | grep 'Model name'")
            cpu_model = cpu_info_raw.split(':')[-1].strip() if cpu_info_raw else "N/A"
            cpu_cores_raw, _, _ = await ssh_service.execute_command("nproc --all")
            cpu_cores = int(cpu_cores_raw.strip()) if cpu_cores_raw.strip().isdigit() else 0
            
            # Get CPU usage via vmstat (last column is idle%, so usage = 100 - idle)
            cpu_usage_percent = 0
            cpu_usage_raw, _, cpu_usage_code = await ssh_service.execute_command("vmstat 1 2 | tail -1 | awk '{print $15}'")
            if cpu_usage_code == 0 and cpu_usage_raw.strip().isdigit():
                idle_percent = int(cpu_usage_raw.strip())
                cpu_usage_percent = 100 - idle_percent

            # Gather Memory info (parse full output from 'free')
            mem_info_raw, _, _ = await ssh_service.execute_command("free -b | grep Mem:")
            total_mem = 0
            used_mem = 0
            available_mem = 0
            if mem_info_raw:
                parts = mem_info_raw.split()
                # Output: Mem: total used free shared buff/cache available
                if len(parts) >= 7:
                    total_mem = int(parts[1]) if parts[1].isdigit() else 0
                    used_mem = int(parts[2]) if parts[2].isdigit() else 0
                    available_mem = int(parts[6]) if parts[6].isdigit() else 0

            # Gather Swap info
            swap_info_raw, _, _ = await ssh_service.execute_command("free -b | grep Swap:")
            total_swap = 0
            used_swap = 0
            swap_percent = 0
            if swap_info_raw:
                parts = swap_info_raw.split()
                if len(parts) >= 4:
                    total_swap = int(parts[1]) if parts[1].isdigit() else 0
                    used_swap = int(parts[2]) if parts[2].isdigit() else 0
                    if total_swap > 0: # Avoid division by zero
                        swap_percent = (used_swap / total_swap) * 100

            # Gather Load Average (1, 5, 15 min)
            load_avg_raw, _, _ = await ssh_service.execute_command("cat /proc/loadavg")
            load_avg_1min = 0.0
            load_avg_5min = 0.0
            load_avg_15min = 0.0
            if load_avg_raw:
                parts = load_avg_raw.split()
                if len(parts) >= 3:
                    try:
                        load_avg_1min = float(parts[0])
                        load_avg_5min = float(parts[1])
                        load_avg_15min = float(parts[2])
                    except ValueError:
                        logger.warning(f"Could not parse load average for {server_profile.name}: {load_avg_raw.strip()}")

            # Gather Process Count
            process_count_raw, _, process_count_code = await ssh_service.execute_command("ps -e --no-headers | wc -l")
            process_count = 0
            if process_count_code == 0 and process_count_raw.strip().isdigit():
                process_count = int(process_count_raw.strip())

            # Gather Open File Descriptors
            # Output is typically: 1024\t0\t102400 (used, free, max)
            file_nr_raw, _, file_nr_code = await ssh_service.execute_command("cat /proc/sys/fs/file-nr")
            open_file_descriptors = 0
            max_file_descriptors = 0
            if file_nr_code == 0 and file_nr_raw.strip():
                parts = file_nr_raw.strip().split() # Split by whitespace
                if len(parts) >= 3 and parts[0].isdigit() and parts[2].isdigit():
                    open_file_descriptors = int(parts[0])
                    max_file_descriptors = int(parts[2])

            # Gather Uptime
            # Output is typically: 3600.00 123.45 (total_uptime_seconds, idle_time_seconds)
            uptime_raw, _, uptime_code = await ssh_service.execute_command("cat /proc/uptime")
            total_uptime_seconds = 0
            if uptime_code == 0 and uptime_raw.strip():
                parts = uptime_raw.strip().split()
                if len(parts) >= 1:
                    try:
                        total_uptime_seconds = int(float(parts[0]))
                    except ValueError:
                        logger.warning(f"Could not parse uptime for {server_profile.name}: {uptime_raw.strip()}")

            # Gather Disk info (simplified, for root fs)
            disk_info_raw, _, _ = await ssh_service.execute_command("df -P -B1 / | tail -n 1")
            total_disk = 0
            used_disk = 0
            if disk_info_raw:
                parts = disk_info_raw.split()
                if len(parts) > 2 and parts[1].isdigit() and parts[2].isdigit():
                    total_disk = int(parts[1])
                    used_disk = int(parts[2])

            # Gather Network info (simplified)
            network_info_raw, _, _ = await ssh_service.execute_command("ip -j addr")
            network_interfaces = json.loads(network_info_raw.strip())

            # Gather packages (example for apt-based systems)
            packages_raw, _, _ = await ssh_service.execute_command("dpkg -l | awk '/^ii/ {print $2 " " $3}'")
            
            # Gather temperatures (requires 'sensors' package and parsing)
            temp_raw, _, temp_code = await ssh_service.execute_command("sensors -j")
            temperatures_data = {}
            if temp_code == 0 and temp_raw.strip():
                try:
                    temperatures_data = json.loads(temp_raw.strip())
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse sensors -j output for {server_profile.name}: {temp_raw.strip()}")
            elif temp_code == 127:
                logger.info(f"'sensors' command not found on {server_profile.name}. Skipping temperature collection.")
            else:
                logger.warning(f"sensors -j command failed on {server_profile.name} with exit code {temp_code}: {temp_raw.strip()}")

            snapshot_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "os": {
                    "system": os_name,
                    "release": os_release,
                    "hostname": hostname,
                    "machine": arch,
                },
                "cpu": {
                    "model": cpu_model,
                    "cores": cpu_cores,
                    "usage_percent": cpu_usage_percent,
                },
                "memory": {
                    "total_bytes": total_mem,
                    "used_bytes": used_mem,
                    "available_bytes": available_mem,
                    "swap_total_bytes": total_swap,
                    "swap_used_bytes": used_swap,
                    "swap_percent": swap_percent,
                },
                "disk": {
                    "root_total_bytes": total_disk,
                    "root_used_bytes": used_disk,
                },
                "load_average": {
                    "1min": load_avg_1min,
                    "5min": load_avg_5min,
                    "15min": load_avg_15min,
                },
                "processes": {
                    "count": process_count,
                },
                "file_descriptors": {
                    "open": open_file_descriptors,
                    "max": max_file_descriptors,
                },
                "uptime_seconds": total_uptime_seconds,
                "network_interfaces": network_interfaces,
                "packages": packages_raw.split('\n') if packages_raw else [],
                "temperatures": temperatures_data,
                "plugins": {},  # Plugin data will be added below
            }
            
            # Collect data from enabled plugins
            enabled_plugins = server_profile.enabled_plugins or []
            if enabled_plugins:
                from app.services.plugin_registry import get_plugin
                plugin_data = {}
                
                for plugin_id in enabled_plugins:
                    plugin = get_plugin(plugin_id)
                    if plugin:
                        try:
                            collect_cmd = plugin.get("collect_cmd", "")
                            if collect_cmd:
                                output, stderr, exit_code = await ssh_service.execute_command(collect_cmd)
                                if exit_code == 0 and output.strip():
                                    parser = plugin.get("parser", "text")
                                    
                                    if parser == "json":
                                        try:
                                            plugin_data[plugin_id] = json.loads(output.strip())
                                        except json.JSONDecodeError:
                                            plugin_data[plugin_id] = {"raw": output.strip(), "parse_error": True}
                                    elif parser == "csv":
                                        # Parse CSV into list of dicts or list of lists
                                        lines = output.strip().split('\n')
                                        plugin_data[plugin_id] = [line.split(',') for line in lines if line.strip()]
                                    elif parser == "jsonl":
                                        # JSON lines (one JSON object per line)
                                        lines = output.strip().split('\n')
                                        parsed_lines = []
                                        for line in lines:
                                            if line.strip():
                                                try:
                                                    parsed_lines.append(json.loads(line.strip()))
                                                except json.JSONDecodeError:
                                                    parsed_lines.append({"raw": line.strip()})
                                        plugin_data[plugin_id] = parsed_lines
                                    else:
                                        # Plain text
                                        plugin_data[plugin_id] = {"raw": output.strip()}
                                else:
                                    plugin_data[plugin_id] = {"error": f"Command failed with exit code {exit_code}", "stderr": stderr}
                        except Exception as plugin_error:
                            logger.warning(f"Error collecting plugin data for {plugin_id} on {server_profile.name}: {plugin_error}")
                            plugin_data[plugin_id] = {"error": str(plugin_error)}
                
                snapshot_data["plugins"] = plugin_data
            
            new_snapshot = models.ServerSnapshot(
                server_id=server_profile.id,
                timestamp=datetime.utcnow(),
                data=snapshot_data
            )
            db.add(new_snapshot)
            db.commit()
            db.refresh(new_snapshot)
            return new_snapshot

        except Exception as e:
            logger.exception(f"Error taking remote snapshot for {server_profile.name}")
            return None