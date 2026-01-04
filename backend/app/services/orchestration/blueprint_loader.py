"""
Blueprint Loader Service

Loads and manages application blueprints for semantic deployment orchestration.
Supports both database-stored and file-based blueprints.
"""

import logging
import yaml
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class BlueprintLoaderError(Exception):
    """Base exception for blueprint loader errors"""
    pass


class BlueprintNotFoundError(BlueprintLoaderError):
    """Raised when blueprint is not found"""
    pass


class BlueprintValidationError(BlueprintLoaderError):
    """Raised when blueprint validation fails"""
    pass


class BlueprintLoader:
    """
    Loads application blueprints from database or filesystem.

    Blueprints define how applications should be deployed, including:
    - Required dependencies
    - Resource templates (K8s manifests or Docker Compose)
    - Configuration parameters
    - Auto-wiring logic
    """

    def __init__(self, db_session: Optional[Session] = None, blueprints_dir: Optional[str] = None):
        """
        Initialize blueprint loader.

        Args:
            db_session: SQLAlchemy database session (optional)
            blueprints_dir: Directory containing blueprint YAML files
        """
        self.db = db_session
        self.blueprints_dir = Path(blueprints_dir) if blueprints_dir else Path(__file__).parent.parent.parent / "blueprints"
        self.logger = logger
        self._cache: Dict[str, Dict[str, Any]] = {}

        # Create blueprints directory if it doesn't exist
        if not self.blueprints_dir.exists():
            logger.info(f"Creating blueprints directory: {self.blueprints_dir}")
            self.blueprints_dir.mkdir(parents=True, exist_ok=True)

    def get_blueprint(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get blueprint by name.

        First checks database, then falls back to filesystem.

        Args:
            name: Blueprint name (e.g., "authentik", "postgresql")

        Returns:
            Blueprint dictionary or None if not found
        """
        # Check cache first
        if name in self._cache:
            self.logger.debug(f"Blueprint '{name}' loaded from cache")
            return self._cache[name]

        # Try database first
        blueprint = self._load_from_database(name)
        if blueprint:
            self._cache[name] = blueprint
            return blueprint

        # Fall back to filesystem
        blueprint = self._load_from_filesystem(name)
        if blueprint:
            self._cache[name] = blueprint
            return blueprint

        self.logger.warning(f"Blueprint '{name}' not found in database or filesystem")
        return None

    def _load_from_database(self, name: str) -> Optional[Dict[str, Any]]:
        """Load blueprint from database."""
        try:
            from app.models import ApplicationBlueprint

            blueprint = self.db.query(ApplicationBlueprint).filter_by(
                name=name,
                is_active=True
            ).first()

            if not blueprint:
                return None

            self.logger.info(f"Loaded blueprint '{name}' from database")

            return {
                "name": blueprint.name,
                "description": blueprint.description,
                "category": blueprint.category,
                "platform": blueprint.platform,
                "type": blueprint.blueprint_type,
                "template": blueprint.manifest_template,
                "variables": blueprint.variables,
                "defaults": blueprint.default_values,
                "dependencies": blueprint.dependencies,
                "ports": blueprint.ports,
                "volumes": blueprint.volumes,
                "environment": blueprint.environment_vars,
                "metadata": blueprint.metadata,
                "is_official": blueprint.is_official
            }

        except Exception as e:
            self.logger.error(f"Failed to load blueprint from database: {e}")
            return None

    def _load_from_filesystem(self, name: str) -> Optional[Dict[str, Any]]:
        """Load blueprint from YAML file."""
        try:
            # Try .yaml and .yml extensions
            for ext in ['.yaml', '.yml']:
                blueprint_path = self.blueprints_dir / f"{name}{ext}"
                if blueprint_path.exists():
                    with open(blueprint_path, 'r') as f:
                        blueprint = yaml.safe_load(f)

                    self.logger.info(f"Loaded blueprint '{name}' from {blueprint_path}")
                    return blueprint

            return None

        except Exception as e:
            self.logger.error(f"Failed to load blueprint from filesystem: {e}")
            return None

    def list_blueprints(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all available blueprints.

        Args:
            category: Optional category filter

        Returns:
            List of blueprint metadata dictionaries
        """
        blueprints = []

        # Load from database
        try:
            from app.models import ApplicationBlueprint

            query = self.db.query(ApplicationBlueprint).filter_by(is_active=True)
            if category:
                query = query.filter_by(category=category)

            db_blueprints = query.all()

            for bp in db_blueprints:
                blueprints.append({
                    "name": bp.name,
                    "description": bp.description,
                    "category": bp.category,
                    "platform": bp.platform,
                    "type": bp.blueprint_type,
                    "is_official": bp.is_official,
                    "deployment_count": bp.deployment_count,
                    "source": "database"
                })

        except Exception as e:
            self.logger.error(f"Failed to list blueprints from database: {e}")

        # Load from filesystem
        if self.blueprints_dir.exists():
            for blueprint_file in self.blueprints_dir.glob("*.y*ml"):
                try:
                    with open(blueprint_file, 'r') as f:
                        bp = yaml.safe_load(f)

                    # Skip if already loaded from database
                    if any(b["name"] == bp.get("name") for b in blueprints):
                        continue

                    if category and bp.get("category") != category:
                        continue

                    blueprints.append({
                        "name": bp.get("name"),
                        "description": bp.get("description"),
                        "category": bp.get("category"),
                        "platform": bp.get("platform", "both"),
                        "type": bp.get("type"),
                        "is_official": bp.get("is_official", False),
                        "source": "filesystem"
                    })

                except Exception as e:
                    self.logger.error(f"Failed to load blueprint {blueprint_file}: {e}")

        return blueprints

    def clear_cache(self):
        """Clear the blueprint cache."""
        self._cache.clear()
        self.logger.debug("Blueprint cache cleared")

    def validate_blueprint(self, blueprint: Dict[str, Any], name: str) -> None:
        """
        Validate blueprint structure and required fields.

        Args:
            blueprint: Blueprint dictionary to validate
            name: Blueprint name (for error messages)

        Raises:
            BlueprintValidationError: If validation fails
        """
        errors = []

        # Check for metadata
        if 'metadata' in blueprint:
            metadata = blueprint.get('metadata', {})
            if not metadata.get('name'):
                errors.append("Missing metadata.name")
            if not metadata.get('version'):
                errors.append("Missing metadata.version")
        elif 'name' not in blueprint:
            errors.append("Missing name field")

        # Check for requirements
        if 'requirements' not in blueprint:
            errors.append("Missing requirements section")

        # Check for templates
        if 'templates' in blueprint:
            templates = blueprint.get('templates', {})
            if not templates.get('kubernetes') and not templates.get('docker'):
                errors.append("Templates must contain kubernetes or docker section")

        if errors:
            error_msg = f"Blueprint '{name}' validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.error(error_msg)
            raise BlueprintValidationError(error_msg)

        logger.debug(f"Blueprint '{name}' validation passed")

    def save_blueprint(self, name: str, blueprint: Dict[str, Any]) -> None:
        """
        Save a blueprint to filesystem.

        Args:
            name: Blueprint name
            blueprint: Blueprint dictionary

        Raises:
            BlueprintValidationError: If blueprint is invalid
        """
        # Validate before saving
        self.validate_blueprint(blueprint, name)

        blueprint_path = self.blueprints_dir / f"{name}.yaml"

        try:
            with open(blueprint_path, 'w') as f:
                yaml.dump(blueprint, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Saved blueprint to: {blueprint_path}")

            # Update cache
            self._cache[name] = blueprint

        except Exception as e:
            logger.error(f"Error saving blueprint {name}: {e}")
            raise BlueprintLoaderError(f"Failed to save blueprint '{name}': {e}") from e

    def delete_blueprint(self, name: str) -> None:
        """
        Delete a blueprint file.

        Args:
            name: Blueprint name

        Raises:
            BlueprintNotFoundError: If blueprint doesn't exist
        """
        blueprint_path = self.blueprints_dir / f"{name}.yaml"
        if not blueprint_path.exists():
            blueprint_path = self.blueprints_dir / f"{name}.yml"

        if not blueprint_path.exists():
            raise BlueprintNotFoundError(f"Blueprint '{name}' not found")

        try:
            blueprint_path.unlink()
            logger.info(f"Deleted blueprint: {blueprint_path}")

            # Remove from cache
            if name in self._cache:
                del self._cache[name]

        except Exception as e:
            logger.error(f"Error deleting blueprint {name}: {e}")
            raise BlueprintLoaderError(f"Failed to delete blueprint '{name}': {e}") from e

    def search_blueprints(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search blueprints by name, category, or tags.

        Args:
            query: Search query (matches name and description)
            category: Filter by category
            tags: Filter by tags (matches any)

        Returns:
            List of matching blueprint metadata
        """
        all_blueprints = self.list_blueprints(category=category)

        if not query and not tags:
            return all_blueprints

        results = []

        for blueprint in all_blueprints:
            # Filter by tags
            if tags:
                blueprint_tags = blueprint.get('tags', [])
                if isinstance(blueprint_tags, list):
                    blueprint_tags = [str(t).lower() for t in blueprint_tags]
                    if not any(tag.lower() in blueprint_tags for tag in tags):
                        continue

            # Filter by query
            if query:
                query_lower = query.lower()
                name_match = query_lower in blueprint.get('name', '').lower()
                desc_match = query_lower in blueprint.get('description', '').lower()
                if not (name_match or desc_match):
                    continue

            results.append(blueprint)

        logger.info(f"Search found {len(results)} blueprints (query={query}, category={category}, tags={tags})")
        return results


# Global blueprint loader instance
_blueprint_loader: Optional[BlueprintLoader] = None


def get_blueprint_loader(db_session: Optional[Session] = None, blueprints_dir: Optional[str] = None) -> BlueprintLoader:
    """
    Get or create the global blueprint loader instance.

    Args:
        db_session: SQLAlchemy database session (optional)
        blueprints_dir: Directory containing blueprints (optional)

    Returns:
        BlueprintLoader instance
    """
    global _blueprint_loader
    if _blueprint_loader is None:
        _blueprint_loader = BlueprintLoader(db_session, blueprints_dir)
    return _blueprint_loader
