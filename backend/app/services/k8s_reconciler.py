"""
Kubernetes Reconciler Service

Implements the reconciliation loop for Kubernetes resources managed by Unity.
Compares desired state with actual cluster state and applies changes when drift is detected.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import traceback

from sqlalchemy.orm import Session
from sqlalchemy import and_

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False
    logging.warning("kubernetes client library not installed. K8s reconciliation will be disabled.")

from app import models

logger = logging.getLogger(__name__)


class KubernetesReconciler:
    """
    Kubernetes reconciler that compares desired state vs current state
    and applies changes to maintain consistency.
    """

    def __init__(self, db: Session):
        self.db = db
        self._api_clients = {}  # Cache of API clients per cluster

        if not KUBERNETES_AVAILABLE:
            logger.warning("Kubernetes client not available. Reconciliation will be skipped.")

    def _get_api_client(self, cluster: models.KubernetesCluster) -> Optional[client.ApiClient]:
        """
        Get or create Kubernetes API client for a cluster.

        Args:
            cluster: KubernetesCluster model instance

        Returns:
            Kubernetes ApiClient or None if unable to connect
        """
        if not KUBERNETES_AVAILABLE:
            return None

        # Check cache
        if cluster.id in self._api_clients:
            return self._api_clients[cluster.id]

        try:
            # Load kubeconfig
            if cluster.kubeconfig_path:
                # Load from file path
                config.load_kube_config(
                    config_file=cluster.kubeconfig_path,
                    context=cluster.context_name
                )
            else:
                # Try in-cluster config
                config.load_incluster_config()

            api_client = client.ApiClient()
            self._api_clients[cluster.id] = api_client

            logger.info(f"Connected to cluster: {cluster.name}")
            return api_client

        except Exception as e:
            logger.error(f"Failed to connect to cluster {cluster.name}: {e}")
            # Update cluster health status
            cluster.health_status = 'unhealthy'
            cluster.health_message = f"Connection failed: {str(e)}"
            cluster.last_health_check = datetime.now(timezone.utc)
            self.db.commit()
            return None

    def _get_dynamic_client(self, api_client: client.ApiClient, api_version: str, kind: str):
        """
        Get the appropriate Kubernetes API client for a resource type.

        Args:
            api_client: Base ApiClient
            api_version: API version (e.g., "v1", "apps/v1")
            kind: Resource kind (e.g., "Deployment", "Service")

        Returns:
            Appropriate API client class instance
        """
        # Map common resource types to their API clients
        api_map = {
            # Core v1
            ("v1", "Pod"): client.CoreV1Api,
            ("v1", "Service"): client.CoreV1Api,
            ("v1", "ConfigMap"): client.CoreV1Api,
            ("v1", "Secret"): client.CoreV1Api,
            ("v1", "PersistentVolumeClaim"): client.CoreV1Api,
            ("v1", "Namespace"): client.CoreV1Api,

            # Apps v1
            ("apps/v1", "Deployment"): client.AppsV1Api,
            ("apps/v1", "StatefulSet"): client.AppsV1Api,
            ("apps/v1", "DaemonSet"): client.AppsV1Api,
            ("apps/v1", "ReplicaSet"): client.AppsV1Api,

            # Batch
            ("batch/v1", "Job"): client.BatchV1Api,
            ("batch/v1", "CronJob"): client.BatchV1Api,

            # Networking
            ("networking.k8s.io/v1", "Ingress"): client.NetworkingV1Api,
        }

        key = (api_version, kind)
        api_class = api_map.get(key)

        if not api_class:
            logger.warning(f"No API client mapping for {api_version}/{kind}, using CoreV1Api as fallback")
            api_class = client.CoreV1Api

        return api_class(api_client)

    def _get_resource_from_cluster(
        self,
        api_client: client.ApiClient,
        resource: models.KubernetesResource
    ) -> Optional[Dict]:
        """
        Fetch current state of a resource from the cluster.

        Args:
            api_client: Kubernetes ApiClient
            resource: KubernetesResource model

        Returns:
            Resource as dict or None if not found
        """
        try:
            api = self._get_dynamic_client(api_client, resource.api_version, resource.kind)

            # Map resource kinds to their read methods
            if resource.kind == "Deployment":
                result = api.read_namespaced_deployment(
                    name=resource.name,
                    namespace=resource.namespace
                )
            elif resource.kind == "Service":
                result = api.read_namespaced_service(
                    name=resource.name,
                    namespace=resource.namespace
                )
            elif resource.kind == "ConfigMap":
                result = api.read_namespaced_config_map(
                    name=resource.name,
                    namespace=resource.namespace
                )
            elif resource.kind == "Secret":
                result = api.read_namespaced_secret(
                    name=resource.name,
                    namespace=resource.namespace
                )
            elif resource.kind == "StatefulSet":
                result = api.read_namespaced_stateful_set(
                    name=resource.name,
                    namespace=resource.namespace
                )
            elif resource.kind == "DaemonSet":
                result = api.read_namespaced_daemon_set(
                    name=resource.name,
                    namespace=resource.namespace
                )
            elif resource.kind == "Ingress":
                result = api.read_namespaced_ingress(
                    name=resource.name,
                    namespace=resource.namespace
                )
            elif resource.kind == "Job":
                result = api.read_namespaced_job(
                    name=resource.name,
                    namespace=resource.namespace
                )
            elif resource.kind == "PersistentVolumeClaim":
                result = api.read_namespaced_persistent_volume_claim(
                    name=resource.name,
                    namespace=resource.namespace
                )
            else:
                logger.warning(f"Unsupported resource kind: {resource.kind}")
                return None

            # Convert to dict
            return api_client.sanitize_for_serialization(result)

        except ApiException as e:
            if e.status == 404:
                logger.info(f"Resource {resource.namespace}/{resource.name} not found in cluster")
                return None
            else:
                logger.error(f"Error fetching resource {resource.namespace}/{resource.name}: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error fetching resource: {e}")
            raise

    def _detect_drift(
        self,
        desired_state: Dict,
        current_state: Optional[Dict]
    ) -> tuple[bool, Optional[Dict]]:
        """
        Compare desired state with current state to detect drift.

        Args:
            desired_state: Desired resource manifest
            current_state: Current resource state from cluster

        Returns:
            Tuple of (drift_detected: bool, differences: dict)
        """
        if current_state is None:
            # Resource doesn't exist - that's drift
            return True, {"reason": "resource_not_found", "action": "create"}

        # Compare key fields (ignoring runtime/status fields)
        differences = {}

        # Compare spec
        desired_spec = desired_state.get("spec", {})
        current_spec = current_state.get("spec", {})

        if desired_spec != current_spec:
            differences["spec"] = {
                "desired": desired_spec,
                "current": current_spec
            }

        # Compare metadata (labels, annotations)
        desired_metadata = desired_state.get("metadata", {})
        current_metadata = current_state.get("metadata", {})

        # Check labels
        desired_labels = desired_metadata.get("labels", {})
        current_labels = current_metadata.get("labels", {})
        if desired_labels != current_labels:
            differences["labels"] = {
                "desired": desired_labels,
                "current": current_labels
            }

        # Check annotations (filter out system annotations)
        desired_annotations = desired_metadata.get("annotations", {})
        current_annotations = current_metadata.get("annotations", {})
        # Filter out kubectl annotations
        current_annotations = {
            k: v for k, v in current_annotations.items()
            if not k.startswith("kubectl.kubernetes.io/")
        }
        if desired_annotations != current_annotations:
            differences["annotations"] = {
                "desired": desired_annotations,
                "current": current_annotations
            }

        drift_detected = len(differences) > 0
        return drift_detected, differences if drift_detected else None

    def _apply_resource(
        self,
        api_client: client.ApiClient,
        resource: models.KubernetesResource,
        desired_state: Dict,
        current_state: Optional[Dict]
    ) -> Dict:
        """
        Apply desired state to the cluster.

        Args:
            api_client: Kubernetes ApiClient
            resource: KubernetesResource model
            desired_state: Desired manifest to apply
            current_state: Current state (None if resource doesn't exist)

        Returns:
            Dict with result information
        """
        try:
            api = self._get_dynamic_client(api_client, resource.api_version, resource.kind)

            # Prepare body from desired state
            body = desired_state.copy()

            # Ensure metadata is set
            if "metadata" not in body:
                body["metadata"] = {}
            body["metadata"]["name"] = resource.name
            body["metadata"]["namespace"] = resource.namespace

            # Apply the resource
            if current_state is None:
                # Create new resource
                logger.info(f"Creating {resource.kind} {resource.namespace}/{resource.name}")

                if resource.kind == "Deployment":
                    result = api.create_namespaced_deployment(
                        namespace=resource.namespace,
                        body=body
                    )
                elif resource.kind == "Service":
                    result = api.create_namespaced_service(
                        namespace=resource.namespace,
                        body=body
                    )
                elif resource.kind == "ConfigMap":
                    result = api.create_namespaced_config_map(
                        namespace=resource.namespace,
                        body=body
                    )
                elif resource.kind == "Secret":
                    result = api.create_namespaced_secret(
                        namespace=resource.namespace,
                        body=body
                    )
                elif resource.kind == "StatefulSet":
                    result = api.create_namespaced_stateful_set(
                        namespace=resource.namespace,
                        body=body
                    )
                elif resource.kind == "DaemonSet":
                    result = api.create_namespaced_daemon_set(
                        namespace=resource.namespace,
                        body=body
                    )
                elif resource.kind == "Ingress":
                    result = api.create_namespaced_ingress(
                        namespace=resource.namespace,
                        body=body
                    )
                elif resource.kind == "Job":
                    result = api.create_namespaced_job(
                        namespace=resource.namespace,
                        body=body
                    )
                elif resource.kind == "PersistentVolumeClaim":
                    result = api.create_namespaced_persistent_volume_claim(
                        namespace=resource.namespace,
                        body=body
                    )
                else:
                    return {
                        "success": False,
                        "error": f"Unsupported resource kind for creation: {resource.kind}"
                    }

                action = "created"
            else:
                # Update existing resource
                logger.info(f"Updating {resource.kind} {resource.namespace}/{resource.name}")

                # Preserve resourceVersion for updates
                if "resourceVersion" in current_state.get("metadata", {}):
                    body["metadata"]["resourceVersion"] = current_state["metadata"]["resourceVersion"]

                if resource.kind == "Deployment":
                    result = api.patch_namespaced_deployment(
                        name=resource.name,
                        namespace=resource.namespace,
                        body=body
                    )
                elif resource.kind == "Service":
                    result = api.patch_namespaced_service(
                        name=resource.name,
                        namespace=resource.namespace,
                        body=body
                    )
                elif resource.kind == "ConfigMap":
                    result = api.patch_namespaced_config_map(
                        name=resource.name,
                        namespace=resource.namespace,
                        body=body
                    )
                elif resource.kind == "Secret":
                    result = api.patch_namespaced_secret(
                        name=resource.name,
                        namespace=resource.namespace,
                        body=body
                    )
                elif resource.kind == "StatefulSet":
                    result = api.patch_namespaced_stateful_set(
                        name=resource.name,
                        namespace=resource.namespace,
                        body=body
                    )
                elif resource.kind == "DaemonSet":
                    result = api.patch_namespaced_daemon_set(
                        name=resource.name,
                        namespace=resource.namespace,
                        body=body
                    )
                elif resource.kind == "Ingress":
                    result = api.patch_namespaced_ingress(
                        name=resource.name,
                        namespace=resource.namespace,
                        body=body
                    )
                elif resource.kind == "Job":
                    result = api.patch_namespaced_job(
                        name=resource.name,
                        namespace=resource.namespace,
                        body=body
                    )
                elif resource.kind == "PersistentVolumeClaim":
                    result = api.patch_namespaced_persistent_volume_claim(
                        name=resource.name,
                        namespace=resource.namespace,
                        body=body
                    )
                else:
                    return {
                        "success": False,
                        "error": f"Unsupported resource kind for update: {resource.kind}"
                    }

                action = "updated"

            # Convert result to dict
            result_dict = api_client.sanitize_for_serialization(result)

            return {
                "success": True,
                "action": action,
                "state": result_dict
            }

        except ApiException as e:
            logger.error(f"API error applying resource: {e}")
            return {
                "success": False,
                "error": f"API error: {e.status} - {e.reason}",
                "details": e.body
            }
        except Exception as e:
            logger.error(f"Unexpected error applying resource: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }

    async def reconcile_resource(self, resource_id: int) -> Dict[str, Any]:
        """
        Reconcile a single Kubernetes resource.

        Args:
            resource_id: ID of the KubernetesResource to reconcile

        Returns:
            Dict with reconciliation result
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Fetch resource
            resource = self.db.query(models.KubernetesResource).filter(
                models.KubernetesResource.id == resource_id
            ).first()

            if not resource:
                logger.warning(f"Resource {resource_id} not found")
                return {"success": False, "error": "Resource not found"}

            # Skip if not active or auto_reconcile is disabled
            if not resource.is_active:
                logger.debug(f"Skipping inactive resource {resource_id}")
                return {"success": True, "skipped": True, "reason": "inactive"}

            if not resource.auto_reconcile:
                logger.debug(f"Skipping resource {resource_id} (auto_reconcile disabled)")
                return {"success": True, "skipped": True, "reason": "auto_reconcile_disabled"}

            # Get cluster
            cluster = resource.cluster
            if not cluster or not cluster.is_active:
                logger.warning(f"Cluster for resource {resource_id} is not active")
                return {"success": False, "error": "Cluster not active"}

            # Create reconciliation record
            reconciliation = models.ResourceReconciliation(
                resource_id=resource.id,
                started_at=start_time,
                status='in_progress',
                triggered_by='scheduler'
            )
            self.db.add(reconciliation)
            self.db.commit()

            # Update resource status
            resource.reconciliation_status = 'in_progress'
            self.db.commit()

            # Get API client
            api_client = self._get_api_client(cluster)
            if not api_client:
                error_msg = f"Failed to connect to cluster {cluster.name}"
                resource.reconciliation_status = 'failed'
                resource.last_error = error_msg
                reconciliation.status = 'failed'
                reconciliation.error_message = error_msg
                reconciliation.completed_at = datetime.now(timezone.utc)
                self.db.commit()
                return {"success": False, "error": error_msg}

            # Fetch current state from cluster
            current_state = self._get_resource_from_cluster(api_client, resource)

            # Detect drift
            drift_detected, differences = self._detect_drift(
                resource.desired_state,
                current_state
            )

            resource.drift_detected = drift_detected
            reconciliation.previous_state = current_state

            result = {
                "success": True,
                "drift_detected": drift_detected,
                "resource": f"{resource.namespace}/{resource.name}",
                "kind": resource.kind
            }

            if drift_detected:
                logger.info(f"Drift detected for {resource.kind} {resource.namespace}/{resource.name}")
                reconciliation.changes_applied = differences

                # Apply changes
                apply_result = self._apply_resource(
                    api_client,
                    resource,
                    resource.desired_state,
                    current_state
                )

                if apply_result["success"]:
                    # Fetch updated state
                    new_state = self._get_resource_from_cluster(api_client, resource)

                    resource.current_state = new_state
                    resource.reconciliation_status = 'success'
                    resource.last_error = None
                    reconciliation.status = 'success'
                    reconciliation.result = apply_result["action"]
                    reconciliation.new_state = new_state

                    result["action"] = apply_result["action"]
                    result["changes_applied"] = True
                else:
                    # Failed to apply
                    resource.reconciliation_status = 'failed'
                    resource.last_error = apply_result.get("error", "Unknown error")
                    reconciliation.status = 'failed'
                    reconciliation.error_message = apply_result.get("error")

                    result["success"] = False
                    result["error"] = apply_result.get("error")
            else:
                # No drift - update current state
                resource.current_state = current_state
                resource.reconciliation_status = 'success'
                resource.drift_detected = False
                reconciliation.status = 'success'
                reconciliation.result = 'no_change'
                reconciliation.new_state = current_state

                result["action"] = "no_change"

            # Update timestamps
            resource.last_reconciled = datetime.now(timezone.utc)
            reconciliation.completed_at = datetime.now(timezone.utc)

            # Calculate duration
            duration = (reconciliation.completed_at - start_time).total_seconds() * 1000
            reconciliation.duration_ms = int(duration)

            self.db.commit()

            logger.info(f"Reconciliation completed for {resource.kind} {resource.namespace}/{resource.name} in {duration:.0f}ms")
            return result

        except Exception as e:
            logger.error(f"Error reconciling resource {resource_id}: {e}")
            logger.error(traceback.format_exc())

            # Update failure state
            if 'resource' in locals():
                resource.reconciliation_status = 'failed'
                resource.last_error = str(e)

            if 'reconciliation' in locals():
                reconciliation.status = 'failed'
                reconciliation.error_message = str(e)
                reconciliation.completed_at = datetime.now(timezone.utc)

            self.db.commit()

            return {
                "success": False,
                "error": str(e)
            }

    async def reconcile_all(self) -> Dict[str, Any]:
        """
        Reconcile all active Kubernetes resources across all enabled clusters.

        Returns:
            Dict with summary of reconciliation results
        """
        logger.info("Starting reconciliation of all Kubernetes resources")
        start_time = datetime.now(timezone.utc)

        results = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "drift_detected": 0,
            "changes_applied": 0,
            "errors": []
        }

        try:
            # Get all active clusters (default cluster or all active clusters)
            clusters = self.db.query(models.KubernetesCluster).filter(
                and_(
                    models.KubernetesCluster.is_active == True,
                    models.KubernetesCluster.is_default == True
                )
            ).all()

            # If no default cluster, use all active clusters
            if not clusters:
                clusters = self.db.query(models.KubernetesCluster).filter(
                    models.KubernetesCluster.is_active == True
                ).all()

            logger.info(f"Found {len(clusters)} active cluster(s)")

            # Get all active resources for these clusters
            for cluster in clusters:
                resources = self.db.query(models.KubernetesResource).filter(
                    and_(
                        models.KubernetesResource.cluster_id == cluster.id,
                        models.KubernetesResource.is_active == True
                    )
                ).all()

                logger.info(f"Processing {len(resources)} resource(s) in cluster {cluster.name}")

                for resource in resources:
                    results["total"] += 1

                    result = await self.reconcile_resource(resource.id)

                    if result.get("skipped"):
                        results["skipped"] += 1
                    elif result.get("success"):
                        results["success"] += 1
                        if result.get("drift_detected"):
                            results["drift_detected"] += 1
                        if result.get("changes_applied"):
                            results["changes_applied"] += 1
                    else:
                        results["failed"] += 1
                        results["errors"].append({
                            "resource_id": resource.id,
                            "resource": f"{resource.namespace}/{resource.name}",
                            "error": result.get("error")
                        })

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            results["duration_seconds"] = round(duration, 2)

            logger.info(
                f"Reconciliation complete: {results['success']}/{results['total']} succeeded, "
                f"{results['failed']} failed, {results['skipped']} skipped, "
                f"{results['drift_detected']} drift detected, "
                f"{results['changes_applied']} changes applied "
                f"in {duration:.1f}s"
            )

            return results

        except Exception as e:
            logger.error(f"Error in reconcile_all: {e}")
            logger.error(traceback.format_exc())
            results["error"] = str(e)
            return results
