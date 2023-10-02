class GameBoard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    connectedCallback() {
        // Create the image element
        const img = document.createElement('img');
        // to do: make this image configurable
        img.src = 'images/loading.gif';
        img.alt = '... loading ...';
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

function on_ws_gameio_init(msg)
{
    console.log("on_ws_gameio_init:", msg);
    // update game-board element
    const gameBoard = document.querySelector('game-board');
    gameBoard.shadowRoot.querySelector('img').src = msg.board_image;
    gameBoard.shadowRoot.querySelector('img').alt = msg.alt_text;
    gameBoard.locations = msg.locations;
    gameBoard.pieces = msg.pieces;

    // {
    //     "cmd": "gameio_init",
    //     "board_image": f"{self.name}_1280.png",
    //     "locations": [
    //         {"id": str(i), "coords": self.coords[i].tolist()} for i in range(self.size)
    //     ],
    //     "pieces": [
    //         {"id": "b", "image": "stone_black.png", "desc": "Black stone"},
    //         {"id": "w", "image": "stone_white.png", "desc": "White stone"},
    //     ],
    // }

}

function on_ws_gameio_allow(msg)
{
    console.log("on_ws_gameio_allow:", msg);
    // to do: update the game board
}

function on_ws_gameio_move(msg)
{
    console.log("on_ws_gameio_move:", msg);
    // to do: update the game board
}

function inject_gameio()
{
    const gameBoard = document.createElement('game-board');
    // replace the workspace contents with the game board
    document.getElementById('workspace').innerHTML = '';
    document.getElementById('workspace').appendChild(gameBoard);
}
console.log("inject_gameio defined:", typeof inject_gameio);

