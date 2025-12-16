# Homelab Intelligence Hub - Implementation Plan

## Overview
This plan outlines the step-by-step implementation of the unified Homelab Intelligence Hub with plugin architecture. We'll build the hub foundation first while bd-store and uptainer are being finalized, then convert them to plugins later.

## Current Status
- ✅ homelab-intelligence: Core monitoring app with hardcoded plugins
- 🚧 bd-store: Storage & database monitoring (in development)
- 🚧 uptainer: Container updater with AI (in development)
- 📋 kc-booth: SSH key & certificate management (needs integration decision)
- 📋 hi-hub: Empty (will become the unified hub)

## Strategic Approach

### Phase 0: Decision Points (Week 0)
Before starting implementation, make these architectural decisions:

#### Decision 1: Hub Location
**Options:**
- **A)** Build new hub in `hi-hub/` from scratch
- **B)** Evolve `homelab-intelligence/` into the hub
- **C)** Fork `homelab-intelligence/` to `hi-hub/` and enhance

**Recommendation:** **Option B** - Evolve homelab-intelligence
- It already has authentication, SSH, monitoring, alerts, AI, dashboard
- Has production-ready features (RBAC, JWT auth, terminal access)
- Well-structured FastAPI + React app
- Just needs plugin architecture added

**Action:** Rename/symlink `homelab-intelligence` to `hi-hub` for clarity

#### Decision 2: KC-Booth Integration
**Options:**
- **A)** Integrate into hub as core service
- **B)** Keep as standalone sidecar service
- **C)** Convert to plugin

**Recommendation:** **Option A** - Integrate into hub core
- SSH keys/certs are infrastructure dependencies for plugins
- Centralized credential management improves security
- Reduces operational complexity

**Action:** Merge kc-booth services into hub core

#### Decision 3: Database Strategy
**Options:**
- **A)** Single PostgreSQL for everything (separate schemas)
- **B)** Separate PostgreSQL per service
- **C)** PostgreSQL + TimescaleDB for time-series

**Recommendation:** **Option C** for production, **Option A** for dev
- Use PostgreSQL for hub/plugin metadata
- Use TimescaleDB extension for plugin metrics (time-series optimized)
- Single instance, multiple databases/schemas

---

## Implementation Phases

### Phase 1: Hub Foundation (Week 1-2)
**Goal:** Prepare homelab-intelligence to become the unified hub

#### 1.1 Repository Setup
- [ ] **Backup current homelab-intelligence** (git tag or branch)
- [ ] **Create feature branch:** `git checkout -b feature/plugin-architecture`
- [ ] **Update README** to reflect it's now "the hub"
- [ ] **Create project structure:**
  ```
  homelab-intelligence/
  ├── backend/
  │   ├── app/
  │   │   ├── plugins/          # NEW: Plugin system
  │   │   │   ├── __init__.py
  │   │   │   ├── base.py       # Base plugin interface
  │   │   │   ├── loader.py     # Plugin discovery
  │   │   │   └── hub_client.py # Client for external plugins
  │   │   ├── services/
  │   │   │   ├── plugin_manager.py  # NEW: Plugin lifecycle
  │   │   │   └── [existing services]
  │   │   └── routers/
  │   │       └── [existing routers]
  │   └── requirements.txt
  └── frontend/
  ```

#### 1.2 Database Schema Additions
- [ ] **Create migration script:** `backend/migrations/add_plugin_system.py`
- [ ] **Add plugin tables:**
  ```sql
  -- Plugin registry
  CREATE TABLE plugins (
      id VARCHAR(100) PRIMARY KEY,
      name VARCHAR(255) NOT NULL,
      version VARCHAR(50),
      category VARCHAR(50),
      description TEXT,
      author VARCHAR(255),
      enabled BOOLEAN DEFAULT FALSE,
      external BOOLEAN DEFAULT FALSE,  -- external vs built-in
      installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      last_health_check TIMESTAMP,
      health_status VARCHAR(50) DEFAULT 'unknown'
  );
  
  -- Plugin metrics (time-series data)
  CREATE TABLE plugin_metrics (
      id SERIAL PRIMARY KEY,
      plugin_id VARCHAR(100) REFERENCES plugins(id),
      timestamp TIMESTAMP NOT NULL,
      data JSONB NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  CREATE INDEX idx_plugin_metrics_plugin_ts ON plugin_metrics(plugin_id, timestamp DESC);
  
  -- Plugin configuration
  CREATE TABLE plugin_configs (
      id SERIAL PRIMARY KEY,
      plugin_id VARCHAR(100) REFERENCES plugins(id) UNIQUE,
      config JSONB NOT NULL,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  
  -- Plugin execution history
  CREATE TABLE plugin_executions (
      id SERIAL PRIMARY KEY,
      plugin_id VARCHAR(100) REFERENCES plugins(id),
      started_at TIMESTAMP NOT NULL,
      completed_at TIMESTAMP,
      status VARCHAR(50),  -- running, success, failed
      error_message TEXT,
      metrics_count INTEGER DEFAULT 0
  );
  CREATE INDEX idx_plugin_executions_plugin ON plugin_executions(plugin_id, started_at DESC);
  ```

