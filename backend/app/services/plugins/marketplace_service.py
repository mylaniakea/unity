"""
Plugin Marketplace Service

Handles plugin discovery, installation, updates, and ratings from the marketplace.
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from app.models.plugin_marketplace import (
    MarketplacePlugin, PluginReview, PluginInstallation, PluginDownload
)
from app.models.plugin import Plugin
from app.plugins.base import PluginMetadata, PluginCategory

logger = logging.getLogger(__name__)


class MarketplaceService:
    """Service for managing plugin marketplace operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def list_plugins(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        search: Optional[str] = None,
        featured: Optional[bool] = None,
        verified: Optional[bool] = None,
        min_rating: Optional[float] = None,
        skip: int = 0,
        limit: int = 50,
        sort_by: str = "popularity"  # popularity, rating, newest, name
    ) -> Tuple[List[MarketplacePlugin], int]:
        """
        List marketplace plugins with filtering and sorting.
        
        Returns:
            Tuple of (plugins list, total count)
        """
        query = self.db.query(MarketplacePlugin).filter(
            MarketplacePlugin.deprecated == False
        )
        
        # Apply filters
        if category:
            query = query.filter(MarketplacePlugin.category == category)
        
        if tag:
            # Filter by tag in JSON array
            query = query.filter(MarketplacePlugin.tags.contains([tag]))
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (MarketplacePlugin.name.ilike(search_term)) |
                (MarketplacePlugin.description.ilike(search_term))
            )
        
        if featured is not None:
            query = query.filter(MarketplacePlugin.featured == featured)
        
        if verified is not None:
            query = query.filter(MarketplacePlugin.verified == verified)
        
        if min_rating is not None:
            query = query.filter(MarketplacePlugin.rating_average >= min_rating)
        
        # Get total count
        total = query.count()
        
        # Apply sorting
        if sort_by == "popularity":
            query = query.order_by(desc(MarketplacePlugin.install_count))
        elif sort_by == "rating":
            query = query.order_by(desc(MarketplacePlugin.rating_average))
        elif sort_by == "newest":
            query = query.order_by(desc(MarketplacePlugin.published_at))
        elif sort_by == "name":
            query = query.order_by(MarketplacePlugin.name)
        else:
            query = query.order_by(desc(MarketplacePlugin.install_count))
        
        # Apply pagination
        plugins = query.offset(skip).limit(limit).all()
        
        return plugins, total
    
    def get_plugin(self, plugin_id: str) -> Optional[MarketplacePlugin]:
        """Get a specific marketplace plugin."""
        return self.db.query(MarketplacePlugin).filter(
            MarketplacePlugin.id == plugin_id
        ).first()
    
    def get_plugin_reviews(
        self,
        plugin_id: str,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "newest"  # newest, helpful, rating
    ) -> Tuple[List[PluginReview], int]:
        """Get reviews for a plugin."""
        query = self.db.query(PluginReview).filter(
            and_(
                PluginReview.plugin_id == plugin_id,
                PluginReview.approved == True
            )
        )
        
        total = query.count()
        
        # Apply sorting
        if sort_by == "newest":
            query = query.order_by(desc(PluginReview.created_at))
        elif sort_by == "helpful":
            query = query.order_by(desc(PluginReview.helpful_count))
        elif sort_by == "rating":
            query = query.order_by(desc(PluginReview.rating))
        else:
            query = query.order_by(desc(PluginReview.created_at))
        
        reviews = query.offset(skip).limit(limit).all()
        
        return reviews, total
    
    def add_review(
        self,
        plugin_id: str,
        user_id: str,
        user_name: str,
        rating: int,
        title: Optional[str] = None,
        review_text: Optional[str] = None
    ) -> PluginReview:
        """Add a review for a plugin."""
        # Validate rating
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")
        
        # Check if user already reviewed
        existing = self.db.query(PluginReview).filter(
            and_(
                PluginReview.plugin_id == plugin_id,
                PluginReview.user_id == user_id
            )
        ).first()
        
        if existing:
            # Update existing review
            existing.rating = rating
            existing.title = title
            existing.review_text = review_text
            existing.updated_at = datetime.utcnow()
            review = existing
        else:
            # Create new review
            review = PluginReview(
                plugin_id=plugin_id,
                user_id=user_id,
                user_name=user_name,
                rating=rating,
                title=title,
                review_text=review_text,
                verified_purchase=self._has_installed_plugin(user_id, plugin_id)
            )
            self.db.add(review)
        
        self.db.commit()
        
        # Update plugin rating average
        self._update_plugin_rating(plugin_id)
        
        return review
    
    def install_plugin(
        self,
        plugin_id: str,
        user_id: str,
        version: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Plugin]]:
        """
        Install a plugin from the marketplace.
        
        Returns:
            Tuple of (success, message, installed_plugin)
        """
        marketplace_plugin = self.get_plugin(plugin_id)
        
        if not marketplace_plugin:
            return False, f"Plugin {plugin_id} not found in marketplace", None
        
        # Check if already installed
        existing = self.db.query(Plugin).filter(Plugin.id == plugin_id).first()
        if existing:
            return False, f"Plugin {plugin_id} is already installed", existing
        
        # Download and install plugin
        try:
            installed_plugin = self._download_and_install_plugin(marketplace_plugin, version)
            
            # Record installation
            installation = PluginInstallation(
                marketplace_plugin_id=plugin_id,
                installed_plugin_id=plugin_id,
                installed_by=user_id,
                version_installed=version or marketplace_plugin.version,
                installation_method="marketplace"
            )
            self.db.add(installation)
            
            # Update install count
            marketplace_plugin.install_count += 1
            marketplace_plugin.download_count += 1
            
            self.db.commit()
            
            return True, f"Plugin {plugin_id} installed successfully", installed_plugin
            
        except Exception as e:
            logger.error(f"Failed to install plugin {plugin_id}: {e}", exc_info=True)
            self.db.rollback()
            return False, f"Installation failed: {str(e)}", None
    
    def uninstall_plugin(self, plugin_id: str, user_id: str) -> Tuple[bool, str]:
        """Uninstall a plugin."""
        plugin = self.db.query(Plugin).filter(Plugin.id == plugin_id).first()
        
        if not plugin:
            return False, f"Plugin {plugin_id} not found"
        
        # Mark installation as inactive
        installation = self.db.query(PluginInstallation).filter(
            and_(
                PluginInstallation.installed_plugin_id == plugin_id,
                PluginInstallation.active == True
            )
        ).first()
        
        if installation:
            installation.active = False
            installation.uninstalled_at = datetime.utcnow()
        
        # Delete plugin from database
        self.db.delete(plugin)
        self.db.commit()
        
        return True, f"Plugin {plugin_id} uninstalled successfully"
    
    def _download_and_install_plugin(
        self,
        marketplace_plugin: MarketplacePlugin,
        version: Optional[str] = None
    ) -> Plugin:
        """
        Download and install a plugin from its source.
        
        This is a placeholder - actual implementation would:
        1. Download plugin file from source_url
        2. Validate plugin structure
        3. Save to plugins directory
        4. Register in database
        """
        # TODO: Implement actual download and installation
        # For now, create a placeholder plugin entry
        
        plugin = Plugin(
            id=marketplace_plugin.id,
            name=marketplace_plugin.name,
            version=version or marketplace_plugin.version,
            category=marketplace_plugin.category,
            description=marketplace_plugin.description,
            author=marketplace_plugin.author,
            external=True,  # Marketplace plugins are external
            enabled=False,  # Don't auto-enable
            plugin_metadata={
                "source": marketplace_plugin.source_url,
                "marketplace": True
            }
        )
        
        self.db.add(plugin)
        return plugin
    
    def _update_plugin_rating(self, plugin_id: str):
        """Update plugin's average rating from reviews."""
        reviews = self.db.query(PluginReview).filter(
            and_(
                PluginReview.plugin_id == plugin_id,
                PluginReview.approved == True
            )
        ).all()
        
        if not reviews:
            return
        
        total_rating = sum(r.rating for r in reviews)
        average = total_rating / len(reviews)
        
        plugin = self.get_plugin(plugin_id)
        if plugin:
            plugin.rating_average = average
            plugin.rating_count = len(reviews)
            self.db.commit()
    
    def _has_installed_plugin(self, user_id: str, plugin_id: str) -> bool:
        """Check if user has installed the plugin."""
        installation = self.db.query(PluginInstallation).filter(
            and_(
                PluginInstallation.marketplace_plugin_id == plugin_id,
                PluginInstallation.installed_by == user_id,
                PluginInstallation.active == True
            )
        ).first()
        
        return installation is not None
    
    def record_download(
        self,
        plugin_id: str,
        version: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Record a plugin download for analytics."""
        download = PluginDownload(
            plugin_id=plugin_id,
            version=version,
            user_id=user_id,
            ip_address=ip_address,
            download_type="install"
        )
        
        self.db.add(download)
        
        # Update download count
        plugin = self.get_plugin(plugin_id)
        if plugin:
            plugin.download_count += 1
        
        self.db.commit()

