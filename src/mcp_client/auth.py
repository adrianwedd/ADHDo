"""
MCP Authentication Manager

Handles authentication for various tool integrations.
"""

import base64
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import uuid

import structlog
from pydantic import BaseModel

from .models import ToolConfig, AuthType

logger = structlog.get_logger()


class AuthToken(BaseModel):
    """Authentication token for a tool."""
    tool_id: str
    auth_type: AuthType
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    token_type: str = "Bearer"
    scope: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() >= self.expires_at
    
    def needs_refresh(self) -> bool:
        """Check if token needs refresh (within 5 minutes of expiry)."""
        if not self.expires_at:
            return False
        return datetime.utcnow() >= (self.expires_at - timedelta(minutes=5))


class OAuth2Config(BaseModel):
    """OAuth 2.0 configuration for a tool."""
    client_id: str
    client_secret: str
    authorization_url: str
    token_url: str
    redirect_uri: Optional[str] = None
    scope: Optional[str] = None


class AuthManager:
    """Manages authentication for MCP tools."""
    
    def __init__(self):
        """Initialize the authentication manager."""
        self.tokens: Dict[str, AuthToken] = {}
        self.oauth_configs: Dict[str, OAuth2Config] = {}
        self.api_keys: Dict[str, str] = {}
        
        # Default redirect URI for OAuth flows
        self.default_redirect_uri = "http://localhost:8000/mcp/oauth/callback"
    
    async def initialize(self):
        """Initialize the auth manager."""
        # Load saved tokens and configs
        await self._load_auth_data()
        logger.info("Auth manager initialized")
    
    async def authenticate_tool(self, tool_config: ToolConfig) -> bool:
        """Authenticate a tool based on its configuration."""
        try:
            tool_id = tool_config.tool_id
            auth_type = tool_config.auth_type
            
            if auth_type == AuthType.API_KEY:
                return await self._authenticate_api_key(tool_config)
            elif auth_type == AuthType.OAUTH2:
                return await self._authenticate_oauth2(tool_config)
            elif auth_type == AuthType.BEARER:
                return await self._authenticate_bearer(tool_config)
            elif auth_type == AuthType.BASIC:
                return await self._authenticate_basic(tool_config)
            else:
                logger.warning("Unsupported auth type", tool_id=tool_id, auth_type=auth_type)
                return False
                
        except Exception as e:
            logger.error("Tool authentication failed", 
                        tool_id=tool_config.tool_id, 
                        error=str(e))
            return False
    
    async def get_auth_headers(self, tool_config: ToolConfig) -> Dict[str, str]:
        """Get authentication headers for a tool."""
        headers = {}
        tool_id = tool_config.tool_id
        auth_type = tool_config.auth_type
        
        try:
            if auth_type == AuthType.API_KEY:
                api_key = self.api_keys.get(tool_id)
                if api_key:
                    # Different APIs use different header formats
                    auth_config = tool_config.auth_config
                    header_name = auth_config.get('header_name', 'X-API-Key')
                    headers[header_name] = api_key
            
            elif auth_type == AuthType.OAUTH2:
                token = self.tokens.get(tool_id)
                if token and not token.is_expired():
                    headers['Authorization'] = f"{token.token_type} {token.access_token}"
                elif token and token.needs_refresh():
                    # Try to refresh token
                    if await self._refresh_oauth2_token(tool_id):
                        token = self.tokens[tool_id]
                        headers['Authorization'] = f"{token.token_type} {token.access_token}"
            
            elif auth_type == AuthType.BEARER:
                token = tool_config.auth_config.get('token')
                if token:
                    headers['Authorization'] = f"Bearer {token}"
            
            elif auth_type == AuthType.BASIC:
                username = tool_config.auth_config.get('username')
                password = tool_config.auth_config.get('password')
                if username and password:
                    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                    headers['Authorization'] = f"Basic {credentials}"
            
            return headers
            
        except Exception as e:
            logger.error("Failed to get auth headers", tool_id=tool_id, error=str(e))
            return {}
    
    # OAuth 2.0 Methods
    
    def register_oauth2_config(self, tool_id: str, config: OAuth2Config):
        """Register OAuth 2.0 configuration for a tool."""
        self.oauth_configs[tool_id] = config
        logger.info("OAuth2 config registered", tool_id=tool_id)
    
    def get_oauth2_auth_url(self, tool_id: str, state: Optional[str] = None) -> Optional[str]:
        """Get OAuth 2.0 authorization URL for a tool."""
        config = self.oauth_configs.get(tool_id)
        if not config:
            return None
        
        if not state:
            state = secrets.token_urlsafe(32)
        
        params = {
            'client_id': config.client_id,
            'response_type': 'code',
            'redirect_uri': config.redirect_uri or self.default_redirect_uri,
            'state': state
        }
        
        if config.scope:
            params['scope'] = config.scope
        
        # Build URL
        param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        auth_url = f"{config.authorization_url}?{param_string}"
        
        logger.info("Generated OAuth2 auth URL", tool_id=tool_id)
        return auth_url
    
    async def handle_oauth2_callback(
        self, 
        tool_id: str, 
        code: str, 
        state: str
    ) -> bool:
        """Handle OAuth 2.0 callback and exchange code for token."""
        try:
            config = self.oauth_configs.get(tool_id)
            if not config:
                logger.error("No OAuth2 config found", tool_id=tool_id)
                return False
            
            # Exchange code for token
            token_data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': config.redirect_uri or self.default_redirect_uri,
                'client_id': config.client_id,
                'client_secret': config.client_secret
            }
            
            # This would make an HTTP request to the token endpoint
            # For now, we'll simulate successful token exchange
            
            # Create token
            token = AuthToken(
                tool_id=tool_id,
                auth_type=AuthType.OAUTH2,
                access_token=f"oauth_token_{secrets.token_urlsafe(32)}",
                refresh_token=f"refresh_token_{secrets.token_urlsafe(32)}",
                expires_at=datetime.utcnow() + timedelta(hours=1),
                token_type="Bearer"
            )
            
            self.tokens[tool_id] = token
            
            # Save to persistent storage
            await self._save_auth_data()
            
            logger.info("OAuth2 token obtained", tool_id=tool_id)
            return True
            
        except Exception as e:
            logger.error("OAuth2 callback handling failed", tool_id=tool_id, error=str(e))
            return False
    
    # API Key Methods
    
    def set_api_key(self, tool_id: str, api_key: str):
        """Set API key for a tool."""
        self.api_keys[tool_id] = api_key
        logger.info("API key set", tool_id=tool_id)
    
    def get_api_key(self, tool_id: str) -> Optional[str]:
        """Get API key for a tool."""
        return self.api_keys.get(tool_id)
    
    # Token Management
    
    def revoke_token(self, tool_id: str) -> bool:
        """Revoke authentication token for a tool."""
        try:
            if tool_id in self.tokens:
                del self.tokens[tool_id]
            
            if tool_id in self.api_keys:
                del self.api_keys[tool_id]
            
            logger.info("Token revoked", tool_id=tool_id)
            return True
            
        except Exception as e:
            logger.error("Token revocation failed", tool_id=tool_id, error=str(e))
            return False
    
    def is_tool_authenticated(self, tool_id: str) -> bool:
        """Check if a tool is authenticated."""
        # Check OAuth2 token
        if tool_id in self.tokens:
            token = self.tokens[tool_id]
            if not token.is_expired():
                return True
        
        # Check API key
        if tool_id in self.api_keys:
            return True
        
        return False
    
    def get_auth_status(self, tool_id: str) -> Dict[str, Any]:
        """Get authentication status for a tool."""
        status = {
            'tool_id': tool_id,
            'authenticated': False,
            'auth_type': None,
            'expires_at': None,
            'needs_refresh': False
        }
        
        if tool_id in self.tokens:
            token = self.tokens[tool_id]
            status.update({
                'authenticated': not token.is_expired(),
                'auth_type': token.auth_type.value,
                'expires_at': token.expires_at.isoformat() if token.expires_at else None,
                'needs_refresh': token.needs_refresh()
            })
        elif tool_id in self.api_keys:
            status.update({
                'authenticated': True,
                'auth_type': 'api_key'
            })
        
        return status
    
    # Private Methods
    
    async def _authenticate_api_key(self, tool_config: ToolConfig) -> bool:
        """Authenticate using API key."""
        tool_id = tool_config.tool_id
        api_key = tool_config.auth_config.get('api_key')
        
        if api_key:
            self.api_keys[tool_id] = api_key
            return True
        
        # Check if already stored
        return tool_id in self.api_keys
    
    async def _authenticate_oauth2(self, tool_config: ToolConfig) -> bool:
        """Authenticate using OAuth 2.0."""
        tool_id = tool_config.tool_id
        
        # Check if we already have a valid token
        if tool_id in self.tokens:
            token = self.tokens[tool_id]
            if not token.is_expired():
                return True
            
            # Try to refresh if possible
            if token.refresh_token:
                return await self._refresh_oauth2_token(tool_id)
        
        # Need to start OAuth flow
        logger.info("OAuth2 authentication required", tool_id=tool_id)
        return False
    
    async def _authenticate_bearer(self, tool_config: ToolConfig) -> bool:
        """Authenticate using Bearer token."""
        token = tool_config.auth_config.get('token')
        return bool(token)
    
    async def _authenticate_basic(self, tool_config: ToolConfig) -> bool:
        """Authenticate using Basic auth."""
        username = tool_config.auth_config.get('username')
        password = tool_config.auth_config.get('password')
        return bool(username and password)
    
    async def _refresh_oauth2_token(self, tool_id: str) -> bool:
        """Refresh an OAuth 2.0 token."""
        try:
            token = self.tokens.get(tool_id)
            config = self.oauth_configs.get(tool_id)
            
            if not token or not config or not token.refresh_token:
                return False
            
            # This would make an HTTP request to refresh the token
            # For now, simulate successful refresh
            
            # Create new token
            new_token = AuthToken(
                tool_id=tool_id,
                auth_type=AuthType.OAUTH2,
                access_token=f"oauth_token_{secrets.token_urlsafe(32)}",
                refresh_token=token.refresh_token,  # May get new refresh token
                expires_at=datetime.utcnow() + timedelta(hours=1),
                token_type="Bearer"
            )
            
            self.tokens[tool_id] = new_token
            
            # Save to persistent storage
            await self._save_auth_data()
            
            logger.info("OAuth2 token refreshed", tool_id=tool_id)
            return True
            
        except Exception as e:
            logger.error("Token refresh failed", tool_id=tool_id, error=str(e))
            return False
    
    async def _load_auth_data(self):
        """Load authentication data from storage."""
        # This would load from encrypted storage in a real implementation
        # For now, we'll start with empty state
        logger.debug("Auth data loaded")
    
    async def _save_auth_data(self):
        """Save authentication data to storage."""
        # This would save to encrypted storage in a real implementation
        logger.debug("Auth data saved")