- [ ] **Add TimescaleDB extension** (optional but recommended):
  ```sql
  CREATE EXTENSION IF NOT EXISTS timescaledb;
  SELECT create_hypertable('plugin_metrics', 'timestamp');
  ```

- [ ] **Run migration:** `python backend/migrations/add_plugin_system.py`

#### 1.3 Core Plugin Infrastructure
- [ ] **Create base plugin interface:** `backend/app/plugins/base.py`
  ```python
  from abc import ABC, abstractmethod
  from typing import Any, Dict, Optional
  from datetime import datetime
  
  class PluginBase(ABC):
      """Base class for all homelab-intelligence plugins."""
      
      def __init__(self, hub_client=None):
          self.hub = hub_client
          self.enabled = False
          self._last_execution = None
          self._execution_count = 0
      
      @abstractmethod
      def get_metadata(self) -> Dict[str, Any]:
          """Return plugin metadata."""
          pass
      
      @abstractmethod
      async def collect_data(self) -> Dict[str, Any]:
          """Collect data from the monitored system."""
          pass
      
      async def health_check(self) -> bool:
          """Check if plugin is healthy and can execute."""
          return True
      
      async def on_enable(self):
          """Called when plugin is enabled."""
          self.enabled = True
      
      async def on_disable(self):
          """Called when plugin is disabled."""
          self.enabled = False
      
      async def on_error(self, error: Exception):
          """Called when plugin encounters an error."""
          pass
  ```

- [ ] **Create plugin loader:** `backend/app/plugins/loader.py`
  ```python
  import importlib.metadata
  from typing import Dict, List, Optional
  from .base import PluginBase
  import logging
  
  logger = logging.getLogger(__name__)
  
  class PluginLoader:
      """Discover and load plugins from entry points."""
      
      def __init__(self):
          self.plugins: Dict[str, PluginBase] = {}
          self._entry_point_group = 'homelab_intelligence.plugins'
      
      def discover_plugins(self) -> List[str]:
          """Discover all installed plugins via entry points."""
          try:
              entry_points = importlib.metadata.entry_points()
              if hasattr(entry_points, 'select'):
                  # Python 3.10+
                  plugin_eps = entry_points.select(group=self._entry_point_group)
              else:
                  # Python 3.9
                  plugin_eps = entry_points.get(self._entry_point_group, [])
              
              return [ep.name for ep in plugin_eps]
          except Exception as e:
              logger.error(f"Error discovering plugins: {e}")
              return []
      
      def load_plugin(self, plugin_name: str, hub_client=None) -> Optional[PluginBase]:
          """Load a specific plugin by name."""
          try:
              entry_points = importlib.metadata.entry_points()
              if hasattr(entry_points, 'select'):
                  plugin_eps = entry_points.select(group=self._entry_point_group)
              else:
                  plugin_eps = entry_points.get(self._entry_point_group, [])
              
              for ep in plugin_eps:
                  if ep.name == plugin_name:
                      plugin_class = ep.load()
                      plugin_instance = plugin_class(hub_client)
                      self.plugins[plugin_name] = plugin_instance
                      logger.info(f"Loaded plugin: {plugin_name}")
                      return plugin_instance
              
              logger.warning(f"Plugin not found: {plugin_name}")
              return None
          except Exception as e:
              logger.error(f"Failed to load plugin {plugin_name}: {e}")
              return None
      
      def load_all_plugins(self, hub_client=None) -> Dict[str, PluginBase]:
          """Load all discovered plugins."""
          plugin_names = self.discover_plugins()
          for name in plugin_names:
              self.load_plugin(name, hub_client)
          return self.plugins
      
      def unload_plugin(self, plugin_name: str):
          """Unload a plugin."""
          if plugin_name in self.plugins:
              del self.plugins[plugin_name]
              logger.info(f"Unloaded plugin: {plugin_name}")
  ```

