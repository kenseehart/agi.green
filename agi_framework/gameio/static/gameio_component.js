class GameBoard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    connectedCallback() {
        // Create the image element
        const img = document.createElement('img');
        // to do: make this image configurable
        img.src = 'images/y15_1280.png';
        img.alt = 'Game Board';
        img.className = 'game_board'; // Apply the 'game_board' class

        // Load and attach styles
        const styleLink = document.createElement('link');
        styleLink.setAttribute('rel', 'stylesheet');
        styleLink.setAttribute('href', 'gameio.css');
        this.shadowRoot.appendChild(styleLink);

        // Append the image to the shadow root
        this.shadowRoot.appendChild(img);
    }
}

customElements.define('game-board', GameBoard);

function inject_gameio()
{
    const gameBoard = document.createElement('game-board');
    // replace the workspace contents with the game board
    document.getElementById('workspace').innerHTML = '';
    document.getElementById('workspace').appendChild(gameBoard);
}
console.log("inject_gameio defined:", typeof inject_gameio);

