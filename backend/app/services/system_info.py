import platform
import psutil
import socket
import shutil
import os
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
    def get_os_info():
        # Try to read hostname from host if available
        hostname = socket.gethostname()
        try:
            if os.path.exists(f'{PROC_DIR}/sys/kernel/hostname'):
                with open(f'{PROC_DIR}/sys/kernel/hostname', 'r') as f:
                    hostname = f.read().strip()
        except:
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

            # Extract status (if available)
            if interface_name in stats:
                s = stats[interface_name]
                info["status"] = {
                    "is_up": s.isup,
                    "duplex": str(s.duplex), # DUPLEX_FULL, DUPLEX_HALF, DUPLEX_UNKNOWN
                    "speed_mbps": s.speed, # in Mbps
                    "mtu": s.mtu
                }
            
            # Extract I/O counters (if available)
            if interface_name in io_counters:
                io = io_counters[interface_name]
                info["io_counters"] = {
                    "bytes_sent": io.bytes_sent,
                    "bytes_recv": io.bytes_recv,
                    "packets_sent": io.packets_sent,
                    "packets_recv": io.packets_recv,
                    "errors_in": io.errin,
                    "errors_out": io.errout,
                    "drops_in": io.dropin,
                    "drops_out": io.dropout
                }
            
            network_stats[interface_name] = info
        
        return network_stats

    @staticmethod
    def get_full_system_snapshot():
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "hardware_info": SystemInfoService.get_hardware_info(),
            "os_info": SystemInfoService.get_os_info(),
            "network_info": SystemInfoService.get_network_info(),
            # You can add more here, e.g., running processes, logged-in users, etc.
            "disk_partitions": [{
                "device": p.device, 
                "mountpoint": p.mountpoint, 
                "fstype": p.fstype,
                "total": shutil.disk_usage(p.mountpoint).total,
                "used": shutil.disk_usage(p.mountpoint).used,
                "free": shutil.disk_usage(p.mountpoint).free,
                "percent": shutil.disk_usage(p.mountpoint).percent
            } for p in psutil.disk_partitions() if shutil.disk_usage(p.mountpoint)], # Filter out inaccessible partitions
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            "users": [{
                "name": u.name, 
                "host": u.host, 
                "started": datetime.fromtimestamp(u.started).isoformat()}
            for u in psutil.users()],
            "temp_sensors": psutil.sensors_temperatures() if hasattr(psutil, 'sensors_temperatures') else {}
        }