- [ ] **Create hub client for external plugins:** `backend/app/plugins/hub_client.py`
  ```python
  import aiohttp
  from typing import Dict, Any, Optional
  import logging
  
  logger = logging.getLogger(__name__)
  
  class HubClient:
      """Client for external plugins to communicate with the hub."""
      
      def __init__(self, hub_url: str, api_key: str):
          self.hub_url = hub_url.rstrip('/')
          self.api_key = api_key
          self.session: Optional[aiohttp.ClientSession] = None
      
      async def __aenter__(self):
          self.session = aiohttp.ClientSession(
              headers={"Authorization": f"Bearer {self.api_key}"}
          )
          return self
      
      async def __aexit__(self, exc_type, exc_val, exc_tb):
          if self.session:
              await self.session.close()
      
      async def send_metrics(
          self, 
          plugin_id: str, 
          timestamp: str, 
          data: Dict[str, Any]
      ) -> Dict[str, Any]:
          """Send metrics to the hub."""
          if not self.session:
              raise RuntimeError("HubClient not initialized. Use async context manager.")
          
          try:
              async with self.session.post(
                  f"{self.hub_url}/api/plugins/{plugin_id}/metrics",
                  json={
                      "timestamp": timestamp,
                      "data": data
                  }
              ) as response:
                  response.raise_for_status()
                  return await response.json()
          except Exception as e:
              logger.error(f"Failed to send metrics for {plugin_id}: {e}")
              raise
      
      async def get_config(self, plugin_id: str) -> Dict[str, Any]:
          """Get plugin configuration from hub."""
          if not self.session:
              raise RuntimeError("HubClient not initialized. Use async context manager.")
          
          try:
              async with self.session.get(
                  f"{self.hub_url}/api/plugins/{plugin_id}/config"
              ) as response:
                  response.raise_for_status()
                  return await response.json()
          except Exception as e:
              logger.error(f"Failed to get config for {plugin_id}: {e}")
              return {}
      
      async def update_health(self, plugin_id: str, healthy: bool, message: str = ""):
          """Update plugin health status."""
          if not self.session:
              return
          
          try:
              async with self.session.post(
                  f"{self.hub_url}/api/plugins/{plugin_id}/health",
                  json={"healthy": healthy, "message": message}
              ) as response:
                  response.raise_for_status()
          except Exception as e:
              logger.error(f"Failed to update health for {plugin_id}: {e}")
      
      async def register_plugin(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
          """Register plugin with the hub."""
          if not self.session:
              raise RuntimeError("HubClient not initialized. Use async context manager.")
          
          try:
              async with self.session.post(
                  f"{self.hub_url}/api/plugins/register",
                  json=metadata
              ) as response:
                  response.raise_for_status()
                  return await response.json()
          except Exception as e:
              logger.error(f"Failed to register plugin: {e}")
              raise
  ```

