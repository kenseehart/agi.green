import logging
from typing import Dict, Any
import aiohttp
from agi_green.dispatcher import Protocol, protocol_handler

logger = logging.getLogger(__name__)

class AzureProtocol(Protocol):
    """
    Azure protocol handler for managing Azure-specific user identification
    """
    protocol_id: str = 'azure'

    def __init__(self, parent: Protocol):
        super().__init__(parent)
        self.azure_user = "Unknown User"
        self.azure_id = "Unknown ID"

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
        access_token = headers.get("X-MS-TOKEN-AAD-ACCESS-TOKEN", None)

        if self.azure_user and self.azure_id:
            logger.info(f"Azure User Connected - Name: {self.azure_user}, ID: {self.azure_id}")
            
            if access_token:
                icon = await self.get_user_photo(access_token)
            else:
                logger.warning("No access token found for Azure user")
                icon = '/avatars/azure.svg'

            await self.send('ws', 'set_user_data', 
                            uid=self.azure_id, 
                            name=self.azure_user, 
                            icon=icon)

