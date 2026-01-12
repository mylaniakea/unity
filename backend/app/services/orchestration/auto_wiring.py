"""
Auto-Wiring Engine for Intelligent Configuration Generation

Automatically generates configurations, secrets, networking, and storage
based on blueprint requirements and cluster context.
"""

import secrets
import string
import logging
from typing import Dict, Any, List, Optional, Set
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class AutoWiringError(Exception):
    """Base exception for auto-wiring errors"""
    pass


class AutoWiringEngine:
    """
    Automatically wires up application configurations and dependencies.

    Features:
    - Smart variable inference
    - Secret generation
    - ConfigMap creation
    - Service networking setup
    - Storage provisioning
    - Dependency wiring
    """

    def __init__(self):
        self.generated_secrets = {}
        self.created_services = {}
        self.storage_allocations = {}

    def infer_variables(
        self,
        blueprint: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fill in variables automatically based on blueprint requirements and context.

        Args:
            blueprint: Blueprint definition with requirements
            context: Execution context with cluster info, existing resources, etc.

        Returns:
            Dict of inferred variables ready for template substitution
        """
        logger.info("Inferring variables from blueprint and context")

        variables = {}
        app_name = blueprint.get('metadata', {}).get('name', 'app')
        variables['app_name'] = app_name

        # Get requirements
        requirements = blueprint.get('requirements', {})

        # Infer namespace
        variables['namespace'] = self._infer_namespace(app_name, context)

        # Infer database URLs
        if requirements.get('database'):
            db_config = self._infer_database_config(
                app_name,
                requirements['database'],
                context
            )
            variables.update(db_config)

        # Infer cache URLs (Redis)
        if requirements.get('cache'):
            cache_config = self._infer_cache_config(
                app_name,
                requirements['cache'],
                context
            )
            variables.update(cache_config)

        # Infer message queue URLs
        if requirements.get('message_queue'):
            mq_config = self._infer_message_queue_config(
                app_name,
                requirements['message_queue'],
                context
            )
            variables.update(mq_config)

        # Infer domain/ingress
        if requirements.get('ingress', {}).get('enabled'):
            domain_config = self._infer_domain_config(
                app_name,
                requirements['ingress'],
                context
            )
            variables.update(domain_config)

        # Infer storage
        if requirements.get('storage'):
            storage_config = self._infer_storage_config(
                app_name,
                requirements['storage'],
                context
            )
            variables.update(storage_config)

        # Infer compute resources
        if requirements.get('resources'):
            resource_config = self._infer_resource_config(
                requirements['resources'],
                context
            )
            variables.update(resource_config)

        # Infer image registry
        variables['image_registry'] = context.get('image_registry', 'ghcr.io')

        # Infer image name if not provided
        if 'image' not in variables:
            registry = variables['image_registry']
            org = context.get('organization', 'unity')
            variables['image'] = f"{registry}/{org}/{app_name}:latest"

        # Infer port
        if 'port' not in variables:
            variables['port'] = requirements.get('port', 8080)

        logger.info(f"Inferred {len(variables)} variables")
        return variables

    def generate_secrets(
        self,
        blueprint: Dict[str, Any],
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create Kubernetes secrets or Docker env files for sensitive data.

        Args:
            blueprint: Blueprint definition
            variables: Variables including connection strings, etc.

        Returns:
            Dict containing:
            - kubernetes: K8s Secret manifests
            - docker: .env file contents
            - secret_refs: References to use in deployments
        """
        logger.info("Generating secrets")

        app_name = variables.get('app_name', 'app')
        namespace = variables.get('namespace', 'default')
        requirements = blueprint.get('requirements', {})

        secrets_data = {}
        secret_refs = {}

        # Database credentials
        if requirements.get('database'):
            db_password = self._generate_password()
            secrets_data['DATABASE_PASSWORD'] = db_password
            secrets_data['DATABASE_URL'] = self._build_database_url(
                variables.get('database_type', 'postgresql'),
                variables.get('database_user', app_name),
                db_password,
                variables.get('database_host', f'{app_name}-postgres'),
                variables.get('database_port', 5432),
                variables.get('database_name', app_name)
            )
            secret_refs['database_password'] = {
                'secret_name': f'{app_name}-secrets',
                'key': 'DATABASE_PASSWORD'
            }

        # Redis password
        if requirements.get('cache', {}).get('type') == 'redis':
            redis_password = self._generate_password()
            secrets_data['REDIS_PASSWORD'] = redis_password
            secrets_data['REDIS_URL'] = self._build_redis_url(
                variables.get('redis_host', f'{app_name}-redis'),
                variables.get('redis_port', 6379),
                redis_password
            )
            secret_refs['redis_password'] = {
                'secret_name': f'{app_name}-secrets',
                'key': 'REDIS_PASSWORD'
            }

        # JWT secret
        if requirements.get('authentication'):
            jwt_secret = self._generate_secret_key(64)
            secrets_data['JWT_SECRET_KEY'] = jwt_secret
            secret_refs['jwt_secret'] = {
                'secret_name': f'{app_name}-secrets',
                'key': 'JWT_SECRET_KEY'
            }

        # Encryption key
        if requirements.get('encryption'):
            encryption_key = self._generate_fernet_key()
            secrets_data['ENCRYPTION_KEY'] = encryption_key
            secret_refs['encryption_key'] = {
                'secret_name': f'{app_name}-secrets',
                'key': 'ENCRYPTION_KEY'
            }

        # API keys for external services
        if requirements.get('external_apis'):
            for api in requirements['external_apis']:
                key_name = f"{api.upper()}_API_KEY"
                # Placeholder - should be provided by user or context
                secrets_data[key_name] = 'REPLACE_ME'
                secret_refs[f'{api}_api_key'] = {
                    'secret_name': f'{app_name}-secrets',
                    'key': key_name
                }

        # Generate Kubernetes Secret manifest
        k8s_secret = {
            'apiVersion': 'v1',
            'kind': 'Secret',
            'metadata': {
                'name': f'{app_name}-secrets',
                'namespace': namespace,
                'labels': {
                    'app': app_name,
                    'managed-by': 'unity'
                }
            },
            'type': 'Opaque',
            'stringData': secrets_data
        }

        # Generate Docker .env file content
        docker_env = '\n'.join([f'{k}={v}' for k, v in secrets_data.items()])

        self.generated_secrets[app_name] = secrets_data

        return {
            'kubernetes': [k8s_secret],
            'docker': docker_env,
            'secret_refs': secret_refs,
            'secret_data': secrets_data
        }

    def generate_configmaps(
        self,
        blueprint: Dict[str, Any],
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create ConfigMaps for non-sensitive configuration.

        Args:
            blueprint: Blueprint definition
            variables: Non-sensitive variables

        Returns:
            Dict with ConfigMap manifests and references
        """
        logger.info("Generating ConfigMaps")

        app_name = variables.get('app_name', 'app')
        namespace = variables.get('namespace', 'default')
        requirements = blueprint.get('requirements', {})

        config_data = {}

        # Application settings
        config_data['APP_NAME'] = app_name
        config_data['ENVIRONMENT'] = variables.get('environment', 'production')
        config_data['PORT'] = str(variables.get('port', 8080))
        config_data['LOG_LEVEL'] = variables.get('log_level', 'info')

        # Database connection (non-sensitive parts)
        if requirements.get('database'):
            config_data['DATABASE_HOST'] = variables.get('database_host', f'{app_name}-postgres')
            config_data['DATABASE_PORT'] = str(variables.get('database_port', 5432))
            config_data['DATABASE_NAME'] = variables.get('database_name', app_name)
            config_data['DATABASE_USER'] = variables.get('database_user', app_name)

        # Redis connection (non-sensitive parts)
        if requirements.get('cache'):
            config_data['REDIS_HOST'] = variables.get('redis_host', f'{app_name}-redis')
            config_data['REDIS_PORT'] = str(variables.get('redis_port', 6379))

        # Feature flags
        if requirements.get('features'):
            for feature, enabled in requirements['features'].items():
                config_data[f'FEATURE_{feature.upper()}'] = str(enabled)

        # Kubernetes ConfigMap
        k8s_configmap = {
            'apiVersion': 'v1',
            'kind': 'ConfigMap',
            'metadata': {
                'name': f'{app_name}-config',
                'namespace': namespace,
                'labels': {
                    'app': app_name,
                    'managed-by': 'unity'
                }
            },
            'data': config_data
        }

        return {
            'kubernetes': [k8s_configmap],
            'config_data': config_data
        }

    def setup_networking(
        self,
        blueprint: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create services and ingress rules for network access.

        Args:
            blueprint: Blueprint definition
            context: Cluster context

        Returns:
            Dict with Service and Ingress manifests
        """
        logger.info("Setting up networking")

        app_name = blueprint.get('metadata', {}).get('name', 'app')
        namespace = context.get('namespace', 'default')
        requirements = blueprint.get('requirements', {})
        port = requirements.get('port', 8080)

        manifests = []

        # Create Service for internal communication
        service = {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'name': app_name,
                'namespace': namespace,
                'labels': {
                    'app': app_name,
                    'managed-by': 'unity'
                }
            },
            'spec': {
                'selector': {'app': app_name},
                'ports': [{
                    'name': 'http',
                    'port': port,
                    'targetPort': port,
                    'protocol': 'TCP'
                }],
                'type': 'ClusterIP'
            }
        }

        # Check if external access is needed
        ingress_config = requirements.get('ingress', {})
        if ingress_config.get('enabled'):
            service['spec']['type'] = ingress_config.get('service_type', 'ClusterIP')

            # Create Ingress for external access
            domain = context.get('domain', f'{app_name}.local')
            path = ingress_config.get('path', '/')

            ingress = {
                'apiVersion': 'networking.k8s.io/v1',
                'kind': 'Ingress',
                'metadata': {
                    'name': app_name,
                    'namespace': namespace,
                    'labels': {
                        'app': app_name,
                        'managed-by': 'unity'
                    },
                    'annotations': {
                        'cert-manager.io/cluster-issuer': 'letsencrypt-prod',
                        'traefik.ingress.kubernetes.io/router.entrypoints': 'websecure'
                    }
                },
                'spec': {
                    'ingressClassName': 'traefik',
                    'tls': [{
                        'hosts': [domain],
                        'secretName': f'{app_name}-tls'
                    }],
                    'rules': [{
                        'host': domain,
                        'http': {
                            'paths': [{
                                'path': path,
                                'pathType': 'Prefix',
                                'backend': {
                                    'service': {
                                        'name': app_name,
                                        'port': {'number': port}
                                    }
                                }
                            }]
                        }
                    }]
                }
            }
            manifests.append(ingress)

        manifests.insert(0, service)

        self.created_services[app_name] = {
            'name': app_name,
            'namespace': namespace,
            'port': port,
            'type': service['spec']['type']
        }

        return {
            'manifests': manifests,
            'services': self.created_services
        }

    def provision_storage(
        self,
        blueprint: Dict[str, Any],
        storage_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create PersistentVolumeClaims for storage needs.

        Args:
            blueprint: Blueprint definition
            storage_requirements: Storage requirements from blueprint

        Returns:
            Dict with PVC manifests
        """
        logger.info("Provisioning storage")

        app_name = blueprint.get('metadata', {}).get('name', 'app')
        namespace = storage_requirements.get('namespace', 'default')

        pvcs = []

        for volume in storage_requirements.get('volumes', []):
            volume_name = volume.get('name', 'data')
            size = volume.get('size', '10Gi')
            storage_class = volume.get('storage_class', 'local-path')
            access_mode = volume.get('access_mode', 'ReadWriteOnce')

            pvc = {
                'apiVersion': 'v1',
                'kind': 'PersistentVolumeClaim',
                'metadata': {
                    'name': f'{app_name}-{volume_name}',
                    'namespace': namespace,
                    'labels': {
                        'app': app_name,
                        'managed-by': 'unity'
                    }
                },
                'spec': {
                    'accessModes': [access_mode],
                    'storageClassName': storage_class,
                    'resources': {
                        'requests': {
                            'storage': size
                        }
                    }
                }
            }

            pvcs.append(pvc)

            self.storage_allocations[f'{app_name}-{volume_name}'] = {
                'size': size,
                'storage_class': storage_class,
                'access_mode': access_mode
            }

        return {
            'manifests': pvcs,
            'allocations': self.storage_allocations
        }

    def wire_dependencies(
        self,
        app_name: str,
        dependencies: List[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Connect services by setting up service discovery and connection strings.

        Args:
            app_name: Name of the app requiring dependencies
            dependencies: List of dependency names (e.g., ["postgres", "redis"])
            context: Cluster context with existing resources

        Returns:
            Dict with:
            - connection_strings: Dict of service -> connection URL
            - required_services: List of services that need to be created
            - existing_services: List of services already available
        """
        logger.info(f"Wiring dependencies for {app_name}: {dependencies}")

        connection_strings = {}
        required_services = []
        existing_services = []

        namespace = context.get('namespace', 'default')
        existing_resources = context.get('existing_resources', {})

        for dep in dependencies:
            dep_lower = dep.lower()
            service_name = f'{app_name}-{dep_lower}'

            # Check if service already exists
            if self._service_exists(dep_lower, existing_resources):
                existing_services.append(dep_lower)
                # Use existing service
                service_name = self._get_existing_service_name(dep_lower, existing_resources)
            else:
                required_services.append(dep_lower)

            # Generate connection string
            if dep_lower in ['postgres', 'postgresql', 'mysql', 'mariadb']:
                connection_strings[dep_lower] = self._build_database_url(
                    dep_lower,
                    app_name,
                    '${DATABASE_PASSWORD}',  # Placeholder for secret
                    service_name,
                    5432 if 'postgres' in dep_lower else 3306,
                    app_name
                )
            elif dep_lower == 'redis':
                connection_strings[dep_lower] = self._build_redis_url(
                    service_name,
                    6379,
                    '${REDIS_PASSWORD}'  # Placeholder for secret
                )
            elif dep_lower in ['rabbitmq', 'kafka']:
                connection_strings[dep_lower] = f'{dep_lower}://{service_name}:5672'
            else:
                # Generic service URL
                connection_strings[dep_lower] = f'http://{service_name}:8080'

        return {
            'connection_strings': connection_strings,
            'required_services': required_services,
            'existing_services': existing_services
        }

    # Helper methods

    def _infer_namespace(self, app_name: str, context: Dict[str, Any]) -> str:
        """Determine the appropriate namespace"""
        # Use context namespace if provided
        if context.get('namespace'):
            return context['namespace']

        # Use environment-based namespace
        env = context.get('environment', 'default')
        if env in ['production', 'prod']:
            return 'production'
        elif env in ['staging', 'stage']:
            return 'staging'
        elif env in ['development', 'dev']:
            return 'development'

        # Default namespace
        return 'default'

    def _infer_database_config(
        self,
        app_name: str,
        db_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Infer database configuration"""
        db_type = db_config.get('type', 'postgresql').lower()

        return {
            'database_type': db_type,
            'database_host': f'{app_name}-{db_type}',
            'database_port': 5432 if 'postgres' in db_type else 3306,
            'database_name': app_name,
            'database_user': app_name
        }

    def _infer_cache_config(
        self,
        app_name: str,
        cache_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Infer cache configuration"""
        cache_type = cache_config.get('type', 'redis').lower()

        return {
            'cache_type': cache_type,
            'redis_host': f'{app_name}-redis',
            'redis_port': 6379
        }

    def _infer_message_queue_config(
        self,
        app_name: str,
        mq_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Infer message queue configuration"""
        mq_type = mq_config.get('type', 'rabbitmq').lower()

        return {
            'message_queue_type': mq_type,
            'message_queue_host': f'{app_name}-{mq_type}',
            'message_queue_port': 5672 if mq_type == 'rabbitmq' else 9092
        }

    def _infer_domain_config(
        self,
        app_name: str,
        ingress_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Infer domain and ingress configuration"""
        # Use provided domain or generate one
        domain = ingress_config.get('domain') or context.get('domain')
        if not domain:
            cluster_domain = context.get('cluster_domain', 'cluster.local')
            domain = f'{app_name}.{cluster_domain}'

        return {
            'domain': domain,
            'ingress_path': ingress_config.get('path', '/'),
            'ingress_class': ingress_config.get('class', 'traefik')
        }

    def _infer_storage_config(
        self,
        app_name: str,
        storage_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Infer storage configuration"""
        storage_class = storage_config.get('class', context.get('default_storage_class', 'local-path'))

        return {
            'storage_class': storage_class,
            'storage_size': storage_config.get('size', '10Gi')
        }

    def _infer_resource_config(
        self,
        resource_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Infer compute resource requirements"""
        return {
            'cpu_request': resource_config.get('cpu', {}).get('request', '100m'),
            'cpu_limit': resource_config.get('cpu', {}).get('limit', '500m'),
            'memory_request': resource_config.get('memory', {}).get('request', '128Mi'),
            'memory_limit': resource_config.get('memory', {}).get('limit', '512Mi')
        }

    def _generate_password(self, length: int = 32) -> str:
        """Generate a secure random password"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def _generate_secret_key(self, length: int = 64) -> str:
        """Generate a secure secret key (hex)"""
        return secrets.token_hex(length // 2)

    def _generate_fernet_key(self) -> str:
        """Generate a Fernet encryption key"""
        import base64
        key = secrets.token_bytes(32)
        return base64.urlsafe_b64encode(key).decode()

    def _build_database_url(
        self,
        db_type: str,
        user: str,
        password: str,
        host: str,
        port: int,
        database: str
    ) -> str:
        """Build database connection URL"""
        if 'postgres' in db_type:
            return f'postgresql://{user}:{password}@{host}:{port}/{database}'
        elif 'mysql' in db_type or 'mariadb' in db_type:
            return f'mysql://{user}:{password}@{host}:{port}/{database}'
        else:
            return f'{db_type}://{user}:{password}@{host}:{port}/{database}'

    def _build_redis_url(
        self,
        host: str,
        port: int,
        password: Optional[str] = None
    ) -> str:
        """Build Redis connection URL"""
        if password:
            return f'redis://:{password}@{host}:{port}/0'
        return f'redis://{host}:{port}/0'

    def _service_exists(
        self,
        service_name: str,
        existing_resources: Dict[str, Any]
    ) -> bool:
        """Check if a service already exists in the cluster"""
        services = existing_resources.get('services', [])
        return any(s.get('name') == service_name for s in services)

    def _get_existing_service_name(
        self,
        service_type: str,
        existing_resources: Dict[str, Any]
    ) -> str:
        """Get the name of an existing service"""
        services = existing_resources.get('services', [])
        for service in services:
            if service_type in service.get('name', '').lower():
                return service['name']
        return f'{service_type}-service'
