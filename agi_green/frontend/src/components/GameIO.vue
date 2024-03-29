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

            <text x="0.14" y="0.06" class="player-name" text-anchor="middle" font-size="0.025">{{ player_names.b }}</text>
            <text x="0.86" y="0.06" class="player-name" text-anchor="middle" font-size="0.025">{{ player_names.w }}</text>
            <text x="0.14" y="0.15" class="clock-text" text-anchor="middle" font-size="0.06">{{ clockText(clockTimes.b) }}</text>
            <text x="0.86" y="0.15" class="clock-text" text-anchor="middle" font-size="0.06">{{ clockText(clockTimes.w) }}</text>

        </svg>
        </div>
    </div>
</template>

<script setup>
  import { inject, ref, computed, onMounted, onBeforeUnmount } from 'vue';
  import { bind_handlers, unbind_handlers } from '@/emitter';

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
  const clockTimes = ref({ b: 0, w: 0 }); // in seconds, negative means clock is stopped and value is time remaining, positive means clock is running and value is real time t0, 0 means 0:00

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

const clockText = (time) => {
    // time: in seconds, negative means clock is stopped and value is time remaining, positive means clock is running and value is t0, 0 means 0:00
    // t is the actual time remaining

    var t;

    if (time <= 0) {
        t = -time;
    } else {
        t = time - Date.now() / 1000;

        if (t < 0) {
            t = 0;
        }
    }

  if (t >= 60) {
    const minutes = Math.floor(t / 60);
    const seconds = Math.floor(t % 60);
    return `${minutes}M:${seconds.toString().padStart(2, '0')}`;
  } else {
    return t.toFixed(2);
  }
};

  const boardStyle = computed(() => ({
    backgroundImage: `url(${board_image.value})`,
    backgroundSize: 'cover', // Use 'cover' to ensure the image covers without stretching
    backgroundPosition: 'center', // Center the background image
    width: '100%', // Full width
    height: '100%' // Full height
  }));

  const initStyles = () => {
    // Append the stylesheet for game board
    const styleLink = document.createElement('link');
    styleLink.setAttribute('rel', 'stylesheet');
    styleLink.setAttribute('href', '/gameio.css');
    document.head.appendChild(styleLink);
  };

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
      doMove(move);
      // Assuming send_ws is a global function to send websocket messages
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
          doMove(msg);
        }
    },
  };

  onMounted(() => {
    bind_handlers(handlers);
  });

  onBeforeUnmount(() => {
    unbind_handlers(handlers);
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
