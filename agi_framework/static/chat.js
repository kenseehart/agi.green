// Create a connection to the WebSocket server
// Get HTTP protocol (http or https)
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

// Get HTTP host
const host = window.location.hostname;

// Get HTTP port and increment by 1 for WebSocket
const port = parseInt(window.location.port) + 1;

// Create a connection to the WebSocket server
const socket = new WebSocket(`${protocol}//${host}:${port}`);

const md = markdownit({
    // Enable HTML in the markdown source
    html: true,
    linkify: true, // Autoconvert URL-like text to links
    typographer: true, // Enable smart quotes and other typographic substitutions

    // Use highlight.js for syntax highlighting
    highlight: function (str, lang) {
      if (lang && hljs.getLanguage(lang)) {
        try {
            return hljs.highlight(str, {language: lang}).value;
        } catch (__) {}
      }
      return ''; // Use external default escaping
    }
  });


function escapeHtml(text) {
    var map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };

    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
}

// Connection opened
socket.addEventListener('open', (event) => {
    console.log('Connected to WS server');
});

// Listen for messages from server
socket.addEventListener('message', (event) => {
    //print the message to the console
    console.log('Message from server:', event.data);
    //{"cmd": "append_chat", "content": "##hello world.", }

    const msg = JSON.parse(event.data);

    console.log(msg);

    if (msg.cmd === 'append_chat') {
        // Render markdown content
        const renderedHtml = md.render(msg.content);

        // Append to messages
        const messages = document.getElementById('messages');
        const newMessage = document.createElement('div');
        newMessage.innerHTML = renderedHtml;
        messages.appendChild(newMessage);

        // Initialize Mermaid for new elements
        mermaid.init(undefined, newMessage.querySelectorAll('.language-mermaid'));

        // Process MathJax (if necessary)
        window.MathJax.typesetPromise([newMessage]);

        // Scroll to the bottom of the messages
        messages.scrollTop = messages.scrollHeight;
    }

});

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
            socket.send(JSON.stringify({
                cmd: 'chat_input',
                content: message
            }));
            inputText.value = '';  // Clear the input field
        } else {
            error('WebSocket is not open');
        }
        console.log('message sent:', message);

        inputText.value = '';  // Clear the input field
        autoResize.call(document.getElementById('chat-input-text'));
    }
}

socket.onerror = function(event) {
    error(`WebSocket Error: ${event.message}`);
};

socket.onclose = function(event) {
    if (event.wasClean) {
        console.log(`Closed cleanly, code=${event.code}, reason=${event.reason}`);
    } else {
        error('Connection died');
    }
};

function autoResize() {
    this.style.height = 'inherit'; // Briefly shrink textarea to minimal size
    this.style.height = `${this.scrollHeight}px`; // Increase textarea height to its scroll-height
}

document.getElementById('chat-input-text').addEventListener('input', autoResize);
autoResize.call(document.getElementById('chat-input-text'));