#### 1.4 Plugin Manager Service
- [ ] **Create plugin manager:** `backend/app/services/plugin_manager.py`
  ```python
  from apscheduler.schedulers.asyncio import AsyncIOScheduler
  from sqlalchemy.orm import Session
  from app.plugins.loader import PluginLoader
  from app.plugins.base import PluginBase
  from app.models import Plugin, PluginExecution
  from datetime import datetime
  import logging
  
  logger = logging.getLogger(__name__)
  
  class PluginManager:
      """Manage plugin lifecycle and scheduling."""
      
      def __init__(self, db: Session, scheduler: AsyncIOScheduler):
          self.db = db
          self.scheduler = scheduler
          self.loader = PluginLoader()
          self.active_plugins: dict[str, PluginBase] = {}
      
      async def initialize(self):
          """Initialize plugin manager and load enabled plugins."""
          logger.info("Initializing plugin manager...")
          
          # Load all available plugins via entry points
          self.loader.load_all_plugins()
          
          # Get enabled plugins from database
          enabled = self.db.query(Plugin).filter(
              Plugin.enabled == True
          ).all()
          
          # Schedule enabled plugins
          for plugin_record in enabled:
              if plugin_record.id in self.loader.plugins:
                  await self.enable_plugin(plugin_record.id)
          
          logger.info(f"Initialized {len(self.active_plugins)} plugins")
      
      async def enable_plugin(self, plugin_id: str):
          """Enable and schedule a plugin."""
          plugin = self.loader.plugins.get(plugin_id)
          if not plugin:
              logger.error(f"Plugin not found: {plugin_id}")
              return False
          
          try:
              # Call plugin's enable hook
              await plugin.on_enable()
              
              # Get metadata
              metadata = plugin.get_metadata()
              interval = metadata.get('interval', 300)  # default 5 min
              
              # Schedule collection task
              self.scheduler.add_job(
                  self._execute_plugin,
                  'interval',
                  seconds=interval,
                  id=f"plugin_{plugin_id}",
                  args=[plugin_id],
                  name=f"Plugin: {metadata.get('name', plugin_id)}",
                  replace_existing=True
              )
              
              # Update database
              db_plugin = self.db.query(Plugin).filter(
                  Plugin.id == plugin_id
              ).first()
              if db_plugin:
                  db_plugin.enabled = True
                  self.db.commit()
              
              self.active_plugins[plugin_id] = plugin
              logger.info(f"Enabled plugin: {plugin_id} (interval: {interval}s)")
              return True
              
          except Exception as e:
              logger.error(f"Failed to enable plugin {plugin_id}: {e}")
              return False
      
      async def disable_plugin(self, plugin_id: str):
          """Disable and unschedule a plugin."""
          plugin = self.active_plugins.get(plugin_id)
          if not plugin:
              logger.warning(f"Plugin not active: {plugin_id}")
              return False
          
          try:
              # Remove scheduled job
              try:
                  self.scheduler.remove_job(f"plugin_{plugin_id}")
              except Exception:
                  pass  # Job might not exist
              
              # Call plugin's disable hook
              await plugin.on_disable()
              
              # Update database
              db_plugin = self.db.query(Plugin).filter(
                  Plugin.id == plugin_id
              ).first()
              if db_plugin:
                  db_plugin.enabled = False
                  self.db.commit()
              
              # Remove from active plugins
              del self.active_plugins[plugin_id]
              
              logger.info(f"Disabled plugin: {plugin_id}")
              return True
              
          except Exception as e:
              logger.error(f"Failed to disable plugin {plugin_id}: {e}")
              return False
      
      async def _execute_plugin(self, plugin_id: str):
          """Execute a plugin's data collection."""
          plugin = self.active_plugins.get(plugin_id)
          if not plugin:
              return
          
          # Create execution record
          execution = PluginExecution(
              plugin_id=plugin_id,
              started_at=datetime.utcnow(),
              status='running'
          )
          self.db.add(execution)
          self.db.commit()
          
          try:
              # Health check
              healthy = await plugin.health_check()
              if not healthy:
                  raise Exception("Plugin health check failed")
              
              # Collect data
              data = await plugin.collect_data()
              
              # Store metrics (handled by plugin itself or here)
              # For now, plugins report via hub_client
              
              # Update execution record
              execution.completed_at = datetime.utcnow()
              execution.status = 'success'
              execution.metrics_count = len(data) if isinstance(data, dict) else 1
              self.db.commit()
              
              logger.debug(f"Plugin {plugin_id} executed successfully")
              
          except Exception as e:
              logger.error(f"Plugin {plugin_id} execution failed: {e}")
              
              # Update execution record
              execution.completed_at = datetime.utcnow()
              execution.status = 'failed'
              execution.error_message = str(e)
              self.db.commit()
              
              # Call plugin's error hook
              await plugin.on_error(e)
      
      async def check_plugin_health(self, plugin_id: str) -> bool:
          """Check if a plugin is healthy."""
          plugin = self.loader.plugins.get(plugin_id)
          if not plugin:
              return False
          
          try:
              return await plugin.health_check()
          except Exception as e:
              logger.error(f"Health check failed for {plugin_id}: {e}")
              return False
  ```

#### 1.5 Update Main Application
- [ ] **Update `backend/app/main.py`** to initialize plugin manager:
  ```python
  # Add to imports
  from app.services.plugin_manager import PluginManager
  from app.plugins.loader import PluginLoader
  
  # Add after scheduler initialization
  plugin_manager = None
  
  @app.on_event("startup")
  async def startup_event():
      # ... existing startup code ...
      
      # Initialize plugin manager
      global plugin_manager
      db = next(get_db())
      plugin_manager = PluginManager(db, scheduler)
      await plugin_manager.initialize()
      
      logger.info("Plugin manager initialized")
  ```

- [ ] **Add to requirements.txt:**
  ```
  # Plugin system dependencies
  importlib-metadata>=4.0.0  # For plugin discovery
  ```

