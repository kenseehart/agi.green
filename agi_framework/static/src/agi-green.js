// Create a connection to the WebSocket server
// Get HTTP protocol (http or https)
const protocol = window.location.protocol
const host = window.location.hostname;
const port = window.location.port;

const ws_protocol = protocol === 'https:' ? 'wss:' : 'ws:';

// Use the same port as the HTTP(S) server for WebSocket connections
const ws_host = `${ws_protocol}//${host}:${port}/ws`;

console.log('ws_host:', ws_host);

var socket;
try {
    socket = new WebSocket(ws_host);
    console.log('WebSocket created:', socket);
}
catch (e) {
    console.log('Error creating WebSocket:', e);
}

socket.onerror = function(event) {
    console.error("WebSocket error observed:", event);
};

socket.onopen = function(event) {
    console.log("WebSocket connection established", event);
};


// Connection opened
socket.addEventListener('open', (event) => {
    console.log('Connected to WS server');
    onWSConnected();
});

function onWSConnected() {
    console.log('onWSConnected()');
}

const md = markdownit({

    // Enable HTML in the markdown source
    html: true,
    linkify: true, // Autoconvert URL-like text to links
    typographer: false, // Enable smart quotes and other typographic substitutions

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

if (window.markdownitFootnote) {
    md.use(window.markdownitFootnote);
}
else {
    console.log('markdownitFootnote not found');
}

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


function send_ws(cmd, data={}) {
    // Send a message to the server
    msg = {cmd, ...data}
    console.log('send_ws:', msg);
    socket.send(JSON.stringify(msg));
}

let userData = {};

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

function on_ws_set_user_data(msg) {
    // Set the user's ID and username
    userData[msg.uid] = msg;
    console.log('userData:', userData);
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


// Workspace injection
// Add a web component to the workspace

function on_ws_workspace_component(msg) {
    // Ensure the game-component script is loaded only once
    console.log('on_ws_workspace_component:', msg);

    if (!window.workspaceComponentsLoaded) {
        window.workspaceComponentsLoaded = {};
    }

    if (!window.workspaceComponentsLoaded[msg.name]) {
        const script = document.createElement('script');
        script.src = msg.name+'_component.js?ts='+Date.now();
        add_ws_promise(msg.name);
        script.onload = function() {
            // call {msg.name}_component.js's inject_{msg.name}() function
            window.workspaceComponentsLoaded[msg.name] = true;
            window['inject_'+msg.name]();
            resolve_ws_promise(msg.name);
        };
        document.body.appendChild(script);
    }
    else {
        window['inject_'+msg.name]();
    }
}

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

    // queue the message until all promises are resolved
    if (!window.wsMessageQueue) {
        window.wsMessageQueue = [];
    }
    if (!window.wsPromises) {
        window.wsPromises = [];
    }

    window.wsMessageQueue.push(msg);

    if (window.wsPromises.length === 0) {
        // Process the queued ws messages
        process_ws_messages();
    }
    else {
        console.log('ws message queued, pending promise', msg);
    }
});

function process_ws_messages() {
    // Process the queued ws messages
    if (!window.wsMessageQueue) {
        window.wsMessageQueue = [];
    }

    while (window.wsMessageQueue.length > 0) {
        const msg = window.wsMessageQueue.shift();
        console.log('processing ws message:', msg);

        if (window['on_ws_'+msg.cmd]) {
            window['on_ws_'+msg.cmd](msg);
        } else {
            console.log('Unknown command:', msg.cmd);
        }
    }
};

function add_ws_promise(promise) {
    // Add a promise to the list of promises to be resolved
    // ws messages will be queued and processed after all promises are resolved
    if (!window.wsPromises) {
        window.wsPromises = [];
    }
    window.wsPromises.push(promise);
    console.log('ws promise added:', promise, '- pending promises:', window.wsPromises.length);
}

function resolve_ws_promise(promise) {
    // Remove a promise from the list of promises to be resolved
    // ws messages will be queued and processed after all promises are resolved
    if (!window.wsPromises) {
        window.wsPromises = [];
    }
    // Remove the promise from the list
    const index = window.wsPromises.indexOf(promise);
    if (index > -1) {
        console.log('ws promise resolved:', promise, 'pending promises:', window.wsPromises.length-1);
        window.wsPromises.splice(index, 1);
    }
    // Check if all promises have been resolved
    if (window.wsPromises.length === 0) {
        // Process the queued ws messages
        process_ws_messages();
    }
}



socket.onerror = function(event) {
    error(`WebSocket Error: ${event.message}`);
    on_ws_append_chat({
        author: 'System',
        content: `A WebSocket error occurred. If you are using a VPN, it could be blocking this. Check your settings and refresh the page.`
    })
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

function unpack(packedList) {
    let unpacked = [];

    for (let packedData of packedList) {
        // Convert all values to arrays
        let lists = {};
        for (let key in packedData) {
            lists[key] = Array.isArray(packedData[key]) ? packedData[key] : [packedData[key]];
        }

        let keys = Object.keys(lists);
        let combinations = cartesianProduct(...Object.values(lists));

        for (let combination of combinations) {
            let unpackedItem = {};
            keys.forEach((key, index) => {
                unpackedItem[key] = combination[index];
            });
            unpacked.push(unpackedItem);
        }
    }

    return unpacked;
}

function cartesianProduct(...arrays) {
    return arrays.reduce((a, b) => {
        return a.map(x => {
            return b.map(y => {
                return x.concat([y]);
            });
        }).reduce((a, b) => a.concat(b), []);
    }, [[]]);
}

function index_key(key, arr) {
    // Index an array of objects by a key
    // index_key('id', [{id: 1, name: 'foo'}, {id: 2, name: 'bar'}])
    // -> {1: {id: 1, name: 'foo'}, 2: {id: 2, name: 'bar'}}
    return arr.reduce((acc, obj) => {
        if (obj[key]) {
            if (!acc[obj[key]]) {
                acc[obj[key]] = [];
            }
            acc[obj[key]].push(obj);
        }
        return acc;
    }, {});
}

