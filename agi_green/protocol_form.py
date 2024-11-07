
from agi_green.dispatcher import Protocol, protocol_handler
import logging
import os

logger = logging.getLogger(__name__)
log_level = os.getenv('LOG_LEVEL', 'WARNING').upper()
logging.basicConfig(level=log_level)


class FormProtocol(Protocol):
    protocol_id = "form"

    @protocol_handler
    async def on_http_vueform_process(self, form_id: str, **kwargs) -> str:
        logger.info(f"vueform_process {form_id}: {kwargs}")
        await self.handle_mesg(form_id, **kwargs)
        return "OK"
