"""
Plugin Marketplace Models

Models for community plugin registry, ratings, and installation tracking.
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.plugin import PortableJSON


class MarketplacePlugin(Base):
    """Community plugin available in the marketplace."""
    __tablename__ = "marketplace_plugins"
    
    id = Column(String(100), primary_key=True)  # Unique plugin ID
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    description = Column(Text)
    author = Column(String(255), nullable=False)
    author_email = Column(String(255))
    author_url = Column(String(500))
    
    # Plugin metadata
    category = Column(String(50))
    tags = Column(PortableJSON, default=[])  # List of tags
    dependencies = Column(PortableJSON, default=[])  # List of dependencies
    requirements = Column(PortableJSON, default={})  # Python/system requirements
    
    # Plugin source
    source_type = Column(String(50), default="github")  # github, gitlab, url, file
    source_url = Column(String(1000))  # Repository URL or download URL
    source_path = Column(String(500))  # Path within repository (e.g., "plugins/my_plugin.py")
    
    # Installation info
    install_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    
    # Ratings and reviews
    rating_average = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    
    # Status
    verified = Column(Boolean, default=False)  # Verified by Unity team
    featured = Column(Boolean, default=False)  # Featured plugin
    deprecated = Column(Boolean, default=False)  # No longer maintained
    
    # Metadata
    readme = Column(Text)  # README content
    changelog = Column(Text)  # Changelog
    license = Column(String(100))
    homepage_url = Column(String(500))
    documentation_url = Column(String(500))
    
    # Timestamps
    published_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_synced_at = Column(DateTime(timezone=True))  # Last sync from source
    
    # Relationships
    reviews = relationship("PluginReview", back_populates="plugin", cascade="all, delete-orphan")
    installations = relationship("PluginInstallation", back_populates="marketplace_plugin")
    
    def __repr__(self):
        return f"<MarketplacePlugin(id={self.id}, name={self.name}, version={self.version})>"


class PluginReview(Base):
    """User reviews and ratings for marketplace plugins."""
    __tablename__ = "plugin_reviews"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plugin_id = Column(String(100), ForeignKey("marketplace_plugins.id"), nullable=False)
    user_id = Column(String(255), nullable=False)  # User who wrote the review
    user_name = Column(String(255))  # Display name
    
    rating = Column(Integer, nullable=False)  # 1-5 stars
    title = Column(String(255))
    review_text = Column(Text)
    
    # Helpful votes
    helpful_count = Column(Integer, default=0)
    
    # Status
    verified_purchase = Column(Boolean, default=False)  # User has installed plugin
    approved = Column(Boolean, default=True)  # Review approved (moderation)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    plugin = relationship("MarketplacePlugin", back_populates="reviews")
    
    def __repr__(self):
        return f"<PluginReview(plugin={self.plugin_id}, rating={self.rating}, user={self.user_id})>"


class PluginInstallation(Base):
    """Track plugin installations from marketplace."""
    __tablename__ = "plugin_installations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    marketplace_plugin_id = Column(String(100), ForeignKey("marketplace_plugins.id"), nullable=False)
    installed_plugin_id = Column(String(100), ForeignKey("plugins.id"), nullable=True)  # Link to installed plugin
    
    # Installation info
    installed_by = Column(String(255))  # User who installed
    version_installed = Column(String(50))
    installation_method = Column(String(50), default="marketplace")  # marketplace, manual, api
    
    # Status
    active = Column(Boolean, default=True)  # Still installed
    auto_update = Column(Boolean, default=False)  # Auto-update enabled
    
    # Timestamps
    installed_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    uninstalled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    marketplace_plugin = relationship("MarketplacePlugin", back_populates="installations")
    
    def __repr__(self):
        return f"<PluginInstallation(plugin={self.marketplace_plugin_id}, version={self.version_installed})>"


class PluginDownload(Base):
    """Track plugin downloads for analytics."""
    __tablename__ = "plugin_downloads"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plugin_id = Column(String(100), ForeignKey("marketplace_plugins.id"), nullable=False)
    
    # Download info
    version = Column(String(50))
    download_type = Column(String(50), default="install")  # install, update, manual
    user_id = Column(String(255), nullable=True)
    ip_address = Column(String(45))  # IPv4 or IPv6
    
    # Timestamps
    downloaded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<PluginDownload(plugin={self.plugin_id}, version={self.version})>"

