"""
Browser-based OAuth Authentication for MCP Tools

Simplifies OAuth flows using the browser for user authorization.
"""

import asyncio
import secrets
import webbrowser
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Callable
from urllib.parse import urlencode, parse_qs, urlparse
import json

import aiohttp
from aiohttp import web
import structlog

from .models import ToolConfig, AuthType
from .auth import AuthToken

logger = structlog.get_logger()


class BrowserAuthServer:
    """Local server for handling OAuth callbacks."""
    
    def __init__(self, port: int = 8080):
        """Initialize the browser auth server."""
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        
        # OAuth state management
        self.pending_states: Dict[str, Dict[str, Any]] = {}
        self.completion_callbacks: Dict[str, Callable] = {}
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup HTTP routes for OAuth callbacks."""
        self.app.router.add_get('/oauth/callback', self._oauth_callback)
        self.app.router.add_get('/oauth/success', self._oauth_success)
        self.app.router.add_get('/oauth/error', self._oauth_error)
    
    async def start(self):
        """Start the local server."""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, 'localhost', self.port)
            await self.site.start()
            
            logger.info("Browser auth server started", port=self.port)
            return True
            
        except Exception as e:
            logger.error("Failed to start browser auth server", error=str(e))
            return False
    
    async def stop(self):
        """Stop the local server."""
        try:
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()
            
            logger.info("Browser auth server stopped")
            
        except Exception as e:
            logger.error("Error stopping browser auth server", error=str(e))
    
    async def _oauth_callback(self, request):
        """Handle OAuth callback from provider."""
        try:
            query_params = dict(request.query)
            state = query_params.get('state')
            
            if not state or state not in self.pending_states:
                return web.Response(
                    text="Invalid OAuth state",
                    status=400
                )
            
            # Get pending OAuth data
            oauth_data = self.pending_states[state]
            tool_id = oauth_data['tool_id']
            
            # Check for errors
            if 'error' in query_params:
                error_description = query_params.get('error_description', 'Unknown error')
                
                # Call completion callback with error
                if state in self.completion_callbacks:
                    await self.completion_callbacks[state]({
                        'success': False,
                        'error': error_description
                    })
                
                # Redirect to error page
                return web.Response(
                    status=302,
                    headers={'Location': f'/oauth/error?error={error_description}'}
                )
            
            # Get authorization code
            auth_code = query_params.get('code')
            if not auth_code:
                return web.Response(
                    text="No authorization code received",
                    status=400
                )
            
            # Exchange code for token
            token_result = await self._exchange_code_for_token(
                oauth_data, auth_code
            )
            
            # Call completion callback
            if state in self.completion_callbacks:
                await self.completion_callbacks[state](token_result)
            
            # Clean up
            del self.pending_states[state]
            if state in self.completion_callbacks:
                del self.completion_callbacks[state]
            
            if token_result['success']:
                # Redirect to success page
                return web.Response(
                    status=302,
                    headers={'Location': f'/oauth/success?tool={tool_id}'}
                )
            else:
                # Redirect to error page
                return web.Response(
                    status=302,
                    headers={'Location': f'/oauth/error?error={token_result.get("error", "Token exchange failed")}'}
                )
                
        except Exception as e:
            logger.error("OAuth callback error", error=str(e))
            return web.Response(
                text=f"OAuth callback error: {str(e)}",
                status=500
            )
    
    async def _oauth_success(self, request):
        """Show OAuth success page."""
        tool_name = request.query.get('tool', 'Tool')
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Success</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }}
                .container {{
                    text-align: center;
                    background: white;
                    color: #333;
                    padding: 2rem;
                    border-radius: 10px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                    max-width: 400px;
                }}
                .success-icon {{
                    font-size: 3rem;
                    margin-bottom: 1rem;
                }}
                .close-btn {{
                    margin-top: 1rem;
                    padding: 0.5rem 1rem;
                    background: #28a745;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 1rem;
                }}
                .close-btn:hover {{
                    background: #218838;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">✅</div>
                <h1>Authentication Successful!</h1>
                <p><strong>{tool_name}</strong> has been connected to your MCP ADHD Server.</p>
                <p>You can now close this window and return to your application.</p>
                <button class="close-btn" onclick="window.close()">Close Window</button>
            </div>
            <script>
                // Auto-close after 5 seconds
                setTimeout(() => {{
                    window.close();
                }}, 5000);
            </script>
        </body>
        </html>
        """
        
        return web.Response(text=html, content_type='text/html')
    
    async def _oauth_error(self, request):
        """Show OAuth error page."""
        error = request.query.get('error', 'Unknown error occurred')
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Error</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #ff7b7b 0%, #d63384 100%);
                    color: white;
                }}
                .container {{
                    text-align: center;
                    background: white;
                    color: #333;
                    padding: 2rem;
                    border-radius: 10px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                    max-width: 400px;
                }}
                .error-icon {{
                    font-size: 3rem;
                    margin-bottom: 1rem;
                }}
                .retry-btn {{
                    margin-top: 1rem;
                    padding: 0.5rem 1rem;
                    background: #dc3545;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 1rem;
                }}
                .retry-btn:hover {{
                    background: #c82333;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error-icon">❌</div>
                <h1>Authentication Failed</h1>
                <p><strong>Error:</strong> {error}</p>
                <p>Please try again or check your settings.</p>
                <button class="retry-btn" onclick="window.close()">Close Window</button>
            </div>
        </body>
        </html>
        """
        
        return web.Response(text=html, content_type='text/html')
    
    async def _exchange_code_for_token(
        self,
        oauth_data: Dict[str, Any],
        auth_code: str
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        try:
            config = oauth_data['config']
            
            # Prepare token request
            token_data = {
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': f"http://localhost:{self.port}/oauth/callback",
                'client_id': config['client_id'],
                'client_secret': config['client_secret']
            }
            
            # Add scope if specified
            if 'scope' in config:
                token_data['scope'] = config['scope']
            
            # Make token request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    config['token_url'],
                    data=token_data,
                    headers={'Accept': 'application/json'}
                ) as response:
                    
                    if response.status == 200:
                        token_response = await response.json()
                        
                        # Calculate expiry
                        expires_in = token_response.get('expires_in', 3600)
                        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                        
                        return {
                            'success': True,
                            'access_token': token_response.get('access_token'),
                            'refresh_token': token_response.get('refresh_token'),
                            'expires_at': expires_at,
                            'token_type': token_response.get('token_type', 'Bearer'),
                            'scope': token_response.get('scope')
                        }
                    else:
                        error_text = await response.text()
                        return {
                            'success': False,
                            'error': f"Token exchange failed: {error_text}"
                        }
            
        except Exception as e:
            logger.error("Token exchange error", error=str(e))
            return {
                'success': False,
                'error': f"Token exchange error: {str(e)}"
            }
    
    def register_oauth_flow(
        self,
        tool_id: str,
        config: Dict[str, Any],
        callback: Callable
    ) -> str:
        """Register an OAuth flow and return state token."""
        state = secrets.token_urlsafe(32)
        
        self.pending_states[state] = {
            'tool_id': tool_id,
            'config': config,
            'created_at': datetime.utcnow()
        }
        
        self.completion_callbacks[state] = callback
        
        return state


class BrowserAuth:
    """Browser-based authentication manager for MCP tools."""
    
    def __init__(self):
        """Initialize browser auth manager."""
        self.server = BrowserAuthServer()
        self.tokens: Dict[str, AuthToken] = {}
        
    async def initialize(self):
        """Initialize the browser auth system."""
        success = await self.server.start()
        if success:
            logger.info("Browser auth system initialized")
        return success
    
    async def close(self):
        """Close the browser auth system."""
        await self.server.stop()
    
    async def authenticate_tool(
        self,
        tool_config: ToolConfig,
        oauth_config: Dict[str, Any]
    ) -> bool:
        """Authenticate a tool using browser OAuth flow."""
        try:
            if tool_config.auth_type != AuthType.OAUTH2:
                logger.error("Browser auth only supports OAuth2", 
                           tool_id=tool_config.tool_id)
                return False
            
            # Create completion event
            auth_complete = asyncio.Event()
            auth_result = {}
            
            async def completion_callback(result):
                auth_result.update(result)
                auth_complete.set()
            
            # Register OAuth flow
            state = self.server.register_oauth_flow(
                tool_id=tool_config.tool_id,
                config=oauth_config,
                callback=completion_callback
            )
            
            # Build authorization URL
            auth_url = self._build_auth_url(oauth_config, state)
            
            logger.info("Opening browser for OAuth authentication", 
                       tool_id=tool_config.tool_id)
            
            # Open browser
            webbrowser.open(auth_url)
            
            # Wait for completion (with timeout)
            try:
                await asyncio.wait_for(auth_complete.wait(), timeout=300)  # 5 minutes
            except asyncio.TimeoutError:
                logger.error("OAuth authentication timed out", 
                           tool_id=tool_config.tool_id)
                return False
            
            # Check result
            if auth_result.get('success'):
                # Store token
                token = AuthToken(
                    tool_id=tool_config.tool_id,
                    auth_type=AuthType.OAUTH2,
                    access_token=auth_result['access_token'],
                    refresh_token=auth_result.get('refresh_token'),
                    expires_at=auth_result['expires_at'],
                    token_type=auth_result.get('token_type', 'Bearer'),
                    scope=auth_result.get('scope')
                )
                
                self.tokens[tool_config.tool_id] = token
                
                logger.info("Browser OAuth authentication successful", 
                           tool_id=tool_config.tool_id)
                return True
            else:
                logger.error("Browser OAuth authentication failed", 
                           tool_id=tool_config.tool_id,
                           error=auth_result.get('error'))
                return False
                
        except Exception as e:
            logger.error("Browser authentication error", 
                        tool_id=tool_config.tool_id,
                        error=str(e))
            return False
    
    def get_auth_headers(self, tool_id: str) -> Dict[str, str]:
        """Get authentication headers for a tool."""
        token = self.tokens.get(tool_id)
        if token and not token.is_expired():
            return {
                'Authorization': f"{token.token_type} {token.access_token}"
            }
        return {}
    
    def is_tool_authenticated(self, tool_id: str) -> bool:
        """Check if a tool is authenticated."""
        token = self.tokens.get(tool_id)
        return token is not None and not token.is_expired()
    
    def _build_auth_url(self, config: Dict[str, Any], state: str) -> str:
        """Build OAuth authorization URL."""
        params = {
            'client_id': config['client_id'],
            'response_type': 'code',
            'redirect_uri': f"http://localhost:{self.server.port}/oauth/callback",
            'state': state,
            'access_type': 'offline'  # Request refresh token
        }
        
        if 'scope' in config:
            params['scope'] = config['scope']
        
        return f"{config['authorization_url']}?{urlencode(params)}"


# Pre-configured OAuth configs for popular services
OAUTH_CONFIGS = {
    'gmail': {
        'client_id': '',  # To be filled by user
        'client_secret': '',  # To be filled by user
        'authorization_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'scope': 'https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/gmail.send'
    },
    'google_calendar': {
        'client_id': '',  # To be filled by user
        'client_secret': '',  # To be filled by user
        'authorization_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'scope': 'https://www.googleapis.com/auth/calendar'
    },
    'github': {
        'client_id': '',  # To be filled by user
        'client_secret': '',  # To be filled by user
        'authorization_url': 'https://github.com/login/oauth/authorize',
        'token_url': 'https://github.com/login/oauth/access_token',
        'scope': 'repo user'
    },
    'slack': {
        'client_id': '',  # To be filled by user
        'client_secret': '',  # To be filled by user
        'authorization_url': 'https://slack.com/oauth/v2/authorize',
        'token_url': 'https://slack.com/api/oauth.v2.access',
        'scope': 'channels:read chat:write'
    },
    'google_nest': {
        'client_id': '',  # To be filled by user
        'client_secret': '',  # To be filled by user
        'authorization_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'scope': 'https://www.googleapis.com/auth/sdm.service'
    },
    'nest': {  # Alias for google_nest
        'client_id': '',  # To be filled by user
        'client_secret': '',  # To be filled by user
        'authorization_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'scope': 'https://www.googleapis.com/auth/sdm.service'
    }
}