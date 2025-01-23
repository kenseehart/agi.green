import { emitter } from '@/emitter'; // Adjust the import path as needed

function generateSimpleId() {
    return Math.random().toString(16).substring(2, 10);
}

export default {
    install(app, options) {
        // Dynamically compute the WebSocket URL
        const protocol = window.location.protocol;
        const host = window.location.hostname;
        const port = window.location.port;
        const ws_protocol = protocol === 'https:' ? 'wss:' : 'ws:';
        const ws_host = `${ws_protocol}//${host}:${port}/ws`;

        console.log('ws_host:', ws_host);

        // Simple 8-character random hex string
        const socket_id = generateSimpleId();
        // Make socket_id globally available
        window.socket_id = socket_id;
        console.log('Generated socket_id:', socket_id);

        // Initialize WebSocket with socket_id in URL
        const ws_url = `${ws_host}?socket_id=${socket_id}`;
        let socket = new WebSocket(ws_url);
        console.log('WebSocket created:', socket);
        let reconnectTimer = null;
        let messageQueue = [];

        // Define handlers at module scope so they can be removed
        let dropConfig = null;
        let handleDragOver = null;
        let handleDrop = null;

        const connect = () => {
            console.log('Connecting WebSocket, current readyState:', socket?.readyState);
            if (socket.readyState === WebSocket.CLOSED) {
                console.log('Attempting to reconnect WebSocket...');
                socket = new WebSocket(ws_url);
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
                const message = {
                    cmd,
                    socket_id,  // Include socket_id in all outgoing messages
                    ...data
                };
                socket.send(JSON.stringify(message));
                console.log('sending ws:', cmd, message);
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

        // Add file upload handler using FormData and fetch
        const handleFileUpload = async (file) => {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('socket_id', socket_id);  // Include socket_id for response routing

            try {
                const response = await fetch('/upload/tax', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    throw new Error(`Upload failed: ${response.statusText}`);
                }

                console.log('File uploaded successfully:', file.name);
            } catch (error) {
                console.error('Upload error:', error);
            }
        };

        // Setup drop handlers for the entire window
        window.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
        });

        window.addEventListener('drop', (e) => {
            console.log('Drop event received:', e);
            e.preventDefault();
            e.stopPropagation();

            if (!dropConfig) return;  // Not configured

            const files = Array.from(e.dataTransfer.files);

            // Filter files based on configuration
            const validFiles = files.filter(file => {
                // Check file type
                const ext = '.' + file.name.split('.').pop().toLowerCase();
                if (!dropConfig.accept.includes(ext)) {
                    send_ws('upload_error', {
                        filename: file.name,
                        error: `File type ${ext} not accepted`
                    });
                    return false;
                }

                // Check file size
                if (file.size > dropConfig.maxSize) {
                    send_ws('upload_error', {
                        filename: file.name,
                        error: `File size ${file.size} exceeds limit of ${dropConfig.maxSize}`
                    });
                    return false;
                }

                return true;
            });

            // Respect multiple files setting
            if (!dropConfig.multiple && validFiles.length > 1) {
                send_ws('upload_error', {
                    filename: 'multiple files',
                    error: 'Multiple file upload not allowed'
                });
                return;
            }

            // Process valid files
            validFiles.forEach(file => {
                console.log('Valid file dropped:', file.name);
                // Upload handling will be added in next step
            });
        });

        const handle_ws = {
            enable_file_drop: (data) => {
                console.log('Enabling file drop with config:', data);

                if (!data) {
                    console.warn('No configuration provided to enable_file_drop');
                    return;
                }

                // Remove existing listeners if they exist
                if (handleDragOver) {
                    window.removeEventListener('dragover', handleDragOver);
                    window.removeEventListener('drop', handleDrop);
                }

                // Store configuration
                dropConfig = {
                    accept: data.accept || [],
                    maxSize: data.max_size || Infinity,
                    uploadUrl: data.upload_url,
                    multiple: data.multiple || false,
                    progressUpdates: data.progress_updates || false
                };
                console.log('Drop configuration set:', dropConfig);

                // Define new handlers
                handleDragOver = (e) => {
                    console.log('Drag over event');
                    e.preventDefault();
                    e.stopPropagation();
                };

                handleDrop = async (e) => {
                    console.log('Drop event received');
                    e.preventDefault();
                    e.stopPropagation();

                    if (!dropConfig) {
                        console.warn('Drop occurred but no configuration set');
                        return;
                    }

                    const files = Array.from(e.dataTransfer.files);
                    console.log('Files dropped:', files);

                    // Validate and upload files
                    for (const file of files) {
                        // Check file type
                        const ext = '.' + file.name.split('.').pop().toLowerCase();
                        if (!dropConfig.accept.includes(ext)) {
                            send_ws('upload_error', {
                                filename: file.name,
                                error: `File type ${ext} not accepted`
                            });
                            continue;
                        }

                        // Check file size
                        if (file.size > dropConfig.maxSize) {
                            send_ws('upload_error', {
                                filename: file.name,
                                error: `File size ${file.size} exceeds limit of ${dropConfig.maxSize}`
                            });
                            continue;
                        }

                        try {
                            const formData = new FormData();
                            formData.append('file', file);
                            formData.append('socket_id', socket_id);  // Include socket_id for response routing

                            const xhr = new XMLHttpRequest();

                            // Setup progress tracking
                            if (dropConfig.progressUpdates) {
                                xhr.upload.onprogress = (e) => {
                                    if (e.lengthComputable) {
                                        send_ws('upload_progress', {
                                            filename: file.name,
                                            bytes_sent: e.loaded,
                                            total_bytes: e.total
                                        });
                                    }
                                };
                            }

                            // Setup completion handlers
                            xhr.onload = () => {
                                if (xhr.status === 200) {
                                    send_ws('upload_complete', {
                                        filename: file.name
                                    });
                                } else {
                                    send_ws('upload_error', {
                                        filename: file.name,
                                        error: `Upload failed: ${xhr.statusText}`
                                    });
                                }
                            };

                            xhr.onerror = () => {
                                send_ws('upload_error', {
                                    filename: file.name,
                                    error: 'Upload failed: Network error'
                                });
                            };

                            // Start upload
                            console.log(`Uploading ${file.name} to ${dropConfig.uploadUrl}`);
                            xhr.open('POST', dropConfig.uploadUrl);
                            xhr.send(formData);

                        } catch (error) {
                            console.error('Upload error:', error);
                            send_ws('upload_error', {
                                filename: file.name,
                                error: `Upload failed: ${error.message}`
                            });
                        }
                    }
                };

                // Add the new listeners
                window.addEventListener('dragover', handleDragOver);
                window.addEventListener('drop', handleDrop);
                console.log('Drop handlers installed');
            },
        };
    }
};

