# AGI.green Framework

A modern Python framework for building AI-powered asynchonous chat applications with a browser interface, featuring markdown content rendering and a unified messaging system.

Application can be built entirely in Python or can integrate with arbitrary external services.
This differs from conventional full stack solutions with a javascript frontend application making API calls to a Python backend.
Instead, the frontend is a slave and the backend is the application.

## Features

- **Unified Message Protocol**: Consistent message handling across different communication channels
- **Rich Content Support**: 
  - Markdown rendering
  - Mermaid diagrams
  - MathJax equations
  - Code syntax highlighting
- **Flexible Architecture**:
  - WebSocket-based real-time communication
  - AMQP integration for distributed systems
  - Extensible protocol system
- **AI Integration**:
  - OpenAI API support
  - Anthropic Claude support
  - Custom model integration capability
- **Asynchronous Execution**:
  - Non limited to call and response
  - Can add chat messages in response to arbitrary events, e.g. incoming email or SMS or task completion
  - Can execute arbitrary code in response to a message or other events

## Quick Start

1. Install dependencies:
```bash
# Install RabbitMQ
sudo apt-get install rabbitmq-server  # Ubuntu/Debian
brew install rabbitmq                 # macOS

# Install package
pip install agi.green
```

2. Create a basic chat application:
```python
from agi_green.dispatcher import Dispatcher

class ChatNode(Dispatcher):
    async def on_mq_chat(self, author: str, content: str):
        'Receive chat message from RabbitMQ'
        await self.send_ws('append_chat', content=content)

    async def on_ws_chat_input(self, content: str = ''):
        'Handle chat input from browser'
        await self.send_mq('chat', 
            author=self.name,
            content=content
        )
```

## Protocol System

The framework uses a protocol-based architecture where each protocol handles specific types of communication:

- `ws`: WebSocket communication with browser
- `mq`: RabbitMQ for peer-to-peer messaging
- `gpt`: OpenAI API integration
- `http`: HTTP/HTTPS server
- Custom protocols can be added by extending the base Protocol class

## Message Formatting

Support for rich content in messages:
```python
# Markdown with syntax highlighting
await self.send_ws('append_chat',
    content='```python\nprint("Hello")\n```'
)

# Mermaid diagrams
await self.send_ws('append_chat',
    content='```mermaid\ngraph TD;\nA-->B;\n```'
)

# Math equations
await self.send_ws('append_chat',
    content=r'\\( \int x dx = \frac{x^2}{2} + C \\)'
)
```

## Development Status

Currently in active development (March 2024). The framework is being used in production but the API may have breaking changes.

## Requirements

- Python 3.11+
- RabbitMQ server
- Modern web browser

## Contributing

Contributions are welcome! Please check our [Contributing Guidelines](CONTRIBUTING.md) for details.

## License

Copyright (c) 2024 Ken Seehart, AGI Green. See [LICENSE](LICENSE) for details.
