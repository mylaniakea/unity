"""
OAuth2 authentication endpoints for external providers.

Supports GitHub and Google OAuth login.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth, OAuthError

from app.core.database import get_db
from app.core.config import settings
from app.services.auth.oauth_service import get_oauth_service
from app.services.auth import jwt_handler
from app.services.auth.session_manager import SessionManager

router = APIRouter(prefix="/api/auth/oauth", tags=["OAuth"])

# Initialize OAuth client
oauth = OAuth()

# Register GitHub provider
if settings.github_client_id and settings.github_client_secret:
    oauth.register(
        name='github',
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        access_token_url='https://github.com/login/oauth/access_token',
        access_token_params=None,
        authorize_url='https://github.com/login/oauth/authorize',
        authorize_params=None,
        api_base_url='https://api.github.com/',
        client_kwargs={'scope': 'user:email'},
    )

# Register Google provider
if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name='google',
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )


@router.get("/github")
async def github_login(request: Request):
    """
    Initiate GitHub OAuth login.
    
    Redirects to GitHub authorization page.
    """
    if not settings.github_client_id:
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured")
    
    redirect_uri = settings.oauth_redirect_uri + "?provider=github"
    return await oauth.github.authorize_redirect(request, redirect_uri)


@router.get("/google")
async def google_login(request: Request):
    """
    Initiate Google OAuth login.
    
    Redirects to Google authorization page.
    """
    if not settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")
    
    redirect_uri = settings.oauth_redirect_uri + "?provider=google"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def oauth_callback(
    request: Request,
    provider: str,
    db: Session = Depends(get_db),
):
    """
    OAuth callback endpoint.
    
    Handles the OAuth provider's redirect after user authorizes the app.
    Creates or links user account and issues JWT token.
    """
    if provider not in ['github', 'google']:
        raise HTTPException(status_code=400, detail="Invalid OAuth provider")
    
    # Get OAuth client for provider
    if provider == 'github':
        if not settings.github_client_id:
            raise HTTPException(status_code=501, detail="GitHub OAuth not configured")
        oauth_client = oauth.github
    elif provider == 'google':
        if not settings.google_client_id:
            raise HTTPException(status_code=501, detail="Google OAuth not configured")
        oauth_client = oauth.google
    
    try:
        # Exchange authorization code for access token
        token = await oauth_client.authorize_access_token(request)
        
        # Get user info from provider
        if provider == 'github':
            resp = await oauth_client.get('user', token=token)
            userinfo = resp.json()
        elif provider == 'google':
            userinfo = token.get('userinfo')
            if not userinfo:
                resp = await oauth_client.get('https://www.googleapis.com/oauth2/v1/userinfo', token=token)
                userinfo = resp.json()
        
        # Handle OAuth callback - create/link user
        oauth_service = get_oauth_service(db, oauth)
        user, is_new = await oauth_service.handle_oauth_callback(
            provider=provider,
            token=token,
            userinfo=userinfo
        )
        
        # Create JWT token
        # jwt_handler module imported
        access_token = jwt_handler.create_access_token({"sub": user.username})
        
        # Create session
        session_manager = SessionManager()
        session_id = session_manager.create_session(
            user_id=str(user.id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"oauth_provider": provider, "is_new_user": is_new}
        )
        
        # Return success response with token
        # In production, you'd typically redirect to frontend with token in query param or cookie
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "session_id": session_id,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_new": is_new
            }
        }
    
    except OAuthError as error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error.error}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.get("/providers")
async def get_oauth_providers():
    """
    Get list of configured OAuth providers.
    
    Returns which providers are available for login.
    """
    providers = []
    
    if settings.github_client_id and settings.github_client_secret:
        providers.append({
            "name": "github",
            "display_name": "GitHub",
            "login_url": "/api/auth/oauth/github"
        })
    
    if settings.google_client_id and settings.google_client_secret:
        providers.append({
            "name": "google",
            "display_name": "Google",
            "login_url": "/api/auth/oauth/google"
        })
    
    return {"providers": providers}
