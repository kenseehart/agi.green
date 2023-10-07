/* gameio_component.js */

/* Nameing convention:
Use python naming convention for things that are defined in python, and messages.
Use camelCase for things that are entirely in the javascript domain.
*/

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

    doMove(msg) {
        console.log("doMove:", msg);
        // implement board update logic here
        this.allowed = [];

        if (msg.from) {
            const pieceElement = this.pieceElements[[msg.from, msg.piece]];
            pieceElement.setAttribute('visibility', 'hidden');
        }

        if (msg.dest) {
            const pieceElement = this.pieceElements[[msg.dest, msg.piece]];
            pieceElement.setAttribute('visibility', 'visible');
        }
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
        const rect = this.boardImage.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Calculate relative positions:
        const relX = x / rect.width;
        const relY = y / rect.height;

        const clickedLocationId = this.getLocationIdAt(this.locations, relX, relY);
        console.log("handleClick:", clickedLocationId);

        const move = this.allowed.find(move => move.dest === clickedLocationId);

        if (move) {
            send_ws('gameio_move', move);
            this.doMove(move);
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
    gameBoard.boardImage = svgImage;

    gameBoard.locations = msg.locations;
    gameBoard.pieces = msg.pieces;
    gameBoard.pieceElements = {};

    const diameter = 0.086;

    // Create a defs section to define the reusable images
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    gameBoard.boardElement.appendChild(defs);

    // Define pieces in defs once
    msg.pieces.forEach(piece => {
        const pieceImageDef = document.createElementNS('http://www.w3.org/2000/svg', 'image');
        pieceImageDef.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', piece.image);
        pieceImageDef.setAttribute('id', `def_${piece.id}`);
        pieceImageDef.setAttribute('width', diameter.toString()); // Normalized width
        pieceImageDef.setAttribute('height', diameter.toString()); // Normalized height
        defs.appendChild(pieceImageDef);
    });

    // Use pieces in the gameBoard using the "use" element
    msg.locations.forEach(location => {
        msg.pieces.forEach(piece => {
            const pieceImageUse = document.createElementNS('http://www.w3.org/2000/svg', 'use');
            pieceImageUse.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', `#def_${piece.id}`);
            pieceImageUse.setAttribute('x', location.coords[0] - diameter/2);
            pieceImageUse.setAttribute('y', location.coords[1] - diameter/2);
            pieceImageUse.setAttribute('visibility', 'hidden');
            gameBoard.boardElement.appendChild(pieceImageUse);
            gameBoard.pieceElements[[location.id, piece.id]] = pieceImageUse;
        });
    });
}



function on_ws_gameio_allow(msg) {
    console.log("on_ws_gameio_allow:", msg);
    const gameBoard = document.querySelector('game-board');
    gameBoard.allowed = unpack(msg.moves);
}

function on_ws_gameio_move(msg) {
    console.log("on_ws_gameio_move:", msg);
    // Implement the logic to update the game board
    const gameBoard = document.querySelector('game-board');
    gameBoard.doMove(msg);

}

function inject_gameio()
{
    const gameBoard = document.createElement('game-board');
    // replace the workspace contents with the game board
    document.getElementById('workspace').innerHTML = '';
    document.getElementById('workspace').appendChild(gameBoard);
}
console.log("inject_gameio defined:", typeof inject_gameio);

