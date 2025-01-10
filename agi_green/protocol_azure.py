import logging
from typing import Dict, Any
import aiohttp
from agi_green.dispatcher import Protocol, protocol_handler
import os
from aiohttp import web

logger = logging.getLogger(__name__)

class AzureProtocol(Protocol):
    """
    Azure protocol handler for managing Azure-specific user identification
    """
    protocol_id: str = 'azure'

    def __init__(self, parent: Protocol):
        super().__init__(parent)
        self.azure_user = None
        self.azure_id = None
        self.azure_tenant = None
        self.app_id = os.getenv('AZURE_APPLICATION_ID')
        self.tenant_id = os.getenv('AZURE_TENANT_ID')
        logger.info("AzureProtocol initialized")

    async def get_user_photo(self, access_token: str) -> str:
        """
        Fetch user's photo from Microsoft Graph API
        Returns photo URL or default avatar if unavailable
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {access_token}'}
                url = f'https://graph.microsoft.com/v1.0/me/photo/$value'
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        # Here you'd need to actually save the photo somewhere and return its URL
                        # For now, we'll just return the default
                        return '/avatars/azure.png'
                    else:
                        logger.error(f"Failed to fetch azure user photo: {response.status}")
        except Exception as e:
            logger.error(f"Failed to fetch user photo: {e}")

        return '/avatars/azure.png'

    @protocol_handler
    async def on_ws_connect(self, headers: Dict[str, str]):
        """
        Handle WebSocket connection and extract Azure user information from headers
        """
        self.azure_user = headers.get("X-MS-CLIENT-PRINCIPAL-NAME", None)
        self.azure_id = headers.get("X-MS-CLIENT-PRINCIPAL-ID", None)
        self.azure_tenant = headers.get("X-MS-CLIENT-PRINCIPAL-IDP", None)
        access_token = headers.get("X-MS-TOKEN-AAD-ACCESS-TOKEN", None)

        if self.azure_user and self.azure_id:
            logger.info(f"Azure User Connected - Name: {self.azure_user}, ID: {self.azure_id}, Tenant: {self.azure_tenant}")

            if access_token:
                icon = await self.get_user_photo(access_token)
            else:
                logger.warning("No access token found for Azure user")
                icon = '/avatars/azure.svg'

            await self.send('ws', 'set_user_data',
                            uid=self.azure_id,
                            name=self.azure_user,
                            icon=icon)

    @protocol_handler
    async def on_http_request(self, request_method: str, request_url: str, **kwargs):
        """Extract Azure headers from HTTP request"""
        headers = kwargs.get('headers', {})
        logger.info(f"HTTP Request headers: {headers}")

        # For local development, check if we're running outside Azure
        if not any(key.startswith('X-MS-CLIENT-') for key in headers):
            logger.debug("Running locally - checking for Azure auth endpoints")
            if '/.auth/login/aad' in request_url:
                # Redirect to Azure login
                auth_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"
                params = {
                    'client_id': self.app_id,
                    'response_type': 'code',
                    'redirect_uri': 'http://localhost:8002/.auth/login/done',
                    'response_mode': 'query',
                    'scope': 'openid profile email'
                }
                redirect_url = f"{auth_url}?{'&'.join(f'{k}={v}' for k,v in params.items())}"
                return web.HTTPFound(redirect_url)
            elif '/.auth/login/done' in request_url:
                # Handle OAuth callback
                # This is simplified - in production you'd validate the token
                self.azure_user = "Local Dev User"
                self.azure_id = "local-dev-id"
                self.azure_tenant = self.tenant_id
                return web.HTTPFound('/')

        # Normal Azure App Service header processing
        self.azure_user = headers.get("X-MS-CLIENT-PRINCIPAL-NAME")
        self.azure_id = headers.get("X-MS-CLIENT-PRINCIPAL-ID")
        self.azure_tenant = headers.get("X-MS-CLIENT-PRINCIPAL-IDP")

        if any([self.azure_user, self.azure_id, self.azure_tenant]):
            logger.info(f"Azure headers found - User: {self.azure_user}, ID: {self.azure_id}, Tenant: {self.azure_tenant}")
        else:
            logger.debug("No Azure headers found in HTTP request")

