"""Storage pool discovery service for ZFS and LVM."""
import json
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.models import MonitoredServer
from app.models import StoragePool, PoolType, HealthStatus
from app.services.infrastructure.ssh_service import InfrastructureSSHService, SSHConnectionError, SSHCommandError
from app.utils.parsers import ZpoolParser, LvmParser

logger = logging.getLogger(__name__)


class PoolDiscoveryService:
    """Service for discovering storage pools on remote servers."""
    
    def __init__(self, ssh_service: InfrastructureSSHService):
        """
        Initialize pool discovery service.
        
        Args:
            ssh_service: SSH service instance for remote command execution
        """
        self.ssh_service = ssh_service
    
    async def discover_zfs_pools(self, server: MonitoredServer) -> List[Dict[str, Any]]:
        """
        Discover ZFS pools using zpool commands.
        
        Args:
            server: MonitoredServer instance
            
        Returns:
            List of ZFS pool dictionaries
        """
        try:
            # Execute zpool list
            command = "sudo zpool list -H -p"
            output, stderr, exit_code = await self.ssh_service.execute_command(
                server,
                command,
                timeout=30
            )
            
            if exit_code != 0:
                if "command not found" in stderr.lower() or "zpool: not found" in stderr.lower():
                    logger.info(f"ZFS not available on {server.hostname}")
                    return []
                logger.warning(f"zpool list failed on {server.hostname}: {stderr}")
                return []
            
            if not output.strip():
                logger.info(f"No ZFS pools found on {server.hostname}")
                return []
            
            # Parse zpool list output
            # Format: NAME SIZE ALLOC FREE CKPOINT EXPANDSZ FRAG CAP DEDUP HEALTH ALTROOT
            pools = []
            for line in output.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 10:
                    pool_name = parts[0]
                    
                    # Get detailed status for the pool
                    status_data = await self.get_zpool_status(server, pool_name)
                    
                    pool = {
                        'name': pool_name,
                        'size': int(parts[1]),
                        'alloc': int(parts[2]),
                        'free': int(parts[3]),
                        'frag': int(parts[6].rstrip('%')) if parts[6] != '-' else 0,
                        'cap': int(parts[7].rstrip('%')) if parts[7] != '-' else 0,
                        'health': parts[9],
                        'status_data': status_data
                    }
                    pools.append(pool)
            
            logger.info(f"Discovered {len(pools)} ZFS pools on {server.hostname}")
            return pools
            
        except Exception as e:
            logger.error(f"Failed to discover ZFS pools on {server.hostname}: {e}")
            return []
    
    async def get_zpool_status(self, server: MonitoredServer, pool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed ZFS pool status.
        
        Args:
            server: MonitoredServer instance
            pool_name: Pool name
            
        Returns:
            Dictionary of pool status or None
        """
        try:
            command = f"sudo zpool status -v {pool_name}"
            output, stderr, exit_code = await self.ssh_service.execute_command(
                server,
                command,
                timeout=30
            )
            
            if exit_code != 0 or not output:
                return None
            
            # Parse status using ZpoolParser
            status_data = ZpoolParser.parse_status(output)
            return status_data
            
        except Exception as e:
            logger.warning(f"Failed to get zpool status for {pool_name}: {e}")
            return None
    
    async def discover_lvm_vgs(self, server: MonitoredServer) -> List[Dict[str, Any]]:
        """
        Discover LVM volume groups.
        
        Args:
            server: MonitoredServer instance
            
        Returns:
            List of volume group dictionaries
        """
        try:
            # Execute vgs command
            command = "sudo vgs --noheadings --units b --separator '|' -o vg_name,vg_size,vg_free,vg_attr,lv_count,pv_count"
            output, stderr, exit_code = await self.ssh_service.execute_command(
                server,
                command,
                timeout=30
            )
            
            if exit_code != 0:
                if "command not found" in stderr.lower() or "vgs: not found" in stderr.lower():
                    logger.info(f"LVM not available on {server.hostname}")
                    return []
                logger.warning(f"vgs command failed on {server.hostname}: {stderr}")
                return []
            
            if not output.strip():
                logger.info(f"No LVM volume groups found on {server.hostname}")
                return []
            
            # Parse vgs output
            vgs = LvmParser.parse_vgs(output)
            
            # Get physical volume details for each VG
            for vg in vgs:
                vg['pvs'] = await self.get_lvm_pvs_for_vg(server, vg['vg_name'])
            
            logger.info(f"Discovered {len(vgs)} LVM volume groups on {server.hostname}")
            return vgs
            
        except Exception as e:
            logger.error(f"Failed to discover LVM volume groups on {server.hostname}: {e}")
            return []
    
    async def get_lvm_pvs_for_vg(self, server: MonitoredServer, vg_name: str) -> List[str]:
        """
        Get physical volumes for a volume group.
        
        Args:
            server: MonitoredServer instance
            vg_name: Volume group name
            
        Returns:
            List of physical volume paths
        """
        try:
            command = f"sudo pvs --noheadings --separator '|' -o pv_name,vg_name | grep '{vg_name}'"
            output, stderr, exit_code = await self.ssh_service.execute_command(
                server,
                command,
                timeout=30
            )
            
            if exit_code != 0 or not output:
                return []
            
            # Parse PV paths
            pvs = []
            for line in output.strip().split('\n'):
                parts = line.split('|')
                if len(parts) >= 1:
                    pvs.append(parts[0].strip())
            
            return pvs
            
        except Exception as e:
            logger.warning(f"Failed to get PVs for {vg_name}: {e}")
            return []
    
    def map_zfs_to_storage_pool(
        self,
        server_id: int,
        pool_data: Dict[str, Any],
        db_session
    ) -> StoragePool:
        """
        Map ZFS pool data to StoragePool model.
        
        Args:
            server_id: MonitoredServer ID
            pool_data: Pool data dictionary
            db_session: Database session
            
        Returns:
            StoragePool instance
        """
        pool_name = pool_data['name']
        
        # Check if pool already exists
        existing = db_session.query(StoragePool).filter(
            StoragePool.server_id == server_id,
            StoragePool.pool_name == pool_name
        ).first()
        
        if existing:
            pool = existing
        else:
            pool = StoragePool(
                server_id=server_id,
                pool_name=pool_name,
                pool_type=PoolType.ZFS
            )
        
        # Update capacity
        pool.total_size_bytes = pool_data['size']
        pool.used_size_bytes = pool_data['alloc']
        pool.available_size_bytes = pool_data['free']
        pool.fragmentation_percent = float(pool_data['frag'])
        
        # Map health status
        health = pool_data['health'].upper()
        if health == 'ONLINE':
            pool.health_status = HealthStatus.HEALTHY
        elif health == 'DEGRADED':
            pool.health_status = HealthStatus.WARNING
        elif health in ('FAULTED', 'UNAVAIL'):
            pool.health_status = HealthStatus.CRITICAL
        elif health == 'OFFLINE':
            pool.health_status = HealthStatus.FAILED
        else:
            pool.health_status = HealthStatus.UNKNOWN
        
        pool.status_message = f"Health: {health}"
        
        # Extract RAID level and device count from status if available
        status_data = pool_data.get('status_data', {})
        if status_data:
            pool.raid_level = status_data.get('config', {}).get('type', 'unknown')
            pool.device_count = len(status_data.get('config', {}).get('devices', []))
            pool.pool_data_raw = json.dumps(status_data)
        
        pool.last_checked = datetime.utcnow()
        
        return pool
    
    def map_lvm_to_storage_pool(
        self,
        server_id: int,
        vg_data: Dict[str, Any],
        db_session
    ) -> StoragePool:
        """
        Map LVM volume group data to StoragePool model.
        
        Args:
            server_id: MonitoredServer ID
            vg_data: Volume group data dictionary
            db_session: Database session
            
        Returns:
            StoragePool instance
        """
        vg_name = vg_data['vg_name']
        
        # Check if pool already exists
        existing = db_session.query(StoragePool).filter(
            StoragePool.server_id == server_id,
            StoragePool.pool_name == vg_name
        ).first()
        
        if existing:
            pool = existing
        else:
            pool = StoragePool(
                server_id=server_id,
                pool_name=vg_name,
                pool_type=PoolType.LVM
            )
        
        # Update capacity (values are in bytes as strings, e.g., "10737418240")
        try:
            pool.total_size_bytes = int(vg_data['vg_size'])
            pool.available_size_bytes = int(vg_data['vg_free'])
            pool.used_size_bytes = pool.total_size_bytes - pool.available_size_bytes
        except (ValueError, KeyError):
            logger.warning(f"Could not parse capacity for VG {vg_name}")
        
        # Map health status from attributes
        vg_attr = vg_data.get('vg_attr', '')
        if len(vg_attr) >= 2:
            # First char: w=writeable, r=readonly
            # Second char: - =normal, p=partial
            writeable = vg_attr[0] == 'w'
            partial = len(vg_attr) > 1 and vg_attr[1] == 'p'
            
            if writeable and not partial:
                pool.health_status = HealthStatus.HEALTHY
                pool.status_message = "VG is active and healthy"
            elif partial:
                pool.health_status = HealthStatus.WARNING
                pool.status_message = "VG is partially active"
            else:
                pool.health_status = HealthStatus.WARNING
                pool.status_message = f"VG status: {vg_attr}"
        else:
            pool.health_status = HealthStatus.UNKNOWN
        
        # Store device count and LV count
        pool.device_count = vg_data.get('pv_count', 0)
        pool.raid_level = f"LVM ({vg_data.get('lv_count', 0)} LVs)"
        
        # Store raw data
        pool.pool_data_raw = json.dumps(vg_data)
        pool.last_checked = datetime.utcnow()
        
        return pool
    
    async def discover_all_pools(
        self,
        server: MonitoredServer,
        db_session
    ) -> Tuple[List[StoragePool], List[str]]:
        """
        Discover all storage pools on a server.
        
        Args:
            server: MonitoredServer instance
            db_session: Database session
            
        Returns:
            Tuple of (list of StoragePool instances, list of error messages)
        """
        discovered_pools = []
        errors = []
        zfs_count = 0
        lvm_count = 0
        
        try:
            # Discover ZFS pools
            zfs_pools = await self.discover_zfs_pools(server)
            for pool_data in zfs_pools:
                try:
                    pool = self.map_zfs_to_storage_pool(server.id, pool_data, db_session)
                    if not pool.id:
                        db_session.add(pool)
                    discovered_pools.append(pool)
                    zfs_count += 1
                except Exception as e:
                    error_msg = f"Failed to process ZFS pool {pool_data.get('name')}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Discover LVM volume groups
            lvm_vgs = await self.discover_lvm_vgs(server)
            for vg_data in lvm_vgs:
                try:
                    pool = self.map_lvm_to_storage_pool(server.id, vg_data, db_session)
                    if not pool.id:
                        db_session.add(pool)
                    discovered_pools.append(pool)
                    lvm_count += 1
                except Exception as e:
                    error_msg = f"Failed to process LVM VG {vg_data.get('vg_name')}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Commit all changes
            db_session.commit()
            
            # Refresh all pools to get updated values
            for pool in discovered_pools:
                db_session.refresh(pool)
            
            logger.info(f"Pool discovery complete: {zfs_count} ZFS, {lvm_count} LVM, {len(errors)} errors")
            
        except Exception as e:
            error_msg = f"Pool discovery failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            db_session.rollback()
        
        return discovered_pools, errors
