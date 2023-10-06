/* gameio_component.js */

class GameBoard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });

        this.boardElement = null;
        this.allowed = [];
    }

    connectedCallback() {
        const styleLink = document.createElement('link');
        styleLink.setAttribute('rel', 'stylesheet');
        styleLink.setAttribute('href', 'gameio.css');
        this.shadowRoot.appendChild(styleLink);

        const svgElement = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svgElement.setAttribute('viewBox', '0 0 1 1'); // Normalized view
        svgElement.style.width = '100%';
        svgElement.style.height = '100%';
        this.shadowRoot.appendChild(svgElement);
        this.boardElement = svgElement;

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

    // Image setup using SVG
    const svgImage = document.createElementNS('http://www.w3.org/2000/svg', 'image');
    svgImage.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', msg.board_image);
    svgImage.setAttribute('x', '0');
    svgImage.setAttribute('y', '0');
    svgImage.setAttribute('width', '1');
    svgImage.setAttribute('height', '1');

    gameBoard.boardElement.appendChild(svgImage);

    gameBoard.locations = msg.locations;
    gameBoard.pieces = msg.pieces;

    // Appending pieces inside the gameBoard using SVG
    msg.locations.forEach(location => {
        msg.pieces.forEach(piece => {
            const pieceImage = document.createElementNS('http://www.w3.org/2000/svg', 'image');
            pieceImage.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', piece.image);
            pieceImage.setAttribute('x', location.coords[0] - 0.05); // Assuming piece width is 0.1 for normalization
            pieceImage.setAttribute('y', location.coords[1] - 0.05); // Assuming piece height is 0.1 for normalization
            pieceImage.setAttribute('width', '0.1'); // Normalized width
            pieceImage.setAttribute('height', '0.1'); // Normalized height
            gameBoard.boardElement.appendChild(pieceImage);
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

