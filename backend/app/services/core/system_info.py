import platform
import psutil
import socket
import shutil
import os
import time
import resource
from datetime import datetime

# Use host directories if available (for K8s deployments with hostPath mounts)
PROC_DIR = '/host/proc' if os.path.exists('/host/proc') else '/proc'
SYS_DIR = '/host/sys' if os.path.exists('/host/sys') else '/sys'

# Configure psutil to use host proc if available
if PROC_DIR != '/proc':
    psutil.PROCFS_PATH = PROC_DIR


class SystemInfoService:
    @staticmethod
    def get_hardware_info():
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu": {
                "physical_cores": psutil.cpu_count(logical=False),
                "total_cores": psutil.cpu_count(logical=True),
                "usage_percent": cpu_usage,
                "frequency": psutil.cpu_freq().current if psutil.cpu_freq() else "N/A"
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            }
        }

    @staticmethod
    def get_memory_bytes():
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "total_bytes": vm.total,
            "used_bytes": vm.used,
            "available_bytes": vm.available,
            "swap_total_bytes": swap.total,
            "swap_used_bytes": swap.used,
            "swap_percent": swap.percent,
        }

    @staticmethod
    @staticmethod
    def get_os_info():
        # Try to read hostname from NODE_NAME env var (k8s downward API), otherwise use container hostname
        hostname = os.getenv('NODE_NAME', socket.gethostname())
        
        # Try to read from host /etc/hostname if available (Docker host mount)
        if not os.getenv('NODE_NAME'):
            try:
                if os.path.exists('/host/etc/hostname'):
                    with open('/host/etc/hostname', 'r') as f:
                        hostname = f.read().strip()
                elif os.path.exists(f'{PROC_DIR}/sys/kernel/hostname'):
                    with open(f'{PROC_DIR}/sys/kernel/hostname', 'r') as f:
                        hostname = f.read().strip()
            except Exception:
                pass

        return {
            "system": platform.system(),
            "node": hostname,
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "hostname": hostname
        }

    @staticmethod
    def get_network_info():
        network_stats = {}
        
        # Get addresses for all interfaces
        addrs = psutil.net_if_addrs()
        # Get status for all interfaces
        stats = psutil.net_if_stats()
        # Get I/O counters per interface
        io_counters = psutil.net_io_counters(pernic=True)

        for interface_name, interface_addresses in addrs.items():
            info = {
                "addresses": [],
                "mac_address": None,
                "status": {},
                "io_counters": {}
            }

            # Extract addresses
            for addr in interface_addresses:
                if addr.family == socket.AF_INET:
                    info["addresses"].append({
                        "family": "IPv4",
                        "address": addr.address,
                        "netmask": addr.netmask,
                        "broadcast": addr.broadcast
                    })
                elif addr.family == socket.AF_INET6:
                    info["addresses"].append({
                        "family": "IPv6",
                        "address": addr.address,
                        "netmask": addr.netmask
                    })
                elif addr.family == psutil.AF_LINK:
                    info["mac_address"] = addr.address

            # Interface status
            if interface_name in stats:
                stat = stats[interface_name]
                info["status"] = {
                    "is_up": stat.isup,
                    "duplex": stat.duplex,
                    "speed_mbps": stat.speed,
                    "mtu": stat.mtu
                }

            # I/O counters
            if interface_name in io_counters:
                counters = io_counters[interface_name]
                info["io_counters"] = {
                    "bytes_sent": counters.bytes_sent,
                    "bytes_recv": counters.bytes_recv,
                    "packets_sent": counters.packets_sent,
                    "packets_recv": counters.packets_recv,
                    "errors_in": counters.errin,
                    "errors_out": counters.errout,
                    "drops_in": counters.dropin,
                    "drops_out": counters.dropout
                }

            network_stats[interface_name] = info

        return network_stats

    @staticmethod
    def get_load_average():
        try:
            one, five, fifteen = os.getloadavg()
        except OSError:
            one = five = fifteen = 0.0
        return {
            "1min": one,
            "5min": five,
            "15min": fifteen
        }

    @staticmethod
    def get_process_info():
        try:
            count = len(psutil.pids())
        except Exception:
            count = None
        return {
            "count": count
        }

    @staticmethod
    def get_file_descriptors():
        open_fds = 0
        try:
            for proc in psutil.process_iter(['pid']):
                try:
                    open_fds += proc.num_fds()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            open_fds = None

        try:
            max_fds = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
        except Exception:
            max_fds = None

        return {
            "open": open_fds,
            "max": max_fds
        }

    @staticmethod
    def get_uptime_seconds():
        try:
            return int(time.time() - psutil.boot_time())
        except Exception:
            return None

    @staticmethod
    def get_network_totals():
        try:
            counters = psutil.net_io_counters()
            return {
                "bytes_sent": counters.bytes_sent,
                "bytes_recv": counters.bytes_recv,
                "packets_sent": counters.packets_sent,
                "packets_recv": counters.packets_recv
            }
        except Exception:
            return None

    @staticmethod
    def get_full_system_snapshot():
        hardware_info = SystemInfoService.get_hardware_info()
        os_info = SystemInfoService.get_os_info()
        network_info = SystemInfoService.get_network_info()
        network_totals = SystemInfoService.get_network_totals()
        load_average = SystemInfoService.get_load_average()
        process_info = SystemInfoService.get_process_info()
        file_descriptors = SystemInfoService.get_file_descriptors()
        memory_bytes = SystemInfoService.get_memory_bytes()
        uptime_seconds = SystemInfoService.get_uptime_seconds()

        disk_partitions = []
        total_disk = 0
        used_disk = 0
        free_disk = 0

        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_partitions.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent
                })
                total_disk += usage.total
                used_disk += usage.used
                free_disk += usage.free
            except PermissionError:
                continue

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "hardware_info": hardware_info,
            "os_info": os_info,
            "network_info": network_info,
            "network_totals": network_totals,
            "load_average": load_average,
            "processes": process_info,
            "file_descriptors": file_descriptors,
            "memory": memory_bytes,
            "uptime_seconds": uptime_seconds,
            "disk_partitions": disk_partitions,
            "disk_totals": {
                "total": total_disk,
                "used": used_disk,
                "free": free_disk,
                "percent": (used_disk / total_disk * 100) if total_disk > 0 else 0
            },
            "boot_time": psutil.boot_time(),
            "users": [
                {
                    "name": user.name,
                    "host": user.host,
                    "started": user.started
                }
                for user in psutil.users()
            ],
            "temp_sensors": psutil.sensors_temperatures() if hasattr(psutil, 'sensors_temperatures') else {}
        }

    @staticmethod
    def get_full_report():
        return {
            "hardware": SystemInfoService.get_hardware_info(),
            "os": SystemInfoService.get_os_info(),
            "network": SystemInfoService.get_network_info(),
            "network_totals": SystemInfoService.get_network_totals(),
            "memory": SystemInfoService.get_memory_bytes(),
            "load_average": SystemInfoService.get_load_average(),
            "processes": SystemInfoService.get_process_info(),
            "file_descriptors": SystemInfoService.get_file_descriptors(),
            "uptime_seconds": SystemInfoService.get_uptime_seconds()
        }
