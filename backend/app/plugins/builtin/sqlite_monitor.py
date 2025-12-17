"""
SQLite Monitor Plugin

Monitors SQLite embedded databases - file sizes, integrity, table stats.
Popular for many small applications and embedded use cases.
"""

import sqlite3
import os
from datetime import datetime
from typing import Dict, Any, List

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class SQLiteMonitorPlugin(PluginBase):
    """Monitors SQLite database files"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="sqlite-monitor",
            name="SQLite Monitor",
            version="1.0.0",
            description="Monitors SQLite database files including size, table counts, and integrity checks",
            author="Unity Team",
            category=PluginCategory.DATABASE,
            tags=["sqlite", "database", "embedded", "sql"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=[],  # SQLite is built into Python
            config_schema={
                "type": "object",
                "properties": {
                    "database_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                        "description": "List of SQLite database file paths to monitor"
                    },
                    "scan_directories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                        "description": "Directories to scan for .db and .sqlite files"
                    },
                    "run_integrity_check": {
                        "type": "boolean",
                        "default": False,
                        "description": "Run integrity check (can be slow for large databases)"
                    },
                    "collect_table_stats": {
                        "type": "boolean",
                        "default": True,
                        "description": "Collect per-table statistics"
                    },
                    "max_databases": {
                        "type": "integer",
                        "default": 20,
                        "description": "Maximum number of databases to monitor"
                    }
                },
                "required": []
            }
        )
    
    def _format_bytes(self, bytes_value: int) -> Dict[str, Any]:
        """Format bytes to human-readable form"""
        if bytes_value is None:
            return {"bytes": 0, "formatted": "0 B", "value": 0, "unit": "B"}
        
        units = ["B", "KB", "MB", "GB", "TB"]
        value = float(bytes_value)
        unit_index = 0
        
        while value >= 1024 and unit_index < len(units) - 1:
            value /= 1024
            unit_index += 1
        
        return {
            "bytes": bytes_value,
            "formatted": f"{value:.2f} {units[unit_index]}",
            "value": round(value, 2),
            "unit": units[unit_index]
        }
    
    def _find_sqlite_databases(self, directories: List[str]) -> List[str]:
        """Find SQLite database files in directories"""
        db_files = []
        
        for directory in directories:
            if not os.path.exists(directory) or not os.path.isdir(directory):
                continue
            
            try:
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        if file.endswith(('.db', '.sqlite', '.sqlite3')):
                            full_path = os.path.join(root, file)
                            db_files.append(full_path)
            except Exception:
                continue
        
        return db_files
    
    def _analyze_database(self, db_path: str) -> Dict[str, Any]:
        """Analyze a single SQLite database"""
        result = {
            "path": db_path,
            "exists": os.path.exists(db_path)
        }
        
        if not result["exists"]:
            result["error"] = "File does not exist"
            return result
        
        try:
            # File stats
            stat_info = os.stat(db_path)
            result["file_size"] = self._format_bytes(stat_info.st_size)
            result["last_modified"] = datetime.fromtimestamp(stat_info.st_mtime).isoformat()
            
            # Connect to database
            conn = sqlite3.connect(db_path, timeout=5.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # SQLite version
            cursor.execute("SELECT sqlite_version()")
            result["sqlite_version"] = cursor.fetchone()[0]
            
            # Page size and count
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            
            result["page_size"] = page_size
            result["page_count"] = page_count
            result["database_size"] = self._format_bytes(page_size * page_count)
            
            # Journal mode
            cursor.execute("PRAGMA journal_mode")
            result["journal_mode"] = cursor.fetchone()[0]
            
            # Get tables
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            result["table_count"] = len(tables)
            
            # Table statistics if enabled
            if self.config.get("collect_table_stats", True) and tables:
                table_stats = []
                
                for table in tables[:50]:  # Limit to 50 tables
                    try:
                        # Row count
                        cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                        row_count = cursor.fetchone()[0]
                        
                        # Table size estimate (not exact, but close)
                        cursor.execute(f"SELECT SUM(pgsize) FROM dbstat WHERE name=?", (table,))
                        size_result = cursor.fetchone()
                        table_size = size_result[0] if size_result and size_result[0] else 0
                        
                        table_stats.append({
                            "name": table,
                            "row_count": row_count,
                            "estimated_size": self._format_bytes(table_size)
                        })
                    except Exception as e:
                        table_stats.append({
                            "name": table,
                            "error": str(e)
                        })
                
                result["tables"] = table_stats
            
            # Integrity check if enabled (can be slow)
            if self.config.get("run_integrity_check", False):
                try:
                    cursor.execute("PRAGMA integrity_check")
                    integrity_result = cursor.fetchone()[0]
                    result["integrity"] = {
                        "status": "ok" if integrity_result == "ok" else "error",
                        "message": integrity_result
                    }
                except Exception as e:
                    result["integrity"] = {
                        "status": "error",
                        "message": str(e)
                    }
            
            # Vacuum stats
            cursor.execute("PRAGMA freelist_count")
            freelist_count = cursor.fetchone()[0]
            result["freelist_pages"] = freelist_count
            result["fragmentation"] = {
                "free_pages": freelist_count,
                "free_space": self._format_bytes(freelist_count * page_size)
            }
            
            conn.close()
            
        except sqlite3.Error as e:
            result["error"] = f"SQLite error: {str(e)}"
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
        
        return result
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect SQLite database metrics"""
        
        # Get database paths
        db_paths = list(self.config.get("database_paths", []))
        
        # Scan directories if specified
        scan_dirs = self.config.get("scan_directories", [])
        if scan_dirs:
            discovered_dbs = self._find_sqlite_databases(scan_dirs)
            db_paths.extend(discovered_dbs)
        
        # Remove duplicates
        db_paths = list(set(db_paths))
        
        # Limit number of databases
        max_dbs = self.config.get("max_databases", 20)
        db_paths = db_paths[:max_dbs]
        
        if not db_paths:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "No database paths configured",
                "message": "Please configure database_paths or scan_directories"
            }
        
        # Analyze each database
        databases = []
        total_size = 0
        total_tables = 0
        total_errors = 0
        
        for db_path in db_paths:
            db_info = self._analyze_database(db_path)
            databases.append(db_info)
            
            if "error" in db_info:
                total_errors += 1
            else:
                if "file_size" in db_info:
                    total_size += db_info["file_size"]["bytes"]
                if "table_count" in db_info:
                    total_tables += db_info["table_count"]
        
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_databases": len(databases),
                "total_size": self._format_bytes(total_size),
                "total_tables": total_tables,
                "errors": total_errors
            },
            "databases": databases
        }
        
        return data
    
    async def health_check(self) -> Dict[str, Any]:
        """Check SQLite monitoring health"""
        
        # Check if we have any databases configured
        db_paths = self.config.get("database_paths", [])
        scan_dirs = self.config.get("scan_directories", [])
        
        if not db_paths and not scan_dirs:
            return {
                "healthy": False,
                "message": "No database paths or scan directories configured",
                "details": {
                    "suggestion": "Configure database_paths or scan_directories in plugin config"
                }
            }
        
        # Check if configured paths exist
        accessible_count = 0
        for db_path in db_paths:
            if os.path.exists(db_path):
                accessible_count += 1
        
        for scan_dir in scan_dirs:
            if os.path.exists(scan_dir) and os.path.isdir(scan_dir):
                accessible_count += 1
        
        if accessible_count == 0:
            return {
                "healthy": False,
                "message": "None of the configured paths are accessible",
                "details": {
                    "database_paths": db_paths,
                    "scan_directories": scan_dirs
                }
            }
        
        return {
            "healthy": True,
            "message": "SQLite monitoring is configured",
            "details": {
                "configured_databases": len(db_paths),
                "scan_directories": len(scan_dirs),
                "accessible_paths": accessible_count
            }
        }
