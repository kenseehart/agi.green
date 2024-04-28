<template>
    <div class="game-container">
        <div class="game-board" :style="boardStyle">
            <svg ref="svgBoard" :viewBox="'0 0 1 1'" style="width: 100%; height: 100%;" @click="handleClick">
                <defs>
                <image id="clocksOverlay" :href="clocks_image" width="1" height="1" />
                <image v-for="(piece, id) in pieces" :key="id" :id="`def_${id}_${game_id}`" :href="piece.image"
                    :width="piece.scale" :height="piece.scale" />
                </defs>
                <use href="#clocksOverlay" x="0" y="0" />
                <use v-for="element in pieceElements" :key="element.uid" :href="`#def_${element.piece}_${game_id}`"
                :x="locations[element.location].coords[0] - pieces[element.piece].scale / 2"
                :y="locations[element.location].coords[1] - pieces[element.piece].scale / 2" />

                <use v-for="annotation in annotationElements" :key="annotation.uid" :href="`#def_${annotation.piece}_${game_id}`"
                :x="locations[annotation.location].coords[0] - pieces[annotation.piece].scale / 2"
                :y="locations[annotation.location].coords[1] - pieces[annotation.piece].scale / 2" />

                <text x="0.14" y="0.06" class="player-name" text-anchor="middle" font-size="0.027">{{ player_names.b }}</text>
                <text x="0.86" y="0.06" class="player-name" text-anchor="middle" font-size="0.027">{{ player_names.w }}</text>
                <text x="0.14" y="0.15" class="clock-text" text-anchor="middle" font-size="0.06">{{ clockTextB }}</text>
                <text x="0.86" y="0.15" class="clock-text" text-anchor="middle" font-size="0.06">{{ clockTextW }}</text>

                <g v-if="showResignButton===1">
                    <SvgButton :label="resignText" x="0.05" y="0.22" text-anchor="start" font-size="0.025" @clicked="resignGame('b')" />
                </g>

                <g v-if="showResignButton===2">
                    <SvgButton :label="resignText" x="0.95" y="0.22" text-anchor="end" font-size="0.025" @clicked="resignGame('w')" />
                </g>

                <text x="0.05" y="0.22" class="clock-text" text-anchor="start" font-size="0.025">{{ resultTextB }}</text>
                <text x="0.95" y="0.22" class="clock-text" text-anchor="end" font-size="0.025">{{ resultTextW }}</text>
            </svg>
        </div>
    </div>
</template>

