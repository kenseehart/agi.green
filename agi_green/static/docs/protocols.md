
## Summary of protocols.py

The `protocols.py` file contains several protocol implementations for an async chat room framework. There are four main classes: `WebSocketProtocol`, `HTTPProtocol`, `RabbitMQProtocol`, and `GPTChatProtocol`.

### WebSocketProtocol
- `__init__(self, port:int=8000, **kwargs)`: Initializes the WebSocket server.
- `arun(self)`: Starts the WebSocket server.
- `aclose(self)`: Closes all WebSocket connections.
- `handle_connection(self, websocket, path)`: Registers a WebSocket connection and waits for messages.
- `do_send(self, cmd:str, **kwargs)`: Sends a WebSocket message to the browser.

### HTTPProtocol
- `__init__(self, port:int=8000, **kwargs)`: Initializes the HTTP server.
- `arun(self)`: Starts the HTTP server.
- `aclose(self)`: Stops the HTTP server.
- `handle_get_root_request(self, request)`: Handles GET requests to the root URL.
- `handle_md_request(self, request)`: Handles GET requests for Markdown files.

### RabbitMQProtocol
- `__init__(self, host:str, port:int=5672, **kwargs)`: Initializes the RabbitMQ protocol.
- `arun(self)`: Connects to the RabbitMQ server.
- `aclose(self)`: Closes the RabbitMQ connection.
- `do_send(self, cmd:str, **kwargs)`: Broadcasts a message to RabbitMQ.
- `receive_mq_mesg(self)`: Receives messages from RabbitMQ.

### GPTChatProtocol
- `__init__(self, config:Config, **kwargs)`: Initializes the GPT Chat protocol.
- `arun(self)`: Authenticates the OpenAI client.
- `request_key(self)`: Requests the OpenAI API key from the browser.
- `on_ws_form_data(self, cmd:str, data:dict)`: Handles form data from the browser via WebSocket.
- `on_mq_chat(self, channel_id:str, author:str, content:str)`: Receives chat messages from RabbitMQ.
- `get_completion(self)`: Gets a chat completion from OpenAI.
- `sync_completion(self)`: Synchronously gets a chat completion from OpenAI.

Each protocol class inherits from a base `Protocol` class from `dispatcher.py` to keep a clean and reusable structure.

