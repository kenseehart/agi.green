class GameBoard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    connectedCallback() {
        const styleLink = document.createElement('link');
        styleLink.setAttribute('rel', 'stylesheet');
        styleLink.setAttribute('href', 'gameio.css');
        this.shadowRoot.appendChild(styleLink);

        const gameBoardContainer = document.createElement('div');
        gameBoardContainer.className = 'game_board_container';
        this.shadowRoot.appendChild(gameBoardContainer);

        this.boardElement = gameBoardContainer;
        this.allowed = [];

        this.boardElement.addEventListener('click', this.handleClick.bind(this));
    }

    do_move(msg) {
        // implement board update logic here
    }

    getLocationIdAt(locations, relX, relY, radius = 0.05) {
        let closestId = null;
        let closestDist = 1e6;

        for (let id in locations) {
            const [locX, locY] = locations[id].coords;
            const d = Math.sqrt((relX - locX)**2 + (relY - locY)**2);
            if (d < radius && d < closestDist) {
                closestDist = d;
                closestId = id;
            }
        }
        return closestId;
    }

    handleClick(e) {
        const rect = this.boardElement.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const boardSize = Math.min(rect.width, rect.height);
        const clickedLocationId = this.getLocationIdAt(this.locations, x/boardSize, y/boardSize);

        if (this.allowed.includes(clickedLocationId)) {
            sendWs('gameio_move', {
                dest: clickedLocationId
            });
            this.do_move({
                dest: clickedLocationId
            });
        }
    }
}

customElements.define('game-board', GameBoard);

function on_ws_gameio_init(msg) {
    console.log("on_ws_gameio_init:", msg);
    const gameBoard = document.querySelector('game-board');

    // Image setup
    const img = document.createElement('img');
    img.src = msg.board_image;
    img.alt = msg.alt_text;
    img.className = 'game_board';

    // Ensure the image is appended to the .game_board_container
    const gameBoardContainer = gameBoard.shadowRoot.querySelector('.game_board_container');
    gameBoardContainer.appendChild(img);

    gameBoard.locations = msg.locations;
    gameBoard.pieces = msg.pieces;

    // Appending pieces inside the gameBoardContainer to maintain relative positioning
    msg.locations.forEach(location => {
        msg.pieces.forEach(piece => {
            const pieceImg = document.createElement('img');
            pieceImg.src = piece.image;
            pieceImg.alt = piece.desc;
            pieceImg.className = 'game_piece';
            pieceImg.style.position = 'absolute';
            pieceImg.style.left = `calc(${location.coords[0] * 100}%)`;
            pieceImg.style.top = `calc(${location.coords[1] * 100}%)`;
            gameBoardContainer.appendChild(pieceImg);
        });
    });
}

function on_ws_gameio_allow(msg) {
    console.log("on_ws_gameio_allow:", msg);
    const gameBoard = document.querySelector('game-board');
    gameBoard.allowed = msg.allow;
}

function on_ws_gameio_move(msg) {
    console.log("on_ws_gameio_move:", msg);
    // Implement the logic to update the game board
}

function inject_gameio()
{
    const gameBoard = document.createElement('game-board');
    // replace the workspace contents with the game board
    document.getElementById('workspace').innerHTML = '';
    document.getElementById('workspace').appendChild(gameBoard);
}
console.log("inject_gameio defined:", typeof inject_gameio);

