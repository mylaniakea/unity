"""Storage device discovery service."""
import json
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.models import MonitoredServer
from app.models import StorageDevice, DeviceType, HealthStatus
from app.services.infrastructure.ssh_service import InfrastructureSSHService, SSHConnectionError, SSHCommandError
from app.utils.parsers import LsblkParser, SmartctlParser, NvmeParser

logger = logging.getLogger(__name__)


class StorageDiscoveryService:
    """Service for discovering storage devices on remote servers."""
    
    def __init__(self, ssh_service: InfrastructureSSHService):
        """
        Initialize storage discovery service.
        
        Args:
            ssh_service: SSH service instance for remote command execution
        """
        self.ssh_service = ssh_service
    
    async def discover_block_devices(self, server: MonitoredServer) -> List[Dict[str, Any]]:
        """
        Discover block devices using lsblk.
        
        Args:
            server: MonitoredServer instance
            
        Returns:
            List of block device dictionaries
            
        Raises:
            SSHConnectionError: If SSH connection fails
            SSHCommandError: If command execution fails
        """
        try:
            # Execute lsblk with JSON output
            command = "lsblk --json -b -o NAME,PATH,SIZE,TYPE,FSTYPE,MODEL,SERIAL,ROTA,PHY-SEC"
            output, stderr, exit_code = await self.ssh_service.execute_command(server, command)
            
            if exit_code != 0:
                logger.error(f"lsblk command failed: {stderr}")
                raise SSHCommandError(f"lsblk failed: {stderr}")
            
            # Parse JSON output
            devices = LsblkParser.parse_json(output)
            
            # Filter for disk devices only (not partitions)
            disk_devices = [d for d in devices if d.get('type') == 'disk']
            
            logger.info(f"Discovered {len(disk_devices)} block devices on {server.hostname}")
            return disk_devices
            
        except Exception as e:
            logger.error(f"Failed to discover block devices on {server.hostname}: {e}")
            raise
    
    async def get_device_smart_data(
        self, 
        server: MonitoredServer, 
        device_path: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get SMART data for HDD/SSD using smartctl.
        
        Args:
            server: MonitoredServer instance
            device_path: Device path (e.g., /dev/sda)
            
        Returns:
            Dictionary of SMART data or None if not available
        """
        try:
            # Execute smartctl
            command = f"sudo smartctl -a {device_path} --json=c"
            output, stderr, exit_code = await self.ssh_service.execute_command(
                server, 
                command,
                timeout=30
            )
            
            # smartctl may return non-zero exit codes even on success
            # Check if we got JSON output
            if output:
                try:
                    smart_data = json.loads(output)
                    return smart_data
                except json.JSONDecodeError:
                    # Fallback to text parsing
                    logger.warning(f"Could not parse SMART JSON for {device_path}, trying text parse")
                    smart_data = SmartctlParser.parse_info(output)
                    smart_data.update(SmartctlParser.parse_health(output))
                    return smart_data if smart_data else None
            
            logger.warning(f"No SMART data available for {device_path} on {server.hostname}")
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get SMART data for {device_path}: {e}")
            return None
    
    async def get_nvme_smart_data(
        self, 
        server: MonitoredServer, 
        device_path: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get SMART data for NVMe devices using nvme-cli.
        
        Args:
            server: MonitoredServer instance
            device_path: Device path (e.g., /dev/nvme0n1)
            
        Returns:
            Dictionary of SMART data or None if not available
        """
        try:
            # Execute nvme smart-log
            command = f"sudo nvme smart-log {device_path} -o json"
            output, stderr, exit_code = await self.ssh_service.execute_command(
                server,
                command,
                timeout=30
            )
            
            if exit_code != 0 or not output:
                logger.warning(f"nvme smart-log failed for {device_path}: {stderr}")
                return None
            
            try:
                smart_data = json.loads(output)
                return NvmeParser.parse_smart_log(json.dumps(smart_data))
            except json.JSONDecodeError:
                logger.warning(f"Could not parse NVMe SMART JSON for {device_path}")
                return None
                
        except Exception as e:
            logger.warning(f"Failed to get NVMe SMART data for {device_path}: {e}")
            return None
    
    def determine_device_type(self, device_data: Dict[str, Any]) -> DeviceType:
        """
        Determine device type from lsblk data.
        
        Args:
            device_data: Device data from lsblk
            
        Returns:
            DeviceType enum value
        """
        device_path = device_data.get('path', '').lower()
        device_name = device_data.get('name', '').lower()
        rota = device_data.get('rota', False)
        
        # Check if NVMe
        if 'nvme' in device_path or 'nvme' in device_name:
            return DeviceType.NVME
        
        # Check rotation status
        if rota == '1' or rota == 1 or rota is True:
            return DeviceType.HDD
        elif rota == '0' or rota == 0 or rota is False:
            return DeviceType.SSD
        
        return DeviceType.UNKNOWN
    
    def map_smart_to_device(
        self, 
        device: StorageDevice,
        smart_data: Optional[Dict[str, Any]],
        device_type: DeviceType
    ) -> StorageDevice:
        """
        Map SMART data to StorageDevice fields.
        
        Args:
            device: StorageDevice instance to update
            smart_data: SMART data dictionary
            device_type: Type of device
            
        Returns:
            Updated StorageDevice instance
        """
        if not smart_data:
            device.smart_status = HealthStatus.UNKNOWN
            return device
        
        # Store raw data
        device.smart_data_raw = json.dumps(smart_data)
        device.last_checked = datetime.utcnow()
        
        if device_type == DeviceType.NVME:
            # Parse NVMe SMART data
            device.temperature_celsius = smart_data.get('temperature')
            device.power_on_hours = smart_data.get('power_on_hours')
            device.total_bytes_written = smart_data.get('data_units_written_bytes')
            device.total_bytes_read = smart_data.get('data_units_read_bytes')
            device.wear_level_percent = smart_data.get('percentage_used')
            
            # Determine health status
            critical_warning = smart_data.get('critical_warning', 0)
            if critical_warning > 0:
                device.smart_status = HealthStatus.CRITICAL
                device.smart_passed = False
            else:
                device.smart_status = HealthStatus.HEALTHY
                device.smart_passed = True
                
        else:
            # Parse HDD/SSD SMART data
            # Health status
            smart_status = smart_data.get('smart_status', {})
            if isinstance(smart_status, dict):
                passed = smart_status.get('passed', True)
                device.smart_passed = passed
                device.smart_status = HealthStatus.HEALTHY if passed else HealthStatus.FAILED
            else:
                device.smart_status = HealthStatus.UNKNOWN
            
            # Temperature
            temp = smart_data.get('temperature', {})
            if isinstance(temp, dict):
                device.temperature_celsius = temp.get('current')
            elif isinstance(temp, (int, float)):
                device.temperature_celsius = int(temp)
            
            # Power on hours
            poh = smart_data.get('power_on_time', {})
            if isinstance(poh, dict):
                device.power_on_hours = poh.get('hours')
            elif isinstance(poh, (int, float)):
                device.power_on_hours = int(poh)
            
            # Error counters
            device.reallocated_sectors = smart_data.get('reallocated_sector_count', 0)
            device.pending_sectors = smart_data.get('current_pending_sector_count', 0)
            device.uncorrectable_errors = smart_data.get('uncorrectable_error_count', 0)
            
            # Wear level (for SSDs)
            device.wear_level_percent = smart_data.get('wear_leveling_count')
            
            # Data written/read (for SSDs)
            lba_written = smart_data.get('total_lbas_written')
            lba_read = smart_data.get('total_lbas_read')
            if lba_written:
                device.total_bytes_written = lba_written * 512  # Assume 512-byte sectors
            if lba_read:
                device.total_bytes_read = lba_read * 512
        
        return device
    
    async def discover_all_devices(
        self,
        server: MonitoredServer,
        db_session
    ) -> Tuple[List[StorageDevice], List[str]]:
        """
        Discover all storage devices on a server.
        
        Args:
            server: MonitoredServer instance
            db_session: Database session
            
        Returns:
            Tuple of (list of StorageDevice instances, list of error messages)
        """
        discovered_devices = []
        errors = []
        
        try:
            # Discover block devices
            block_devices = await self.discover_block_devices(server)
            
            for device_data in block_devices:
                try:
                    device_path = device_data.get('path')
                    device_name = device_data.get('name')
                    
                    if not device_path:
                        errors.append(f"No path for device {device_name}")
                        continue
                    
                    # Determine device type
                    device_type = self.determine_device_type(device_data)
                    
                    # Check if device already exists
                    existing = db_session.query(StorageDevice).filter(
                        StorageDevice.server_id == server.id,
                        StorageDevice.device_path == device_path
                    ).first()
                    
                    if existing:
                        device = existing
                    else:
                        device = StorageDevice(
                            server_id=server.id,
                            device_name=device_name,
                            device_path=device_path,
                            device_type=device_type
                        )
                    
                    # Update basic info
                    device.size_bytes = device_data.get('size')
                    device.sector_size = device_data.get('phy-sec')
                    device.model = device_data.get('model')
                    device.serial_number = device_data.get('serial')
                    
                    # Get SMART data
                    smart_data = None
                    if device_type == DeviceType.NVME:
                        smart_data = await self.get_nvme_smart_data(server, device_path)
                    elif device_type in (DeviceType.HDD, DeviceType.SSD):
                        smart_data = await self.get_device_smart_data(server, device_path)
                    
                    # Map SMART data to device
                    device = self.map_smart_to_device(device, smart_data, device_type)
                    
                    # Save to database
                    if not existing:
                        db_session.add(device)
                    
                    discovered_devices.append(device)
                    logger.info(f"Discovered device {device_name} on {server.hostname}")
                    
                except Exception as e:
                    error_msg = f"Failed to process device {device_data.get('name')}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue
            
            # Commit all changes
            db_session.commit()
            
            # Refresh all devices to get updated values
            for device in discovered_devices:
                db_session.refresh(device)
            
            logger.info(f"Discovery complete: {len(discovered_devices)} devices, {len(errors)} errors")
            
        except Exception as e:
            error_msg = f"Discovery failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            db_session.rollback()
        
        return discovered_devices, errors
