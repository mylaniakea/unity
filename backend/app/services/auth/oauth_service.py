"""
OAuth2 authentication service for external providers.

Supports GitHub, Google, and other OAuth providers via authlib.
"""
import logging
import json
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session
from app.models.users import User
from app.models.oauth import UserOAuthLink
from app.services.auth.user_service import UserService

logger = logging.getLogger(__name__)


class OAuthService:
    """
    Service for OAuth2 authentication with external providers.
    """
    
    def __init__(self, db: Session, oauth_client: OAuth):
        self.db = db
        self.oauth = oauth_client
    
    async def handle_oauth_callback(
        self,
        provider: str,
        token: Dict[str, Any],
        userinfo: Dict[str, Any],
    ) -> Tuple[User, bool]:
        """
        Handle OAuth callback and create/link user account.
        
        Args:
            provider: OAuth provider name (github, google)
            token: OAuth token response
            userinfo: User info from provider
        
        Returns:
            Tuple of (User, is_new_user)
        """
        # Extract provider-specific user ID
        provider_user_id = self._get_provider_user_id(provider, userinfo)
        provider_email = self._get_provider_email(provider, userinfo)
        provider_username = self._get_provider_username(provider, userinfo)
        
        # Check if this OAuth account is already linked
        oauth_link = self.db.query(UserOAuthLink).filter(
            UserOAuthLink.provider == provider,
            UserOAuthLink.provider_user_id == provider_user_id
        ).first()
        
        if oauth_link:
            # Update existing link
            oauth_link.access_token = token.get("access_token")
            oauth_link.refresh_token = token.get("refresh_token")
            oauth_link.token_expires_at = self._parse_token_expiry(token)
            oauth_link.provider_username = provider_username
            oauth_link.provider_email = provider_email
            oauth_link.profile_data = json.dumps(userinfo)
            oauth_link.last_login_at = datetime.utcnow()
            
            user = oauth_link.user
            is_new = False
            
            logger.info(f"OAuth login: {provider} user {provider_username} -> Unity user {user.username}")
        
        else:
            # Try to find existing user by email
            user = None
            if provider_email:
                user = self.db.query(User).filter(User.email == provider_email).first()
            
            is_new = False
            if not user:
                # Create new user
                user = self._create_user_from_oauth(provider, userinfo, provider_email, provider_username)
                is_new = True
                logger.info(f"Created new user from {provider}: {user.username}")
            else:
                logger.info(f"Linking {provider} account to existing user: {user.username}")
            
            # Create OAuth link
            oauth_link = UserOAuthLink(
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_user_id,
                provider_username=provider_username,
                provider_email=provider_email,
                access_token=token.get("access_token"),
                refresh_token=token.get("refresh_token"),
                token_expires_at=self._parse_token_expiry(token),
                profile_data=json.dumps(userinfo),
                last_login_at=datetime.utcnow()
            )
            self.db.add(oauth_link)
        
        # Update user last login
        user.last_login_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(user)
        
        return user, is_new
    
    def _get_provider_user_id(self, provider: str, userinfo: Dict[str, Any]) -> str:
        """Extract user ID from provider userinfo."""
        if provider == "github":
            return str(userinfo.get("id"))
        elif provider == "google":
            return userinfo.get("sub")  # Google uses 'sub' for user ID
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _get_provider_email(self, provider: str, userinfo: Dict[str, Any]) -> Optional[str]:
        """Extract email from provider userinfo."""
        return userinfo.get("email")
    
    def _get_provider_username(self, provider: str, userinfo: Dict[str, Any]) -> Optional[str]:
        """Extract username from provider userinfo."""
        if provider == "github":
            return userinfo.get("login")
        elif provider == "google":
            return userinfo.get("email", "").split("@")[0]  # Use email prefix as username
        return None
    
    def _parse_token_expiry(self, token: Dict[str, Any]) -> Optional[datetime]:
        """Parse token expiry from OAuth token response."""
        expires_in = token.get("expires_in")
        if expires_in:
            from datetime import timedelta
            return datetime.utcnow() + timedelta(seconds=expires_in)
        return None
    
    def _create_user_from_oauth(
        self,
        provider: str,
        userinfo: Dict[str, Any],
        email: Optional[str],
        username: Optional[str]
    ) -> User:
        """Create a new user account from OAuth provider data."""
        import uuid
        import secrets
        
        # Generate unique username if needed
        base_username = username or email.split("@")[0] if email else f"{provider}_user"
        final_username = base_username
        counter = 1
        
        while self.db.query(User).filter(User.username == final_username).first():
            final_username = f"{base_username}{counter}"
            counter += 1
        
        # Extract full name
        full_name = None
        if provider == "github":
            full_name = userinfo.get("name")
        elif provider == "google":
            full_name = userinfo.get("name")
        
        # Create user with random password (they'll use OAuth to log in)
        user = User(
            username=final_username,
            email=email,
            full_name=full_name,
            hashed_password=secrets.token_urlsafe(32),  # Random password, never used
            role="viewer",  # Default role
            is_active=True,
            is_superuser=False,
        )
        
        self.db.add(user)
        self.db.flush()  # Get the user ID
        
        return user
    
    def get_user_oauth_links(self, user_id: str) -> list[UserOAuthLink]:
        """Get all OAuth links for a user."""
        import uuid
        user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        return self.db.query(UserOAuthLink).filter(
            UserOAuthLink.user_id == user_uuid
        ).all()
    
    def unlink_oauth_provider(self, user_id: str, provider: str) -> bool:
        """Unlink an OAuth provider from a user account."""
        import uuid
        user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        
        link = self.db.query(UserOAuthLink).filter(
            UserOAuthLink.user_id == user_uuid,
            UserOAuthLink.provider == provider
        ).first()
        
        if link:
            self.db.delete(link)
            self.db.commit()
            logger.info(f"Unlinked {provider} from user {user_id}")
            return True
        
        return False


def get_oauth_service(db: Session, oauth_client: OAuth) -> OAuthService:
    """Factory function to get OAuthService instance."""
    return OAuthService(db, oauth_client)
