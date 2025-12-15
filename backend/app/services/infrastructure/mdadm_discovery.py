"""mdadm RAID discovery and monitoring service."""
import logging
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models import MonitoredServer
from app.models import storage import StoragePool, PoolType
from app.services.infrastructure.ssh_service import InfrastructureSSHService, SSHConnectionError

logger = logging.getLogger(__name__)


class MdadmDiscoveryService:
    """Service for discovering and monitoring mdadm RAID arrays."""
    
    def __init__(self, ssh_service: InfrastructureSSHService):
        self.ssh_service = ssh_service
    
    async def discover_raids(self, server: MonitoredServer, db: Session) -> List[StoragePool]:
        """
        Discover mdadm RAID arrays on a server.
        
        Args:
            server: MonitoredServer to scan
            db: Database session
            
        Returns:
            List of discovered RAID arrays as StoragePool objects
        """
        logger.info(f"Discovering mdadm RAIDs on {server.hostname}")
        
        try:
            # Check if mdadm is available
            check_command = "which mdadm"
            stdout, stderr, exit_code = await self.ssh_service.execute_command(
                server, check_command
            )
            
            if exit_code != 0:
                logger.debug(f"mdadm not found on {server.hostname}")
                return []
            
            # Read /proc/mdstat for RAID arrays
            raids = await self._parse_mdstat(server)
            
            if not raids:
                logger.debug(f"No mdadm RAIDs found on {server.hostname}")
                return []
            
            # Get detailed info for each array
            pools = []
            for raid_name in raids.keys():
                detail = await self._get_raid_detail(server, raid_name)
                if detail:
                    raids[raid_name].update(detail)
                    pool = await self._create_pool_from_raid(server, raid_name, raids[raid_name], db)
                    if pool:
                        pools.append(pool)
            
            logger.info(f"Found {len(pools)} mdadm RAID arrays on {server.hostname}")
            return pools
            
        except SSHConnectionError as e:
            logger.error(f"SSH error discovering mdadm on {server.hostname}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error discovering mdadm on {server.hostname}: {e}", exc_info=True)
            return []
    
    async def _parse_mdstat(self, server: MonitoredServer) -> Dict[str, Dict[str, Any]]:
        """
        Parse /proc/mdstat file.
        
        Returns:
            Dictionary of RAID arrays with basic info
        """
        command = "cat /proc/mdstat"
        stdout, stderr, exit_code = await self.ssh_service.execute_command(server, command)
        
        if exit_code != 0:
            logger.warning(f"Could not read /proc/mdstat on {server.hostname}")
            return {}
        
        raids = {}
        current_raid = None
        
        for line in stdout.strip().split('\n'):
            # Match RAID line: md0 : active raid1 sdb1[1] sda1[0]
            raid_match = re.match(r'^(md\d+)\s*:\s*(\w+)\s+(\w+)\s+(.+)$', line)
            if raid_match:
                raid_name, state, raid_level, devices = raid_match.groups()
                current_raid = raid_name
                
                # Parse devices
                device_list = re.findall(r'(\w+)\[\d+\]', devices)
                
                raids[raid_name] = {
                    'name': raid_name,
                    'state': state,  # active, inactive
                    'level': raid_level,  # raid0, raid1, raid5, raid10
                    'devices': device_list,
                    'device_count': len(device_list)
                }
                continue
            
            # Match status line: 1953513408 blocks super 1.2 [2/2] [UU]
            if current_raid and 'blocks' in line:
                blocks_match = re.search(r'(\d+)\s+blocks', line)
                status_match = re.search(r'\[(\d+)/(\d+)\]\s+\[([U_]+)\]', line)
                
                if blocks_match:
                    raids[current_raid]['blocks'] = int(blocks_match.group(1))
                    raids[current_raid]['size_bytes'] = int(blocks_match.group(1)) * 1024
                
                if status_match:
                    total_devs, active_devs, status = status_match.groups()
                    raids[current_raid]['total_devices'] = int(total_devs)
                    raids[current_raid]['active_devices'] = int(active_devs)
                    raids[current_raid]['health_status'] = status  # e.g., "UU" or "U_"
                    raids[current_raid]['degraded'] = active_devs != total_devs
            
            # Match sync status: [>....................]  resync =  5.7% (...)
            if current_raid and ('resync' in line or 'recovery' in line or 'reshape' in line):
                sync_match = re.search(r'(resync|recovery|reshape)\s*=\s*([\d.]+)%', line)
                if sync_match:
                    operation, percent = sync_match.groups()
                    raids[current_raid]['sync_operation'] = operation
                    raids[current_raid]['sync_percent'] = float(percent)
        
        return raids
    
    async def _get_raid_detail(self, server: MonitoredServer, raid_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a RAID array using mdadm --detail.
        
        Args:
            server: MonitoredServer connection
            raid_name: Name of RAID device (e.g., md0)
            
        Returns:
            Dictionary with detailed RAID information
        """
        command = f"sudo mdadm --detail /dev/{raid_name}"
        stdout, stderr, exit_code = await self.ssh_service.execute_command(server, command)
        
        if exit_code != 0:
            logger.warning(f"Could not get mdadm detail for {raid_name}: {stderr}")
            return None
        
        detail = {}
        
        for line in stdout.strip().split('\n'):
            line = line.strip()
            
            # Parse key-value pairs
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip().lower().replace(' ', '_')
                    value = parts[1].strip()
                    
                    # Store useful fields
                    if key in ['raid_level', 'array_size', 'used_dev_size', 'raid_devices', 
                               'total_devices', 'persistence', 'update_time', 'state', 
                               'active_devices', 'working_devices', 'failed_devices',
                               'spare_devices']:
                        detail[key] = value
        
        return detail
    
    async def _create_pool_from_raid(
        self, 
        server: MonitoredServer, 
        raid_name: str, 
        raid_data: Dict[str, Any],
        db: Session
    ) -> Optional[StoragePool]:
        """
        Create or update StoragePool from RAID data.
        
        Args:
            server: MonitoredServer object
            raid_name: RAID device name
            raid_data: Parsed RAID information
            db: Database session
            
        Returns:
            StoragePool object
        """
        # Check if pool already exists
        existing_pool = db.query(StoragePool).filter(
            StoragePool.server_id == server.id,
            StoragePool.name == raid_name
        ).first()
        
        # Determine health status
        health = "ONLINE"
        if raid_data.get('degraded'):
            health = "DEGRADED"
        elif raid_data.get('state', '').lower() == 'inactive':
            health = "OFFLINE"
        
        pool_data = {
            'name': raid_name,
            'pool_type': PoolType.MDADM,
            'size_bytes': raid_data.get('size_bytes', 0),
            'used_bytes': 0,  # mdadm doesn't provide this easily
            'free_bytes': 0,
            'health': health,
            'raid_level': raid_data.get('level', 'unknown'),
            'device_count': raid_data.get('device_count', 0),
            'metadata': {
                'state': raid_data.get('state'),
                'active_devices': raid_data.get('active_devices'),
                'total_devices': raid_data.get('total_devices'),
                'health_status': raid_data.get('health_status'),
                'degraded': raid_data.get('degraded', False),
                'sync_operation': raid_data.get('sync_operation'),
                'sync_percent': raid_data.get('sync_percent'),
                'devices': raid_data.get('devices', [])
            }
        }
        
        if existing_pool:
            # Update existing pool
            for key, value in pool_data.items():
                setattr(existing_pool, key, value)
            return existing_pool
        else:
            # Create new pool
            pool = StoragePool(
                server_id=server.id,
                **pool_data
            )
            db.add(pool)
            return pool
