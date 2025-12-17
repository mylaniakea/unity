"""
Parsers for storage and system information.
These parse output from commands like lsblk, smartctl, and nvme.
"""
from typing import Dict, List, Any, Optional
import json


class LsblkParser:
    """Parses lsblk JSON output."""
    
    @staticmethod
    def parse(output: str) -> List[Dict[str, Any]]:
        """Parse lsblk --json output."""
        try:
            data = json.loads(output)
            return data.get("blockdevices", [])
        except (json.JSONDecodeError, KeyError):
            return []


class SmartctlParser:
    """Parses smartctl JSON output."""
    
    @staticmethod
    def parse(output: str) -> Dict[str, Any]:
        """Parse smartctl --json output."""
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {}
    
    @staticmethod
    def get_health_status(data: Dict[str, Any]) -> Optional[str]:
        """Extract health status from smartctl data."""
        return data.get("smart_status", {}).get("passed")
    
    @staticmethod
    def get_temperature(data: Dict[str, Any]) -> Optional[int]:
        """Extract temperature from smartctl data."""
        return data.get("temperature", {}).get("current")
    
    @staticmethod
    def get_power_on_hours(data: Dict[str, Any]) -> Optional[int]:
        """Extract power-on hours from smartctl data."""
        return data.get("power_on_time", {}).get("hours")


class NvmeParser:
    """Parses nvme CLI output."""
    
    @staticmethod
    def parse_smart_log(output: str) -> Dict[str, Any]:
        """Parse nvme smart-log output."""
        result = {}
        for line in output.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                result[key.strip()] = value.strip()
        return result
    
    @staticmethod
    def get_wear_level(data: Dict[str, Any]) -> Optional[float]:
        """Extract wear level percentage from NVMe data."""
        wear = data.get("percentage_used", data.get("Percentage Used"))
        if wear:
            try:
                return float(wear.rstrip("%"))
            except (ValueError, AttributeError):
                pass
        return None


class ZpoolParser:
    """Parses zpool command output."""
    
    @staticmethod
    def parse_list(output: str) -> List[Dict[str, Any]]:
        """Parse zpool list output."""
        pools = []
        lines = output.strip().splitlines()
        if len(lines) < 2:
            return pools
        
        headers = lines[0].split()
        for line in lines[1:]:
            values = line.split()
            if len(values) >= len(headers):
                pool = dict(zip(headers, values))
                pools.append(pool)
        return pools
    
    @staticmethod
    def parse_status(output: str) -> Dict[str, Any]:
        """Parse zpool status output."""
        result = {
            "pool_name": None,
            "state": None,
            "status": None,
            "action": None,
            "scan": None,
            "config": []
        }
        
        current_section = None
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("pool:"):
                result["pool_name"] = line.split(":", 1)[1].strip()
            elif line.startswith("state:"):
                result["state"] = line.split(":", 1)[1].strip()
            elif line.startswith("status:"):
                current_section = "status"
                result["status"] = line.split(":", 1)[1].strip()
            elif line.startswith("action:"):
                current_section = "action"
                result["action"] = line.split(":", 1)[1].strip()
            elif line.startswith("scan:"):
                result["scan"] = line.split(":", 1)[1].strip()
        
        return result


class LvmParser:
    """Parses LVM command output."""
    
    @staticmethod
    def parse_vgs(output: str) -> List[Dict[str, Any]]:
        """Parse vgs (volume group) output."""
        vgs = []
        lines = output.strip().splitlines()
        if len(lines) < 2:
            return vgs
        
        headers = lines[0].split()
        for line in lines[1:]:
            values = line.split()
            if len(values) >= len(headers):
                vg = dict(zip(headers, values))
                vgs.append(vg)
        return vgs
    
    @staticmethod
    def parse_lvs(output: str) -> List[Dict[str, Any]]:
        """Parse lvs (logical volume) output."""
        lvs = []
        lines = output.strip().splitlines()
        if len(lines) < 2:
            return lvs
        
        headers = lines[0].split()
        for line in lines[1:]:
            values = line.split()
            if len(values) >= len(headers):
                lv = dict(zip(headers, values))
                lvs.append(lv)
        return lvs
    
    @staticmethod
    def parse_pvs(output: str) -> List[Dict[str, Any]]:
        """Parse pvs (physical volume) output."""
        pvs = []
        lines = output.strip().splitlines()
        if len(lines) < 2:
            return pvs
        
        headers = lines[0].split()
        for line in lines[1:]:
            values = line.split()
            if len(values) >= len(headers):
                pv = dict(zip(headers, values))
                pvs.append(pv)
        return pvs
