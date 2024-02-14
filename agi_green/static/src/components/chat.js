

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

function on_ws_append_chat(msg) {
    // Get the user's ID and username
    const uid = msg.author;
    var user = userData[uid];

    if (!user) {
        console.log('Unknown user:', uid);
        console.log('Using default');
        user = {
            name: uid,
            icon: '/images/default_avatar.png'
        };
    }

    // Render markdown content
    const renderedHtml = md.render(msg.content);

    // Append to messages
    const messages = document.getElementById('messages');
    const newMessageBlock = document.createElement('div');
    const newMessage = document.createElement('div');
    const avatarImage = document.createElement('img');
    avatarImage.className = 'avatar';
    avatarImage.src = `${user.icon}`;
    avatarImage.alt = `${user.name}'s avatar`;
    avatarImage.title = user.name; // for the mouse-over text

    newMessage.className = 'chat-message';
    newMessage.innerHTML += renderedHtml;
    newMessageBlock.className = 'chat-message-block';
    newMessageBlock.appendChild(avatarImage);
    newMessageBlock.appendChild(newMessage);
    messages.appendChild(newMessageBlock);


    // Initialize Mermaid for new elements
    mermaid.init(undefined, newMessage.querySelectorAll('.language-mermaid'));

    // Process MathJax (if necessary)
    window.MathJax.typesetPromise([newMessage]);

    // Scroll to the bottom of the messages
    messages.scrollTop = messages.scrollHeight;
}


