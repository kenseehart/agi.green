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
        "'": '&#039;',
        '\n': '<br>',
    };

    return text.replace(/[&<>"'\n]/g, function(m) { return map[m]; });
}

// Connection opened
socket.addEventListener('open', (event) => {
    console.log('Connected to WS server');
    onWSConnected();
});

let userData = {};
let wsHandlers = {};

function wsRegisterHandlers(handlers) {
    wsHandlers = { ...wsHandlers, ...handlers };
}

function setTextWithNewlines(element, text) {
    // First clear the current content
    element.innerHTML = '';

    // Split the text by newlines
    let lines = text.split('\n');

    // For each line, append a text node and a <br/> element
    for(let i = 0; i < lines.length; i++) {
        element.appendChild(document.createTextNode(lines[i]));

        // Add a <br/> for each line except the last one
        if(i !== lines.length - 1) {
            element.appendChild(document.createElement('br'));
        }
    }
}

wsRegisterHandlers({
    'set_user_data': function(msg) {
        // Set the user's ID and username
        userData[msg.uid] = msg;
        console.log('userData:', userData);
    },

    'append_chat': function(msg) {
        // Get the user's ID and username
        const uid = msg.author;
        const user = userData[uid];

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
    },

    'update_md_content': function(msg) {
        // Update the markdown content
        const mdSource = document.getElementById('md-source');
        setTextWithNewlines(mdSource, msg.content);
        autoResize.call(mdSource);
        const renderedContent = md.render(msg.content)
        const mdRendered = document.getElementById('md-render');
        mdRendered.innerHTML = renderedContent;
        autoResize.call(mdRendered);
        mermaid.init(undefined, mdRendered.querySelectorAll('.language-mermaid'));
        window.MathJax.typesetPromise([mdRendered]);

        if (msg.format === 'source') {
            showSource();
        }
        else {
            showRendered();
        }
    }
});

// Listen for messages from server
socket.addEventListener('message', (event) => {
    let msg;
    try {
        msg = JSON.parse(event.data);
    } catch (e) {
        console.log('Error parsing JSON in ws message:', e);
        console.log('ws message:', event.data);
        return;
    }

    console.log('received ws message:', msg);

    if (msg.cmd in wsHandlers) {
        wsHandlers[msg.cmd](msg);
    } else {
        console.log('Unknown command:', msg.cmd);
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

chatInputText = document.getElementById('chat-input-text')
if (chatInputText) {
    chatInputText.addEventListener('input', autoResize);
    autoResize.call(document.getElementById('chat-input-text'));
}

// Toggle between showing the rendered markdown and the markdown source
function showSource() {
    console.log('showSource()');
    var sourceButton = document.getElementById('source-button');
    var renderButton = document.getElementById('render-button');

    document.getElementById('md-render').style.display = 'none';
    document.getElementById('md-source').style.display = 'block';

    sourceButton.classList.add('button-selected');
    sourceButton.classList.remove('button-unselected');

    renderButton.classList.add('button-unselected');
    renderButton.classList.remove('button-selected');
}

function showRendered() {
    console.log('showRendered()');
    var sourceButton = document.getElementById('source-button');
    var renderButton = document.getElementById('render-button');

    document.getElementById('md-render').style.display = 'block';
    document.getElementById('md-source').style.display = 'none';

    renderButton.classList.add('button-selected');
    renderButton.classList.remove('button-unselected');

    sourceButton.classList.add('button-unselected');
    sourceButton.classList.remove('button-selected');
}

function onWSConnected() {
    if (document.getElementById('md-source')) {

        showRendered();

        console.log('requesting md content cmd');

        socket.send(JSON.stringify({ 'cmd': 'request_md_content' }));
    }
}

const vsplitter = document.getElementById('vsplitter');
if (vsplitter) {
    // Resizer from https://htmldom.dev/create-resizable-split-views/
    const leftSide = vsplitter.previousElementSibling;
    const rightSide = vsplitter.nextElementSibling;

    // The current position of mouse
    let x = 0;
    let y = 0;

    // Width of left side
    let leftWidth = 0;

    // Handle the mousedown event
    // that's triggered when user drags the resizer
    const resizeMouseDownHandler = function (e) {
        // Get the current mouse position
        x = e.clientX;
        y = e.clientY;
        leftWidth = leftSide.getBoundingClientRect().width;

        // Attach the listeners to `document`
        document.addEventListener('mousemove', mouseMoveHandler);
        document.addEventListener('mouseup', mouseUpHandler);
    };

    // Attach the handler
    vsplitter.addEventListener('mousedown', resizeMouseDownHandler);

    const mouseMoveHandler = function (e) {
        // How far the mouse has been moved
        const dx = e.clientX - x;
        const dy = e.clientY - y;

        const newLeftWidth = ((leftWidth + dx) * 100) / vsplitter.parentNode.getBoundingClientRect().width;
        leftSide.style.width = `${newLeftWidth}%`;
        vsplitter.style.cursor = 'col-resize';
        document.body.style.cursor = 'col-resize';

        leftSide.style.userSelect = 'none';
        leftSide.style.pointerEvents = 'none';

        rightSide.style.userSelect = 'none';
        rightSide.style.pointerEvents = 'none';
    };

    const mouseUpHandler = function () {
        vsplitter.style.removeProperty('cursor');
        document.body.style.removeProperty('cursor');

        leftSide.style.removeProperty('user-select');
        leftSide.style.removeProperty('pointer-events');

        rightSide.style.removeProperty('user-select');
        rightSide.style.removeProperty('pointer-events');

        // Remove the handlers of `mousemove` and `mouseup`
        document.removeEventListener('mousemove', mouseMoveHandler);
        document.removeEventListener('mouseup', mouseUpHandler);
    };
}
