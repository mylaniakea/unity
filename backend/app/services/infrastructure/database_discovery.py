"""Database discovery service for detecting and monitoring database instances."""
import re
import logging
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import DatabaseInstance, DatabaseType, DatabaseStatus
from app.models import MonitoredServer
from app.services.infrastructure.ssh_service import InfrastructureSSHService
from app.services.encryption import EncryptionService

logger = logging.getLogger(__name__)


class DatabaseDiscoveryService:
    """Service for discovering database instances on remote servers."""
    
    def __init__(self, db: Session):
        self.db = db
        self.ssh_service = InfrastructureSSHService()
        self.encryption_service = EncryptionService()
    
    async def discover_databases(
        self,
        server_id: int,
        db_types: list[DatabaseType],
        test_connection: bool = True
    ) -> dict:
        """
        Discover database instances on a server.
        
        Args:
            server_id: MonitoredServer to discover databases on
            db_types: List of database types to discover
            test_connection: Whether to test connections
            
        Returns:
            Dictionary with discovery results
        """
        server = self.db.query(MonitoredServer).filter(MonitoredServer.id == server_id).first()
        if not server:
            raise ValueError(f"MonitoredServer {server_id} not found")
        
        discovered = []
        errors = []
        
        for db_type in db_types:
            try:
                if db_type == DatabaseType.POSTGRESQL:
                    instances = await self._discover_postgresql(server)
                elif db_type == DatabaseType.MYSQL:
                    instances = await self._discover_mysql(server)
                elif db_type == DatabaseType.MARIADB:
                    instances = await self._discover_mariadb(server)
                elif db_type == DatabaseType.MONGODB:
                    instances = await self._discover_mongodb(server)
                elif db_type == DatabaseType.REDIS:
                    instances = await self._discover_redis(server)
                elif db_type == DatabaseType.MINIO:
                    instances = await self._discover_minio(server)
                else:
                    errors.append(f"Discovery not implemented for {db_type}")
                    continue
                
                for instance_data in instances:
                    # Create or update database instance
                    db_instance = self._upsert_database_instance(server_id, instance_data)
                    
                    # Test connection if requested
                    if test_connection and db_instance:
                        await self._test_connection(server, db_instance)
                    
                    if db_instance:
                        discovered.append(db_instance)
                        
            except Exception as e:
                logger.error(f"Error discovering {db_type} on server {server_id}: {e}")
                errors.append(f"{db_type}: {str(e)}")
        
        return {
            "server_id": server_id,
            "discovered_count": len(discovered),
            "databases": discovered,
            "errors": errors
        }
    
    async def _discover_postgresql(self, server: MonitoredServer) -> list[dict]:
        """Discover PostgreSQL instances."""
        instances = []
        
        # Check for PostgreSQL processes
        result = await self.ssh_service.execute_command(
            server.id,
            "ps aux | grep -E 'postgres.*-D' | grep -v grep || true"
        )
        
        if result["exit_code"] == 0 and result["stdout"].strip():
            # Extract data directories and ports
            for line in result["stdout"].strip().split('\n'):
                port_match = re.search(r'-p\s+(\d+)', line)
                port = int(port_match.group(1)) if port_match else 5432
                
                instances.append({
                    "db_type": DatabaseType.POSTGRESQL,
                    "db_name": "postgres",  # Default database
                    "host": server.host,
                    "port": port,
                    "username": "postgres"
                })
        
        # Also check common ports with netstat
        result = await self.ssh_service.execute_command(
            server.id,
            "netstat -tlnp 2>/dev/null | grep ':5432' | grep LISTEN || true"
        )
        
        if result["exit_code"] == 0 and result["stdout"].strip():
            if not any(i["port"] == 5432 for i in instances):
                instances.append({
                    "db_type": DatabaseType.POSTGRESQL,
                    "db_name": "postgres",
                    "host": server.host,
                    "port": 5432,
                    "username": "postgres"
                })
        
        return instances
    
    async def _discover_mysql(self, server: MonitoredServer) -> list[dict]:
        """Discover MySQL/MariaDB instances."""
        instances = []
        
        # Check for MySQL/MariaDB processes
        result = await self.ssh_service.execute_command(
            server.id,
            "ps aux | grep -E 'mysqld|mariadbd' | grep -v grep || true"
        )
        
        if result["exit_code"] == 0 and result["stdout"].strip():
            # Extract ports
            for line in result["stdout"].strip().split('\n'):
                port_match = re.search(r'--port[=\s]+(\d+)', line)
                port = int(port_match.group(1)) if port_match else 3306
                
                instances.append({
                    "db_type": DatabaseType.MYSQL,
                    "db_name": "mysql",  # Default database
                    "host": server.host,
                    "port": port,
                    "username": "root"
                })
        
        # Also check common ports with netstat
        result = await self.ssh_service.execute_command(
            server.id,
            "netstat -tlnp 2>/dev/null | grep ':3306' | grep LISTEN || true"
        )
        
        if result["exit_code"] == 0 and result["stdout"].strip():
            if not any(i["port"] == 3306 for i in instances):
                instances.append({
                    "db_type": DatabaseType.MYSQL,
                    "db_name": "mysql",
                    "host": server.host,
                    "port": 3306,
                    "username": "root"
                })
        
        return instances
    
    def _upsert_database_instance(self, server_id: int, data: dict) -> Optional[DatabaseInstance]:
        """Create or update a database instance."""
        try:
            # Check if instance already exists
            existing = self.db.query(DatabaseInstance).filter(
                DatabaseInstance.server_id == server_id,
                DatabaseInstance.db_type == data["db_type"],
                DatabaseInstance.host == data["host"],
                DatabaseInstance.port == data["port"]
            ).first()
            
            if existing:
                # Update existing
                existing.db_name = data.get("db_name", existing.db_name)
                existing.username = data.get("username", existing.username)
                existing.updated_at = datetime.now()
                self.db.commit()
                self.db.refresh(existing)
                return existing
            else:
                # Create new
                db_instance = DatabaseInstance(
                    server_id=server_id,
                    db_type=data["db_type"],
                    db_name=data["db_name"],
                    host=data["host"],
                    port=data["port"],
                    username=data.get("username"),
                    status=DatabaseStatus.UNKNOWN
                )
                self.db.add(db_instance)
                self.db.commit()
                self.db.refresh(db_instance)
                return db_instance
                
        except Exception as e:
            logger.error(f"Error upserting database instance: {e}")
            self.db.rollback()
            return None
    
    async def _test_connection(self, server: MonitoredServer, db_instance: DatabaseInstance):
        """Test database connection and update status."""
        try:
            if db_instance.db_type == DatabaseType.POSTGRESQL:
                await self._test_postgresql(server, db_instance)
            elif db_instance.db_type == DatabaseType.MYSQL:
                await self._test_mysql(server, db_instance)
        except Exception as e:
            logger.error(f"Error testing connection for database {db_instance.id}: {e}")
            db_instance.status = DatabaseStatus.ERROR
            db_instance.last_error = str(e)
            db_instance.last_checked = datetime.now()
            self.db.commit()
    
    async def _test_postgresql(self, server: MonitoredServer, db_instance: DatabaseInstance):
        """Test PostgreSQL connection."""
        # Try to get version without credentials (assumes local socket access)
        cmd = f"psql -h {db_instance.host} -p {db_instance.port} -U {db_instance.username} -d {db_instance.db_name} -c 'SELECT version();' 2>&1 || echo 'OFFLINE'"
        
        result = await self.ssh_service.execute_command(server.id, cmd)
        
        if "PostgreSQL" in result["stdout"]:
            # Extract version
            version_match = re.search(r'PostgreSQL ([\d.]+)', result["stdout"])
            version = version_match.group(1) if version_match else "unknown"
            
            db_instance.status = DatabaseStatus.ONLINE
            db_instance.version = version
            db_instance.last_error = None
        else:
            db_instance.status = DatabaseStatus.OFFLINE
            db_instance.last_error = "Cannot connect (may need credentials)"
        
        db_instance.last_checked = datetime.now()
        self.db.commit()
    
    async def _test_mysql(self, server: MonitoredServer, db_instance: DatabaseInstance):
        """Test MySQL connection."""
        # Try to get version
        cmd = f"mysql -h {db_instance.host} -P {db_instance.port} -u {db_instance.username} -e 'SELECT VERSION();' 2>&1 || echo 'OFFLINE'"
        
        result = await self.ssh_service.execute_command(server.id, cmd)
        
        if result["exit_code"] == 0 and "VERSION" not in result["stdout"] and "ERROR" not in result["stdout"]:
            # Extract version
            version_match = re.search(r'([\d.]+)', result["stdout"])
            version = version_match.group(1) if version_match else "unknown"
            
            db_instance.status = DatabaseStatus.ONLINE
            db_instance.version = version
            db_instance.last_error = None
        else:
            db_instance.status = DatabaseStatus.OFFLINE
            db_instance.last_error = "Cannot connect (may need credentials)"
        
        db_instance.last_checked = datetime.now()
        self.db.commit()

    async def collect_metrics_for_database(self, db_instance_id: int) -> dict:
        """
        Collect metrics for a specific database instance.
        
        Args:
            db_instance_id: Database instance ID
            
        Returns:
            Dictionary with metrics collection results
        """
        from app.services.postgres_metrics import PostgreSQLMetricsService
        from app.services.mysql_metrics import MySQLMetricsService
        from app.models import DatabaseType, DatabaseStatus
        
        db_instance = self.db.query(DatabaseInstance).filter(
            DatabaseInstance.id == db_instance_id
        ).first()
        
        if not db_instance:
            return {"success": False, "error": f"Database instance {db_instance_id} not found"}
        
        try:
            metrics_result = {}
            
            if db_instance.db_type == DatabaseType.POSTGRESQL:
                service = PostgreSQLMetricsService()
                metrics_result = service.collect_metrics(
                    host=db_instance.host,
                    port=db_instance.port,
                    database=db_instance.db_name,
                    username=db_instance.username,
                    password_encrypted=db_instance.password_encrypted
                )
            elif db_instance.db_type == DatabaseType.MYSQL:
                service = MySQLMetricsService()
                metrics_result = service.collect_metrics(
                    host=db_instance.host,
                    port=db_instance.port,
                    database=db_instance.db_name,
                    username=db_instance.username,
                    password_encrypted=db_instance.password_encrypted
                )
            else:
                return {"success": False, "error": f"Metrics collection not implemented for {db_instance.db_type}"}
            
            # Update database instance with metrics
            if metrics_result.get("success"):
                db_instance.size_bytes = metrics_result.get("size_bytes")
                db_instance.connection_count = metrics_result.get("connection_count")
                db_instance.active_queries = metrics_result.get("active_queries")
                db_instance.idle_connections = metrics_result.get("idle_connections")
                db_instance.max_connections = metrics_result.get("max_connections")
                db_instance.slow_queries = metrics_result.get("slow_queries")
                db_instance.cache_hit_ratio = metrics_result.get("cache_hit_ratio")
                db_instance.uptime_seconds = metrics_result.get("uptime_seconds")
                db_instance.last_metrics_collection = datetime.now()
                db_instance.metrics_error = None
                db_instance.status = DatabaseStatus.ONLINE
                
                # Update version if available
                if metrics_result.get("version"):
                    db_instance.version = metrics_result.get("version")
            else:
                db_instance.metrics_error = metrics_result.get("error")
                db_instance.status = DatabaseStatus.ERROR
                db_instance.last_metrics_collection = datetime.now()
            
            self.db.commit()
            self.db.refresh(db_instance)
            
            return {
                "success": metrics_result.get("success", False),
                "database_id": db_instance_id,
                "error": metrics_result.get("error")
            }
            
        except Exception as e:
            logger.error(f"Error collecting metrics for database {db_instance_id}: {e}")
            self.db.rollback()
            return {"success": False, "error": str(e)}

    async def _discover_mongodb(self, server: MonitoredServer) -> list[dict]:
        """Discover MongoDB instances."""
        instances = []
        
        # Check for MongoDB processes
        command = (
            "ps aux | grep -E 'mongod' | grep -v grep || true"
        )
        stdout, stderr, exit_code = await self.ssh_service.execute_command(server, command)
        
        if exit_code == 0 and stdout.strip():
            # Parse process output for port
            for line in stdout.strip().split('\n'):
                port_match = re.search(r'--port[= ](\d+)', line)
                port = int(port_match.group(1)) if port_match else 27017
                
                instances.append({
                    "db_type": DatabaseType.MONGODB,
                    "host": "localhost",
                    "port": port,
                    "db_name": "admin",  # Default database
                    "username": ""  # MongoDB often uses no username locally
                })
        
        # Also check standard port
        if not instances:
            check_cmd = "ss -tlnp | grep :27017 || true"
            stdout, stderr, exit_code = await self.ssh_service.execute_command(server, check_cmd)
            if exit_code == 0 and stdout.strip():
                instances.append({
                    "db_type": DatabaseType.MONGODB,
                    "host": "localhost",
                    "port": 27017,
                    "db_name": "admin",
                    "username": ""
                })
        
        return instances
    
    async def _discover_redis(self, server: MonitoredServer) -> list[dict]:
        """Discover Redis instances."""
        instances = []
        
        # Check for Redis processes
        command = (
            "ps aux | grep -E 'redis-server' | grep -v grep || true"
        )
        stdout, stderr, exit_code = await self.ssh_service.execute_command(server, command)
        
        if exit_code == 0 and stdout.strip():
            # Parse process output for port
            for line in stdout.strip().split('\n'):
                port_match = re.search(r':(\d+)', line)
                port = int(port_match.group(1)) if port_match else 6379
                
                instances.append({
                    "db_type": DatabaseType.REDIS,
                    "host": "localhost",
                    "port": port,
                    "db_name": "0",  # Default database
                    "username": ""
                })
        
        # Also check standard port
        if not instances:
            check_cmd = "ss -tlnp | grep :6379 || true"
            stdout, stderr, exit_code = await self.ssh_service.execute_command(server, check_cmd)
            if exit_code == 0 and stdout.strip():
                instances.append({
                    "db_type": DatabaseType.REDIS,
                    "host": "localhost",
                    "port": 6379,
                    "db_name": "0",
                    "username": ""
                })
        
        return instances
    
    async def _discover_mariadb(self, server: MonitoredServer) -> list[dict]:
        """Discover MariaDB instances (MySQL-compatible)."""
        instances = []
        
        # Check for MariaDB processes (similar to MySQL)
        command = (
            "ps aux | grep -E 'mariadbd|mysqld.*mariadb' | grep -v grep || true"
        )
        stdout, stderr, exit_code = await self.ssh_service.execute_command(server, command)
        
        if exit_code == 0 and stdout.strip():
            # Parse process output for port and socket
            for line in stdout.strip().split('\n'):
                port_match = re.search(r'--port[= ](\d+)', line)
                socket_match = re.search(r'--socket[= ]([^\s]+)', line)
                
                port = int(port_match.group(1)) if port_match else 3306
                socket = socket_match.group(1) if socket_match else "/var/run/mysqld/mysqld.sock"
                
                instances.append({
                    "db_type": DatabaseType.MARIADB,
                    "host": "localhost",
                    "port": port,
                    "socket": socket,
                    "db_name": "mysql",  # Default database
                    "username": "root"
                })
        
        # Also check standard MySQL port for MariaDB
        if not instances:
            check_cmd = "ss -tlnp | grep :3306 || true"
            stdout, stderr, exit_code = await self.ssh_service.execute_command(server, check_cmd)
            if exit_code == 0 and "mariadb" in stdout.lower():
                instances.append({
                    "db_type": DatabaseType.MARIADB,
                    "host": "localhost",
                    "port": 3306,
                    "socket": "/var/run/mysqld/mysqld.sock",
                    "db_name": "mysql",
                    "username": "root"
                })
        
        return instances
    
    async def _discover_minio(self, server: MonitoredServer) -> list[dict]:
        """Discover MinIO instances."""
        instances = []
        
        # Check for MinIO processes
        command = (
            "ps aux | grep -E 'minio server' | grep -v grep || true"
        )
        stdout, stderr, exit_code = await self.ssh_service.execute_command(server, command)
        
        if exit_code == 0 and stdout.strip():
            # Parse process output for port (default 9000 for API, 9001 for console)
            for line in stdout.strip().split('\n'):
                port_match = re.search(r'--address[= ]:(\d+)', line)
                port = int(port_match.group(1)) if port_match else 9000
                
                instances.append({
                    "db_type": DatabaseType.MINIO,
                    "host": "localhost",
                    "port": port,
                    "db_name": "minio",  # Not really a database
                    "username": ""  # Uses access keys
                })
        
        # Also check standard MinIO ports
        if not instances:
            for check_port in [9000, 9001]:
                check_cmd = f"ss -tlnp | grep :{check_port} || true"
                stdout, stderr, exit_code = await self.ssh_service.execute_command(server, check_cmd)
                if exit_code == 0 and stdout.strip():
                    instances.append({
                        "db_type": DatabaseType.MINIO,
                        "host": "localhost",
                        "port": check_port,
                        "db_name": "minio",
                        "username": ""
                    })
                    break
        
        return instances
