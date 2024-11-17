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
        const socket = new WebSocket(ws_host);
        console.log('WebSocket created:', socket);

        const send_ws = (cmd, data = {}) => {
            if (socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({ cmd, ...data }));
                console.log('sending ws:', cmd, data);
            } else {
                console.error('WebSocket is not open');
            }
        };

        // Provide to Vue app
        app.provide('send_ws', send_ws);
        // Also make available globally
        window.send_ws = send_ws;

        socket.onmessage = (event) => {
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

          // Handle open, error, and close events similarly
        socket.onopen = () => emitter.emit('ws_open');
        socket.onerror = (error) => emitter.emit('ws_error', error);
        socket.onclose = () => emitter.emit('ws_close');
    }
};