#### 1.6 API Endpoints for Plugin Management
- [ ] **Extend `backend/app/routers/plugins.py`** with new endpoints:
  ```python
  # Add these new endpoints
  
  @router.post("/plugins/register")
  async def register_external_plugin(
      metadata: dict,
      db: Session = Depends(get_db)
  ):
      """Register an external plugin with the hub."""
      plugin = Plugin(
          id=metadata['id'],
          name=metadata['name'],
          version=metadata.get('version'),
          category=metadata.get('category'),
          description=metadata.get('description'),
          author=metadata.get('author'),
          external=True,
          enabled=False
      )
      db.add(plugin)
      db.commit()
      return {"status": "registered", "plugin_id": metadata['id']}
  
  @router.post("/plugins/{plugin_id}/metrics")
  async def receive_plugin_metrics(
      plugin_id: str,
      payload: dict,
      db: Session = Depends(get_db)
  ):
      """Receive metrics from external plugins."""
      from app.models import PluginMetric
      
      metric = PluginMetric(
          plugin_id=plugin_id,
          timestamp=payload['timestamp'],
          data=payload['data']
      )
      db.add(metric)
      db.commit()
      return {"status": "received"}
  
  @router.get("/plugins/{plugin_id}/config")
  async def get_plugin_config(
      plugin_id: str,
      db: Session = Depends(get_db)
  ):
      """Get configuration for a plugin."""
      from app.models import PluginConfig
      
      config = db.query(PluginConfig).filter(
          PluginConfig.plugin_id == plugin_id
      ).first()
      return config.config if config else {}
  
  @router.post("/plugins/{plugin_id}/health")
  async def update_plugin_health(
      plugin_id: str,
      health: dict,
      db: Session = Depends(get_db)
  ):
      """Update plugin health status."""
      plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
      if plugin:
          plugin.health_status = 'healthy' if health.get('healthy') else 'unhealthy'
          plugin.last_health_check = datetime.utcnow()
          db.commit()
      return {"status": "updated"}
  
  @router.post("/plugins/{plugin_id}/enable")
  async def enable_plugin_endpoint(
      plugin_id: str,
      db: Session = Depends(get_db)
  ):
      """Enable a plugin."""
      from app.main import plugin_manager
      success = await plugin_manager.enable_plugin(plugin_id)
      return {"status": "enabled" if success else "failed"}
  
  @router.post("/plugins/{plugin_id}/disable")
  async def disable_plugin_endpoint(
      plugin_id: str,
      db: Session = Depends(get_db)
  ):
      """Disable a plugin."""
      from app.main import plugin_manager
      success = await plugin_manager.disable_plugin(plugin_id)
      return {"status": "disabled" if success else "failed"}
  ```

---

### Phase 2: KC-Booth Integration (Week 2-3)
**Goal:** Integrate SSH key and certificate management into hub core

#### 2.1 Analysis and Planning
- [ ] **Review kc-booth codebase** to understand all features
- [ ] **Map kc-booth models to hub models**
- [ ] **Identify shared vs. unique functionality**

#### 2.2 Database Schema Migration
- [ ] **Create migration:** `backend/migrations/add_kc_booth_features.py`
- [ ] **Add tables:**
  ```sql
  -- SSH Keys
  CREATE TABLE ssh_keys (
      id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL,
      key_type VARCHAR(50) NOT NULL,  -- rsa, ed25519, etc.
      public_key TEXT NOT NULL,
      private_key_encrypted TEXT NOT NULL,
      fingerprint VARCHAR(255),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      created_by INTEGER REFERENCES users(id)
  );
  
  -- Certificates
  CREATE TABLE certificates (
      id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL,
      certificate_type VARCHAR(50),  -- x509, ssh-cert, etc.
      certificate_data TEXT NOT NULL,
      private_key_encrypted TEXT,
      issuer VARCHAR(255),
      subject VARCHAR(255),
      valid_from TIMESTAMP,
      valid_until TIMESTAMP,
      auto_rotate BOOLEAN DEFAULT FALSE,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  
  -- Server credentials (link keys/certs to servers)
  CREATE TABLE server_credentials (
      id SERIAL PRIMARY KEY,
      server_id INTEGER REFERENCES server_profiles(id),
      ssh_key_id INTEGER REFERENCES ssh_keys(id),
      certificate_id INTEGER REFERENCES certificates(id),
      credential_type VARCHAR(50),  -- ssh_key, certificate, password
      username VARCHAR(255),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  
  -- Step CA configuration
  CREATE TABLE step_ca_config (
      id SERIAL PRIMARY KEY,
      ca_url VARCHAR(255) NOT NULL,
      provisioner_name VARCHAR(255),
      provisioner_password_encrypted TEXT,
      root_certificate TEXT,
      enabled BOOLEAN DEFAULT FALSE,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```

- [ ] **Run migration**

#### 2.3 Copy KC-Booth Services
- [ ] **Copy and adapt services:**
  ```
  kc-booth/src/step_ca.py       → backend/app/services/certificate_manager.py
  kc-booth/src/distribution.py  → backend/app/services/credential_distribution.py
  kc-booth/src/crud.py           → backend/app/services/ssh_key_manager.py
  kc-booth/src/scheduler.py     → Merge with existing scheduler
  ```

- [ ] **Update imports and dependencies** in copied files
- [ ] **Remove kc-booth-specific code** (its database models, etc.)
- [ ] **Integrate with hub's encryption service**