<script setup>
import { inject, ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue';

import { bind_handlers, unbind_handlers } from '@/emitter';
import SvgButton from './SvgButton.vue';

const send_ws = inject('send_ws');

function arrayToObj(array) {
    return array.reduce((obj, item) => {
        obj[item.id] = item;
        return obj;
    }, {});
}

const props = defineProps({
    board_image: String,
    clocks_image: String,
    locations: Object,
    pieces: Object,
    game_id: String,
    player_names: Object,
    roles: Array,
});

const svgBoard = ref(null);
const board_image = ref(props.board_image);
const clocks_image = ref(props.clocks_image);
const pieces = ref(arrayToObj(props.pieces));
const locations = ref(arrayToObj(props.locations));
const pieceElements = ref([]);
const annotationElements = ref([]);
const allowed = ref([]);
const nextUid = ref({});
const game_id = ref(props.game_id);
const player_names = ref(props.player_names);
const clockTimes = ref({ b: 0, w: 0 }); // in seconds, negative means clock is stopped and value is time remaining, positive means clock is running and value is absolute time t0, 0 means 0:00
const resultTextB = ref('');
const resultTextW = ref('');
const winner = ref('');
const roles = ref(props.roles); // player: ['b'] or ['w'], watcher: [], teacher: ['b', 'w']
const moveIndex = ref(0); // move index of current board state on the client, which is moveList.value.length+1 if we made a move that hasn't been echoed back from the server, otherwise moveList.value.length
const moveList = ref([]); // moves received from the server
const resignText = ref('resign');

// Show resign button if the game is not over and the player has a role: 1 for black, 2 for white
const showResignButton = computed(() => winner.value ? 0 : roles.value.includes('b') ? 1 : roles.value.includes('w') ? 2 : 0);

const resignGame = (role) => {
    console.log("Resignation triggered by", role)
    send_ws('gameio_move', { game_id: game_id.value, clock: stopAndGetClock(), role:role, i:moveIndex.value++, lose: 'resigned'})
};

const checkElements = () => {
    // Check if all pieces and annotations are defined
    for (const element of pieceElements.value.concat(annotationElements.value)) {
        if (!pieces.value[element.piece]) {
            console.error(`Piece ${element.piece} not defined`);
            return false;
        }
    }
    return true;
};

/*
About time:

There are two conventions for time:

UI time: time displayed on the clock
    relative or absolute time in seconds,
      negative means clock is stopped and value is time remaining,
      positive means clock is running and it's value is t0 (the absolute time when the clock will run out)

API time: time communicated to and from the server
    relative time in seconds,
      negative means clock is stopped and value is time remaining
      positive means clock is running and value is time remaining

*/



const clockText = (time) => {
    // time: relative or absolute time in seconds,
    //   negative means clock is stopped and value is time remaining,
    //   positive means clock is running and it's value is t0 (the absolute time when the clock will run out)
    // t is the actual time remaining

    if (time === undefined) {
        console.error("Time is undefined");
        return "-:--";
    }

    var t;

    if (time <= 0) {
        t = -time;
    } else {
        t = time - Date.now() / 1000;

        if (t < 0) {
            t = 0;
        }
    }

    if (t >= 3600) {
        const hours = Math.floor(t / 3600);
        const minutes = Math.floor((t % 3600) / 60);
        return `${hours}:${minutes.toString().padStart(2, '0')}`;
    }
    else if (t >= 60) {
        const minutes = Math.floor(t / 60);
        const seconds = Math.floor(t % 60);
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
    else {
        return t.toFixed(1);
    }
};

const clockTextB = computed(() => {
    return clockText(clockTimes.value.b);
});

const clockTextW = computed(() => {
    return clockText(clockTimes.value.w);
});


const updateClockDisplay = () => {
    for (const key in clockTimes.value) {
        if (clockTimes.value[key] > 0) { // Ensure the clock is running
            if (Date.now()/1000 > clockTimes.value[key]) {
                // timeout has occurred
                clockTimes.value[key] = 0;
                send_ws('gameio_move', { game_id: game_id.value, clock: clockTimes.value, role:key, i:moveIndex.value++, lose: 'out of time'})
                return
            }

            const millis = Math.floor(clockTimes.value[key]*1000);

            // XOR adjustment based on the current millisecond value
            if (millis % 2 === 0) {
                // Even millisecond: increment time by 1ms (0.001 seconds)
                clockTimes.value[key] += 0.001;
            } else {
                // Odd millisecond: decrement time by 1ms (0.001 seconds)
                clockTimes.value[key] -= 0.001;
            }
        }
    }
};


const updateClock = (clock) => {
    // clock: {b: time, w: time}
    // time: relative time in seconds,
    //   negative means clock is stopped and value is time remaining
    //   positive means clock is running and value is time remaining

    for (const player in clock) {
        if (clock[player] > 0) {
            clockTimes.value[player] = Date.now() / 1000 + clock[player];
        }
        else {
            clockTimes.value[player] = clock[player];
        }
    }
};

const stopAndGetClock = () => {
    // Stop the clock and return the time remaining (as negative seconds)
    for (const player in clockTimes.value) {
        if (clockTimes.value[player] > 0) {
            clockTimes.value[player] = Date.now() / 1000 - clockTimes.value[player];
        }
    }
    return { ...clockTimes.value };
};



const boardStyle = computed(() => ({
    backgroundImage: `url(${board_image.value})`,
    backgroundSize: 'cover', // Use 'cover' to ensure the image covers without stretching
    backgroundPosition: 'center', // Center the background image
    width: '100%', // Full width
    height: '100%' // Full height
}));


const newUid = (piece) => {
    if (!nextUid.value[piece]) {
        nextUid.value[piece] = 0;
    } else {
        nextUid.value[piece]++;
    }
    return `${piece}_${nextUid.value[piece]}`;
};

const handleClick = (event) => {
    const rect = svgBoard.value.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // Calculate relative positions
    const relX = x / rect.width;
    const relY = y / rect.height;

    const clickedLocationId = getLocationIdAt(locations.value, relX, relY);
    const move = allowed.value.find(move => move.dest === clickedLocationId);

    if (move) {
        move.game_id = props.game_id;
        move.clock = stopAndGetClock();

        if (moveIndex.value != moveList.value.length) {
            console.error("Client move index out of sync with client move list", moveList.value.length, moveIndex.value, move);
        }

        move.i = moveIndex.value++;
        doMove(move);
        send_ws('gameio_move', move);
    }
};

const getLocationIdAt = (locations, relX, relY, radius = 0.05) => {
    let closestId = null;
    let closestDist = Infinity;

    for (const loc of Object.values(locations)) {
        const [locX, locY] = loc.coords;
        const d = Math.sqrt((relX - locX) ** 2 + (relY - locY) ** 2);
        if (d < radius && d < closestDist) {
        closestDist = d;
        closestId = loc.id;
        }
    }
    return closestId;
};

const doMove = (msg) => {
    console.log("doMove:", msg);
    allowed.value = [];

    var pieceElement = null;

    if (msg.from) {
        pieceElement = pieceElements.value.find(element => element.location === msg.from);

        if (!msg.to) {
            // remove piece element
            pieceElements.value = pieceElements.value.filter(element => element !== pieceElement);
        }
        else {
            // move piece element
            pieceElement.location = msg.to;
        }
    }
    else if (msg.piece) {
        // create new piece element
        pieceElement = {
            uid: newUid(msg.piece),
            piece: msg.piece,
            location: msg.dest,
        };
        pieceElements.value.push(pieceElement);
    }

    if (msg.annotations) {
        // replace annotations
        annotationElements.value = msg.annotations;
    }
    else {
        // remove annotations
        annotationElements.value = [];
    }

    checkElements();
};


const handlers = {
    ws_gameio_allow: (msg) => {
        if (msg.game_id === props.game_id) {
            allowed.value = msg.moves;
        }
    },

    ws_gameio_move: (msg) => {
        if (msg.game_id === props.game_id) {
            if (msg.clock) {
                updateClock(msg.clock);
            }

            if (msg.i == moveIndex.value) {
                doMove(msg);
            }
            else
            {
                if (msg.i == moveIndex.value - 1) {
                    console.info("Received echo of move", msg.i)
                }
                else {
                    console.error("Incoming move.i out of sync with client board state", moveIndex.value, msg.i, msg);
                }
            }

            if (moveList.value.length == msg.i) {
                moveList.value.push(msg);
                moveIndex.value = moveList.value.length;
            }
            else if (moveList.value.length == msg.i + 1) {
                console.info("Received duplicate or collision of move", msg.i)
                // TODO: check if the move is the same, if not, handle it
            }
            else {
                console.error("Incoming move.i out of sync with client move list", moveList.value.length, msg.i, msg);
            }
        }
    },

    ws_gameio_status: (msg) => {
        console.log("ws_gameio_status:", msg);
        if (msg.game_id === props.game_id) {
            winner.value = msg.winner;
            if (msg.b) {
                resultTextB.value = msg.b;
            }
            if (msg.w) {
                resultTextW.value = msg.w;
            }
            if (msg.clock) {
                updateClock(msg.clock);
            }
        }
    }
};

onMounted(() => {
    bind_handlers(handlers);
    const interval = setInterval(updateClockDisplay, 100);  // Update at 10Hz

    onBeforeUnmount(() => {
        clearInterval(interval);
        unbind_handlers(handlers);
    });
});

</script>

<style scoped>

.game-container {
    position: relative;
    max-width: 100vh; /* Ensure that width does not exceed viewport height */
    padding-bottom: 100%; /* Maintain aspect ratio */
}
.game_board {
    position: relative;
    padding-bottom: 100%; /* Maintain aspect ratio */
    max-width: 100%;
    max-height: 100vh;
}

.game_board svg {
    position: absolute;
    width: 100%;
    height: 100%;
}
img.game_board {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
}

img.game_piece {
    position: absolute;
    width: 7%;
    cursor: pointer;
    transform: translate(-50%, -50%);
}

.player-name {
  font-size: 0.05;
}

.clock-text {
  font-size: 0.04;
}

</style>
