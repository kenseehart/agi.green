<template>
    <div class="game-container">
        <div class="game-board" :style="boardStyle">
        <svg ref="svgBoard" :viewBox="'0 0 1 1'" style="width: 100%; height: 100%;" @click="handleClick">
            <defs>
            <image v-for="piece in pieces" :key="piece.id" :id="`def_${piece.id}_${uid}`" :href="piece.image"
                :width="piece.scale" :height="piece.scale" />
            </defs>
            <use v-for="element in pieceElements" :key="element.uid" :href="`#def_${element.piece}_${uid}`"
            :x="locations[element.location].coords[0] - pieces[0].scale / 2"
            :y="locations[element.location].coords[1] - pieces[0].scale / 2" />
        </svg>
        </div>
    </div>
</template>

<script setup>
  import { inject, ref, computed, onMounted, onBeforeUnmount } from 'vue';
  import { bind_handlers, unbind_handlers } from '@/emitter';

  const send_ws = inject('send_ws');

  const props = defineProps({
    board_image: String,
    locations: Object,
    pieces: Object,
    uid: String,
  });

  const svgBoard = ref(null);
  const board_image = ref(props.board_image);
  const pieces = ref(props.pieces);
  const locations = ref(props.locations);
  const pieceElements = ref([]);
  const allowed = ref([]);
  const nextUid = ref({});
  const uid = ref(props.uid);

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
  };


  const handlers = {
    ws_gameio_allow: (msg) => {
      allowed.value = unpack(msg.moves);
    },

    ws_gameio_move: (msg) => {
      doMove(msg);
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
</style>
