"""
Plugin Marketplace API

Endpoints for browsing, installing, and managing plugins from the marketplace.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.services.plugins.marketplace_service import MarketplaceService
from app.models.plugin_marketplace import MarketplacePlugin, PluginReview

router = APIRouter(prefix="/api/v1/marketplace", tags=["Plugin Marketplace"])


# Request/Response Models
class PluginListItem(BaseModel):
    """Marketplace plugin list item."""
    id: str
    name: str
    version: str
    description: Optional[str]
    author: str
    category: Optional[str]
    tags: List[str] = []
    rating_average: float
    rating_count: int
    install_count: int
    verified: bool
    featured: bool
    
    class Config:
        from_attributes = True


class PluginDetail(PluginListItem):
    """Full plugin details."""
    author_email: Optional[str]
    author_url: Optional[str]
    dependencies: List[str] = []
    requirements: dict = {}
    source_type: str
    source_url: Optional[str]
    readme: Optional[str]
    changelog: Optional[str]
    license: Optional[str]
    homepage_url: Optional[str]
    documentation_url: Optional[str]
    published_at: str
    updated_at: Optional[str]
    
    class Config:
        from_attributes = True


class ReviewCreate(BaseModel):
    """Create a review."""
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    title: Optional[str] = None
    review_text: Optional[str] = None


class ReviewResponse(BaseModel):
    """Review response."""
    id: int
    plugin_id: str
    user_id: str
    user_name: Optional[str]
    rating: int
    title: Optional[str]
    review_text: Optional[str]
    helpful_count: int
    verified_purchase: bool
    created_at: str
    
    class Config:
        from_attributes = True


class InstallResponse(BaseModel):
    """Plugin installation response."""
    success: bool
    message: str
    plugin_id: Optional[str] = None


@router.get("/plugins", response_model=dict)
async def list_marketplace_plugins(
    category: Optional[str] = Query(None, description="Filter by category"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    search: Optional[str] = Query(None, description="Search plugins"),
    featured: Optional[bool] = Query(None, description="Show only featured"),
    verified: Optional[bool] = Query(None, description="Show only verified"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="Minimum rating"),
    sort_by: str = Query("popularity", description="Sort by: popularity, rating, newest, name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List plugins available in the marketplace."""
    service = MarketplaceService(db)
    plugins, total = service.list_plugins(
        category=category,
        tag=tag,
        search=search,
        featured=featured,
        verified=verified,
        min_rating=min_rating,
        skip=skip,
        limit=limit,
        sort_by=sort_by
    )
    
    return {
        "plugins": [PluginListItem.from_orm(p) for p in plugins],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/plugins/{plugin_id}", response_model=PluginDetail)
async def get_marketplace_plugin(
    plugin_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a marketplace plugin."""
    service = MarketplaceService(db)
    plugin = service.get_plugin(plugin_id)
    
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")
    
    return PluginDetail.from_orm(plugin)


@router.get("/plugins/{plugin_id}/reviews", response_model=dict)
async def get_plugin_reviews(
    plugin_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("newest", description="Sort by: newest, helpful, rating"),
    db: Session = Depends(get_db)
):
    """Get reviews for a plugin."""
    service = MarketplaceService(db)
    reviews, total = service.get_plugin_reviews(
        plugin_id=plugin_id,
        skip=skip,
        limit=limit,
        sort_by=sort_by
    )
    
    return {
        "reviews": [ReviewResponse.from_orm(r) for r in reviews],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("/plugins/{plugin_id}/reviews", response_model=ReviewResponse)
async def create_review(
    plugin_id: str,
    review: ReviewCreate,
    user_id: str = "anonymous",  # TODO: Get from auth
    user_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Create or update a review for a plugin."""
    service = MarketplaceService(db)
    
    # Verify plugin exists
    plugin = service.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")
    
    review_obj = service.add_review(
        plugin_id=plugin_id,
        user_id=user_id,
        user_name=user_name or user_id,
        rating=review.rating,
        title=review.title,
        review_text=review.review_text
    )
    
    return ReviewResponse.from_orm(review_obj)


@router.post("/plugins/{plugin_id}/install", response_model=InstallResponse)
async def install_plugin(
    plugin_id: str,
    version: Optional[str] = Body(None),
    user_id: str = "system",  # TODO: Get from auth
    db: Session = Depends(get_db)
):
    """Install a plugin from the marketplace."""
    service = MarketplaceService(db)
    
    success, message, plugin = service.install_plugin(
        plugin_id=plugin_id,
        user_id=user_id,
        version=version
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return InstallResponse(
        success=True,
        message=message,
        plugin_id=plugin.id if plugin else None
    )


@router.delete("/plugins/{plugin_id}/uninstall")
async def uninstall_plugin(
    plugin_id: str,
    user_id: str = "system",  # TODO: Get from auth
    db: Session = Depends(get_db)
):
    """Uninstall a plugin."""
    service = MarketplaceService(db)
    
    success, message = service.uninstall_plugin(plugin_id=plugin_id, user_id=user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=message)
    
    return {"success": True, "message": message}


@router.get("/categories")
async def list_categories(db: Session = Depends(get_db)):
    """List all plugin categories in the marketplace."""
    service = MarketplaceService(db)
    plugins, _ = service.list_plugins(limit=1000)  # Get all for category extraction
    
    categories = set()
    for plugin in plugins:
        if plugin.category:
            categories.add(plugin.category)
    
    return {"categories": sorted(list(categories))}


@router.get("/tags")
async def list_tags(db: Session = Depends(get_db)):
    """List all tags used in the marketplace."""
    service = MarketplaceService(db)
    plugins, _ = service.list_plugins(limit=1000)
    
    tags = set()
    for plugin in plugins:
        if plugin.tags:
            tags.update(plugin.tags)
    
    return {"tags": sorted(list(tags))}