#### 2.4 API Endpoints
- [ ] **Create:** `backend/app/routers/credentials.py`
  ```python
  from fastapi import APIRouter, Depends, HTTPException
  from sqlalchemy.orm import Session
  from app.database import get_db
  from app.services.ssh_key_manager import SSHKeyManager
  from app.services.certificate_manager import CertificateManager
  
  router = APIRouter(prefix="/api/credentials", tags=["credentials"])
  
  # SSH Keys
  @router.post("/ssh-keys")
  async def create_ssh_key(...):
      """Generate and store a new SSH key."""
      pass
  
  @router.get("/ssh-keys")
  async def list_ssh_keys(...):
      """List all SSH keys."""
      pass
  
  @router.get("/ssh-keys/{key_id}")
  async def get_ssh_key(...):
      """Get SSH key details (without private key)."""
      pass
  
  @router.delete("/ssh-keys/{key_id}")
  async def delete_ssh_key(...):
      """Delete an SSH key."""
      pass
  
  @router.post("/ssh-keys/{key_id}/distribute")
  async def distribute_ssh_key(...):
      """Distribute SSH key to a server."""
      pass
  
  # Certificates
  @router.post("/certificates")
  async def create_certificate(...):
      """Request a new certificate from step-ca."""
      pass
  
  @router.get("/certificates")
  async def list_certificates(...):
      """List all certificates."""
      pass
  
  @router.post("/certificates/{cert_id}/rotate")
  async def rotate_certificate(...):
      """Manually rotate a certificate."""
      pass
  
  # Step CA Configuration
  @router.post("/step-ca/configure")
  async def configure_step_ca(...):
      """Configure step-ca integration."""
      pass
  
  @router.get("/step-ca/status")
  async def step_ca_status(...):
      """Check step-ca connection status."""
      pass
  ```

- [ ] **Register router in `main.py`:**
  ```python
  from app.routers import credentials
  app.include_router(credentials.router)
  ```

#### 2.5 Frontend Integration
- [ ] **Create credential management pages:**
  ```
  frontend/src/pages/Credentials/
  ├── SSHKeys.tsx           # List and manage SSH keys
  ├── Certificates.tsx      # List and manage certificates
  ├── StepCAConfig.tsx      # Configure step-ca
  └── DistributeKey.tsx     # Distribute keys to servers
  ```

- [ ] **Add to navigation menu**
- [ ] **Create API client functions** in `frontend/src/api/credentials.ts`

#### 2.6 Testing
- [ ] **Unit tests** for new services
- [ ] **Integration tests** for certificate rotation
- [ ] **Test step-ca connectivity** (if available)
- [ ] **Test SSH key distribution** to servers

---

### Phase 3: Plugin SDK Package (Week 3-4)
**Goal:** Create an installable SDK for plugin developers

#### 3.1 Create SDK Package
- [ ] **Create new directory:** `hi-hub/plugin-sdk/`
  ```
  plugin-sdk/
  ├── pyproject.toml
  ├── README.md
  ├── LICENSE
  ├── homelab_intelligence_sdk/
  │   ├── __init__.py
  │   ├── plugin.py         # Base plugin class (copy from hub)
  │   ├── client.py         # Hub client (copy from hub)
  │   ├── utils.py          # Helper utilities
  │   └── types.py          # Type definitions
  ├── examples/
  │   └── example_plugin.py
  └── tests/
      └── test_plugin.py
  ```

#### 3.2 SDK pyproject.toml
- [ ] **Create:** `plugin-sdk/pyproject.toml`
  ```toml
  [project]
  name = "homelab-intelligence-sdk"
  version = "0.1.0"
  description = "SDK for building Homelab Intelligence plugins"
  authors = [{name = "Your Name", email = "your.email@example.com"}]
  requires-python = ">=3.10"
  dependencies = [
      "aiohttp>=3.9.0",
      "pydantic>=2.0.0",
  ]
  
  [project.optional-dependencies]
  dev = [
      "pytest>=7.0.0",
      "pytest-asyncio>=0.21.0",
      "black>=23.0.0",
  ]
  
  [build-system]
  requires = ["hatchling"]
  build-backend = "hatchling.build"
  ```

#### 3.3 Documentation
- [ ] **Create comprehensive README** with:
  - Installation instructions
  - Quick start guide
  - Plugin development tutorial
  - API reference
  - Example plugins

- [ ] **Create plugin template** in `examples/`

#### 3.4 Publish SDK
- [ ] **Test SDK locally:** `uv pip install -e plugin-sdk/`
- [ ] **Create git tag:** `git tag sdk-v0.1.0`
- [ ] **(Optional) Publish to PyPI** for easier distribution

