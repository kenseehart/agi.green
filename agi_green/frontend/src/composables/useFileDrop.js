import { ref, onMounted, onBeforeUnmount } from 'vue';
import { bind_handlers, unbind_handlers } from '@agi.green/emitter';

export function useFileDrop() {
    let dropConfig = null;
    let cleanup = null;

    const handlers = {
        ws_enable_file_drop: (config) => {
            console.log('Enabling file drop with config:', config);
            dropConfig = {
                accept: config.accept || [],
                maxSize: config.max_size || Infinity,
                uploadUrl: config.upload_url,
                multiple: config.multiple || false,
                progressUpdates: config.progress_updates || false
            };

            function handleDrop(e) {
                console.log('Drop event received');
                e.preventDefault();
                e.stopPropagation();

                if (!dropConfig) {
                    console.warn('Drop occurred but no configuration set');
                    return;
                }

                const files = Array.from(e.dataTransfer.files);
                console.log('Files dropped:', files);

                // Process each file
                files.forEach(async (file) => {
                    // Validate file type
                    const ext = '.' + file.name.split('.').pop().toLowerCase();
                    if (!dropConfig.accept.includes(ext)) {
                        console.log('File type not accepted:', ext);
                        return;
                    }

                    // Validate file size
                    if (file.size > dropConfig.maxSize) {
                        console.log('File too large:', file.size);
                        return;
                    }

                    // Create FormData
                    const formData = new FormData();
                    formData.append('file', file);
                    // Use the socket_id from websocketPlugin
                    const socket_id = window.socket_id;  // This is set by websocketPlugin.js
                    if (!socket_id) {
                        console.error('No socket_id available');
                        return;
                    }
                    formData.append('socket_id', socket_id);

                    try {
                        console.log(`Uploading ${file.name} to ${dropConfig.uploadUrl} with socket_id ${socket_id}`);
                        const response = await fetch(dropConfig.uploadUrl, {
                            method: 'POST',
                            body: formData
                        });

                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }

                        console.log(`Upload complete: ${file.name}`);
                    } catch (error) {
                        console.error('Upload failed:', error);
                    }
                });
            }

            function handleDragOver(e) {
                e.preventDefault();
                e.stopPropagation();
            }

            // Add handlers to window (since we want it to work anywhere in these components)
            window.addEventListener('dragover', handleDragOver);
            window.addEventListener('drop', handleDrop);

            // Store cleanup function
            if (cleanup) cleanup();
            cleanup = () => {
                window.removeEventListener('dragover', handleDragOver);
                window.removeEventListener('drop', handleDrop);
            };
        }
    };

    onMounted(() => {
        bind_handlers(handlers);
    });

    onBeforeUnmount(() => {
        if (cleanup) cleanup();
        unbind_handlers(handlers);
    });
}