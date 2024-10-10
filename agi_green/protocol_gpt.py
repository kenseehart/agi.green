import os
from os.path import join, dirname, splitext, isabs
from typing import Callable, Awaitable, Dict, Any, List, Set, Union, Tuple
from logging import getLogger, Logger
import asyncio
import logging

from aiohttp import web, WSMsgType
from openai import OpenAI

from agi_green.dispatcher import Protocol, format_call, protocol_handler

here = dirname(__file__)
logger = logging.getLogger(__name__)
log_level = os.getenv('LOG_LEVEL', 'WARNING').upper()
logging.basicConfig(level=log_level)

class GPTChatProtocol(Protocol):
    '''
    OpenAI GPT Chat protocol

    This is just a POC: simple async wrapper around the OpenAI API in chat mode.
    Next step is to implement HuggingFace transformers and langchain for more control.
    '''
    protocol_id: str = 'gpt'

    _openai_client: OpenAI = None

    def __init__(self, parent:Protocol):
        super().__init__(parent)
        self.name = 'agi.green'
        self.uid = 'bot'

    @property
    def openai_client(self):
        if GPTChatProtocol._openai_client is None:
            api_key = os.environ.get("OPENAI_API_KEY", None)

            if api_key is None:
                raise Exception("gpt protocol needs OPENAI_API_KEY environment variable to be set")

            GPTChatProtocol._openai_client = OpenAI(api_key=api_key)

        return GPTChatProtocol._openai_client

    async def run(self):
        self.add_task(super().run())

        self.messages = [
            {"role": "system", "content": "You are a helpful assistant."},
        ]

    @protocol_handler
    async def on_ws_form_data(self, cmd:str, data:dict):
        key = data.get('key')
        self.config.set('openai.key', key)
        self.messages.append({"role": "system", "content": "OpenAI API key was just now set by the user."})
        await self.get_completion()

    @protocol_handler
    async def on_ws_connect(self):
        await self.send('ws', 'set_user_data', uid='bot', name='GPT-4', icon='/avatars/agibot.png')
        await self.send('ws', 'set_user_data', uid='info', name='InfoBot', icon='/avatars/infobot.png')

    @protocol_handler
    async def on_mq_chat(self, channel_id:str, author:str, content:str):
        'receive chat message from RabbitMQ'
        if author != self.uid:
            self.messages.append({"role": "user", "content": content})
            task = asyncio.create_task(self.get_completion())

    async def get_completion(self):
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, self.sync_completion)
        if content:
            await self.send('mq', 'chat', channel='chat.public', author=self.uid, content=content)

    def sync_completion(self):
        try:
            # if env DISABLE_GPT4 is set, skip GPT4 completion
            if os.environ.get('DISABLE_GPT', None):
                logger.info('skipping GPT completion')
            else:
                response = self.openai_client.chat.completions.create(model="gpt-4",
                messages=self.messages)
                return response.choices[0].message.content
        except Exception as e:
            msg = f'protocol_gpt: OpenAI API error: {e}'
            logger.error(msg)
            return f'<span style="color:red">{msg}</span>'