---

### Phase 4: Built-in Plugin Migration (Week 4-5)
**Goal:** Convert existing hardcoded plugins to the new system

#### 4.1 Analyze Current Plugins
- [ ] **Review:** `backend/app/services/plugin_registry.py`
- [ ] **List all hardcoded plugins:**
  - lm-sensors
  - ipmitool
  - smartctl
  - zpool-status
  - mdadm
  - iostat
  - lsblk
  - nvidia-smi
  - docker-stats
  - lxc-list
  - virsh
  - ss
  - fail2ban
  - iperf3
  - systemctl
  - journalctl
  - upsc

#### 4.2 Create Built-in Plugin Package
- [ ] **Create:** `backend/app/plugins/builtin/`
  ```
  builtin/
  ├── __init__.py
  ├── thermal/
  │   ├── lm_sensors.py
  │   └── ipmitool.py
  ├── storage/
  │   ├── smartctl.py
  │   ├── zpool.py
  │   ├── mdadm.py
  │   └── lsblk.py
  ├── containers/
  │   ├── docker_stats.py
  │   └── lxc.py
  └── [other categories]
  ```

#### 4.3 Convert One Plugin (Template)
- [ ] **Convert `lm-sensors` as template:**
  ```python
  # backend/app/plugins/builtin/thermal/lm_sensors.py
  
  from app.plugins.base import PluginBase
  from typing import Dict, Any
  import json
  
  class LMSensorsPlugin(PluginBase):
      def get_metadata(self) -> Dict[str, Any]:
          return {
              "id": "lm-sensors",
              "name": "LM Sensors",
              "version": "1.0.0",
              "category": "thermal",
              "description": "Monitor system temperatures via lm-sensors",
              "author": "Homelab Intelligence",
              "requires_sudo": False,
              "interval": 60,
              "check_cmd": "sensors --version",
          }
      
      async def collect_data(self) -> Dict[str, Any]:
          # Use hub's SSH service to execute command
          # Parse output
          # Return structured data
          pass
      
      async def health_check(self) -> bool:
          # Check if lm-sensors is available
          pass
  ```

