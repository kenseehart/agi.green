

function error(msg) {
    console.log('error:', msg);
    const messages = document.getElementById('messages');
    const newMessage = document.createElement('div');
    newMessage.className = 'error';
    newMessage.innerHTML = msg;
    messages.appendChild(newMessage);
}

// Function to send messages to the server
function onChatInput() {
    console.log('onChatInput()');
    const inputText = document.getElementById('chat-input-text');
    const message = inputText.value.trim();
    console.log('message:', message);
    if (message !== '') {

        if(socket.readyState === WebSocket.OPEN) {
            send_ws('chat_input', {
                content: message
            });
            inputText.value = '';  // Clear the input field
        } else {
            error('WebSocket is not open');
        }
        console.log('message sent:', message);

        inputText.value = '';  // Clear the input field
        autoResize.call(document.getElementById('chat-input-text'));
    }
}

