import { emitter } from '@/emitter'; // Adjust the import path as needed

export default {
    install(app, options) {
        // Dynamically compute the WebSocket URL
        const protocol = window.location.protocol;
        const host = window.location.hostname;
        const port = window.location.port;
        const ws_protocol = protocol === 'https:' ? 'wss:' : 'ws:';
        const ws_host = `${ws_protocol}//${host}:${port}/ws`;

        console.log('ws_host:', ws_host);

        // Initialize WebSocket
        let socket = new WebSocket(ws_host);
        console.log('WebSocket created:', socket);
        let reconnectTimer = null;
        let messageQueue = [];
        let connectionId = null;

        const connect = () => {
            console.log('Connecting WebSocket, current readyState:', socket?.readyState);
            if (socket.readyState === WebSocket.CLOSED) {
                console.log('Attempting to reconnect WebSocket...');
                socket = new WebSocket(ws_host);
                console.log('New WebSocket created:', socket);

                socket.onmessage = onMessage;
                socket.onopen = onOpen;
                socket.onerror = onError;
                socket.onclose = onClose;
            }
        };

        const send_ws = (cmd, data = {}) => {
            console.log('Attempting to send:', cmd, data, 'Socket state:', socket?.readyState);
            if (socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({ cmd, ...data }));
                console.log('sending ws:', cmd, data);
            } else {
                console.log('WebSocket not open, queueing message:', cmd, data);
                messageQueue.push({ cmd, data });
                connect(); // Try to reconnect
            }
        };

        // Provide to Vue app
        app.provide('send_ws', send_ws);
        // Also make available globally
        window.send_ws = send_ws;

        const onMessage = (event) => {
            console.log('WebSocket message received:', event.data);
            const message = JSON.parse(event.data);
            const cmd = message.cmd;
            if (cmd) {
                delete message.cmd;
                console.log('received ws message:', cmd, message);
                emitter.emit('ws_'+cmd, message);
            }
            else {
                console.error('No cmd in ws message:', message);
            }
        };

        const onOpen = () => {
            console.log('WebSocket connected');

            // Get connection ID from response headers if available
            if (socket.headers) {
                connectionId = socket.headers['X-Connection-ID'];
                console.log('Connection ID:', connectionId);
            }

            emitter.emit('ws_open');

            // Clear any reconnect timer
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }

            // Send any queued messages
            while (messageQueue.length > 0) {
                const { cmd, data } = messageQueue.shift();
                send_ws(cmd, data);
            }
        };

        const onError = (error) => {
            console.error('WebSocket error:', error);
            emitter.emit('ws_error', error);
        };

        const onClose = () => {
            console.log('WebSocket closed');
            emitter.emit('ws_close');

            // Schedule reconnect if not already scheduled
            if (!reconnectTimer) {
                reconnectTimer = setTimeout(connect, 2000);
            }
        };

        // Attach event handlers
        socket.onmessage = onMessage;
        socket.onopen = onOpen;
        socket.onerror = onError;
        socket.onclose = onClose;
    }
};

