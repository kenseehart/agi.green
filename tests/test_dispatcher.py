'''
Provides MockDispatcher for test harnesses.
'''

import asyncio
import pytest
from typing import Callable
from agi_green.dispatcher import Dispatcher, Protocol

class MockProtocol(Protocol):
    def __init__(self, protocol_id, returns):
        self.protocol_id = protocol_id
        self.returns = returns

    async def do_send(self, **kwargs):
        if isinstance(self.returns, Callable):
            return self.returns(**kwargs)

        return self.returns

class MockDispatcher(Dispatcher):
    def __init__(self):
        super().__init__()
        self.sent_messages = []

    async def send(self, protocol_id, command, **kwargs):
        """Mock sending a message by recording it."""
        self.sent_messages.append((protocol_id, command, kwargs))
        # Forward to the protocol if it is registered
        protocol = self.registered_protocols.get(protocol_id, None)

        if isinstance(protocol, Protocol):
            return super().send(protocol_id, command, **kwargs)
        else:
            return protocol

    def mock_protocol(self, protocol_id: str, returns):
        """Mock a protocol to return a value."""
        self.registered_protocols[protocol_id] = MockProtocol(returns)

    def mock_receive(self, protocol_id: str, command: str, **kwargs):
        """Simulate receiving a message."""
        protocol = self.registered_protocols.get(protocol_id)
        if protocol:
            handler_name = f"on_{protocol_id}_{command}"
            handler = getattr(protocol, handler_name, None)
            if handler:
                return asyncio.run(handler(**kwargs))
            else:
                raise ValueError(f"No handler named {handler_name} in protocol {protocol_id}")
        else:
            raise ValueError(f"Protocol {protocol_id} not registered with this dispatcher")

class TestProtocol(Protocol):
    protocol_id = "test"

    async def on_test_command(self, data):
        return "Handled"

@pytest.fixture
def dispatcher():
    disp = MockDispatcher()
    protocol = TestProtocol(parent=disp)
    disp.add_protocol(protocol)
    return disp

def test_message_passing(dispatcher):
    asyncio.run(dispatcher.send("test", "command", data="Hello"))
    assert ("test", "command", {"data": "Hello"}) in dispatcher.sent_messages

def test_mock_receive(dispatcher):
    response = dispatcher.mock_receive("test", "command", data="Hello")
    assert response == "Handled"
    