- [ ] **Register in entry points** (in hub's pyproject.toml or setup.py)
- [ ] **Test the converted plugin**

#### 4.4 Convert Remaining Plugins
- [ ] **Convert all 17 built-in plugins** following the template
- [ ] **Update plugin registry** to use new system
- [ ] **Remove old `plugin_registry.py`**

#### 4.5 Testing
- [ ] **Test each plugin individually**
- [ ] **Test plugin enable/disable**
- [ ] **Test data collection and storage**
- [ ] **Verify dashboard still displays plugin data**

---

### Phase 5: Redis Integration (Week 5-6)
**Goal:** Add message queue for better plugin communication

#### 5.1 Add Redis to Stack
- [ ] **Update `docker-compose.yml`:**
  ```yaml
  services:
    redis:
      image: redis:7-alpine
      container_name: hi-redis
      restart: unless-stopped
      ports:
        - "6379:6379"
      volumes:
        - redis_data:/data
      networks:
        - hi-net
      healthcheck:
        test: ["CMD", "redis-cli", "ping"]
        interval: 10s
        timeout: 5s
        retries: 5
  
  volumes:
    redis_data:
  ```

- [ ] **Add to requirements.txt:**
  ```
  redis>=5.0.0
  ```

#### 5.2 Redis Service
- [ ] **Create:** `backend/app/services/redis_service.py`
  ```python
  import redis.asyncio as redis
  from typing import Dict, Any
  import json
  import logging
  
  logger = logging.getLogger(__name__)
  
  class RedisService:
      def __init__(self, redis_url: str = "redis://localhost:6379"):
          self.redis_url = redis_url
          self.client = None
      
      async def connect(self):
          """Connect to Redis."""
          self.client = await redis.from_url(self.redis_url)
          logger.info("Connected to Redis")
      
      async def disconnect(self):
          """Disconnect from Redis."""
          if self.client:
              await self.client.close()
      
      async def publish_plugin_metric(
          self,
          plugin_id: str,
          data: Dict[str, Any]
      ):
          """Publish plugin metric to Redis stream."""
          stream_key = f"plugin:{plugin_id}:metrics"
          await self.client.xadd(
              stream_key,
              {"data": json.dumps(data)},
              maxlen=1000  # Keep last 1000 entries
          )
      
      async def consume_plugin_metrics(self, plugin_id: str):
          """Consume plugin metrics from Redis stream."""
          stream_key = f"plugin:{plugin_id}:metrics"
          # Read from stream
          messages = await self.client.xread({stream_key: '0'}, count=100)
          return messages
      
      async def set_plugin_state(self, plugin_id: str, state: Dict[str, Any]):
          """Store plugin state."""
          await self.client.set(
              f"plugin:{plugin_id}:state",
              json.dumps(state),
              ex=3600  # Expire after 1 hour
          )
      
      async def get_plugin_state(self, plugin_id: str) -> Dict[str, Any]:
          """Get plugin state."""
          data = await self.client.get(f"plugin:{plugin_id}:state")
          return json.loads(data) if data else {}
  ```

- [ ] **Initialize in `main.py`**
- [ ] **Update plugins to publish to Redis**

#### 5.3 Metrics Consumer
- [ ] **Create background task** to consume metrics from Redis
- [ ] **Batch insert metrics** into PostgreSQL
- [ ] **Implement buffering** for high-throughput scenarios

---

### Phase 6: Monitoring & Observability (Week 6)
**Goal:** Add comprehensive monitoring for the plugin system

#### 6.1 Logging Improvements
- [ ] **Structured logging** (JSON format)
- [ ] **Correlation IDs** for tracing plugin executions
- [ ] **Log levels** per plugin

#### 6.2 Plugin Health Dashboard
- [ ] **Frontend page:** `frontend/src/pages/PluginHealth.tsx`
- [ ] **Show:**
  - Plugin status (enabled/disabled/unhealthy)
  - Last execution time
  - Success/failure rate
  - Error messages
  - Execution duration

#### 6.3 Metrics & Alerting
- [ ] **Track plugin metrics:**
  - Execution count
  - Failure rate
  - Average duration
  - Data volume

- [ ] **Alerts for:**
  - Plugin down > 15 minutes
  - High failure rate (>10%)
  - Execution timeout

#### 6.4 Performance Monitoring
- [ ] **Database query optimization**
- [ ] **Add indexes** for common queries
- [ ] **Monitor connection pool usage**

---

### Phase 7: Documentation (Week 7)
**Goal:** Comprehensive documentation for the new system

#### 7.1 Hub Documentation
- [ ] **Update main README**
- [ ] **Architecture documentation**
- [ ] **API documentation** (update Swagger/OpenAPI)
- [ ] **Configuration guide**

#### 7.2 Plugin Development Guide
- [ ] **Getting started tutorial**
- [ ] **Plugin development best practices**
- [ ] **Testing guide**
- [ ] **Deployment guide**

#### 7.3 Migration Guides
- [ ] **Guide for converting bd-store to plugins**
- [ ] **Guide for converting uptainer to plugin**
- [ ] **Breaking changes and upgrade path**

---

## Phase 8: Ready for External Plugins (Week 8+)

At this point, the hub is ready to accept external plugins from bd-store and uptainer!

### Checklist for External Plugin Development:
- [ ] Hub has dynamic plugin loading
- [ ] SDK is published and documented
- [ ] API endpoints for plugin registration
- [ ] Metrics ingestion pipeline
- [ ] Plugin health monitoring
- [ ] Configuration management
- [ ] Credential management (from kc-booth)

---

## Testing Strategy

### Unit Tests
- [ ] Plugin base classes
- [ ] Plugin loader
- [ ] Hub client
- [ ] Plugin manager
- [ ] All services

### Integration Tests
- [ ] Plugin registration
- [ ] Plugin enable/disable
- [ ] Metrics collection and storage
- [ ] Health checks
- [ ] Redis integration

### End-to-End Tests
- [ ] Full plugin lifecycle
- [ ] Multiple plugins running concurrently
- [ ] Plugin failure and recovery
- [ ] Dashboard displays plugin data

---

## Rollback Plan

If something goes wrong:
1. **Keep feature branch** separate from main
2. **Tag current production** state before merging
3. **Database migrations** are reversible
4. **Docker volumes** are backed up before major changes

---

## Success Metrics

### Week 2:
- [ ] Plugin infrastructure in place
- [ ] Can load and run 1 test plugin
- [ ] Database schema updated

### Week 4:
- [ ] KC-Booth integrated
- [ ] SDK published
- [ ] 5+ built-in plugins converted

### Week 6:
- [ ] All built-in plugins converted
- [ ] Redis integration complete
- [ ] Health monitoring dashboard

### Week 8:
- [ ] System ready for external plugins
- [ ] Documentation complete
- [ ] Performance tested with 30 plugins

---

## Next Steps

1. **Make architectural decisions** (Phase 0)
2. **Create feature branch** in homelab-intelligence
3. **Start Phase 1** implementation
4. **Set up weekly check-ins** to track progress

Once you've finished bd-store and uptainer, we'll create specific conversion guides for turning them into plugins!
