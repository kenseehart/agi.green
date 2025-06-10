<template>
    <div class="flex-container" :id="id">
        <div class="md-button-container">
            <button
                @click="setViewMode('rendered')"
                :class="{'md-button-selected': localViewMode === 'rendered', 'md-button-unselected': localViewMode !== 'rendered'}">
                <img :src="renderIcon" alt="Markdown Rendered">
            </button>
            <button
                @click="setViewMode('source')"
                :class="{'md-button-selected': localViewMode === 'source', 'md-button-unselected': localViewMode !== 'source'}">
                <img :src="sourceIcon" alt="Markdown Source">
            </button>
        </div>
        <div class="md-scroll-container">
            <!-- Source Content -->
            <div v-show="localViewMode === 'source'" class="md-doc">
                <pre><code>{{ markdownContent }}</code></pre>
            </div>
            <!-- Rendered Markdown Content -->
            <div v-show="localViewMode === 'rendered'" class="md-doc" v-html="renderedMarkdown" ref="markdownContainer"></div>
        </div>
    </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { processMarkdown, postRender } from '@agi.green/plugins/markdownPlugin';
import { bind_handlers, unbind_handlers } from '@agi.green/emitter';
import { useFileDrop } from '@agi.green/composables/useFileDrop';
import sourceIcon from '@agi.green/assets/md-source.png';
import renderIcon from '@agi.green/assets/md-render.png';

const props = defineProps({
    markdownContent: {
        type: String,
        default: ''
    },
    viewMode: {
        type: String,
        default: 'rendered'
    },
    id: {
        type: String,
        default: 'markdown-default'
    }
});

// Create internal reactive state
const localViewMode = ref(props.viewMode);
const markdownContent = ref(props.markdownContent);
const renderedMarkdown = ref('');

// Handle external prop changes
watch(() => props.markdownContent, (newVal) => {
    markdownContent.value = newVal;
}, { immediate: true });

watch(() => props.viewMode, (newVal) => {
    localViewMode.value = newVal;
}, { immediate: true });

// Process markdown content initially and on content updates
watch(() => markdownContent.value, (newVal) => {
    renderedMarkdown.value = processMarkdown(newVal);
    // Ensure postRender is called after markdown has been processed and DOM updated
    nextTick(() => {
        if (localViewMode.value === 'rendered') {
            postRender();
        }
    });
}, { immediate: true });

const setViewMode = (mode) => {
    localViewMode.value = mode;
    if (mode === 'rendered') {
        nextTick(() => {
            postRender();
        });
    }
};

function setContent(content, mode) {
    // Update the internal reactive state
    markdownContent.value = content; 

    // If a view mode is provided, update it
    if (mode) {
        localViewMode.value = mode;
    }

    // Ensure the DOM is updated and then run post-render hooks
    nextTick(() => {
        if (localViewMode.value === 'rendered') {
            postRender();
        }
    });
}

const handlers = {
    ws_set_md: ({ content, viewMode, id }) => {
        // Only update if id matches or id is not provided (backwards compatibility)
        if (!id || id === props.id) {
            // Similar to how OpenTab affects markdown view but without tab involvement
            setContent(content, viewMode || localViewMode.value);
        }
    },
};

// Add file drop functionality
useFileDrop();

onMounted(() => {
    bind_handlers(handlers);
});

onBeforeUnmount(() => {
    unbind_handlers(handlers);
});
</script>

<style scoped>
/* Add styles for your markdown viewer here */

.md-doc {
    position: relative;
}

.md-doc pre {
    margin: 0px;
    box-sizing: border-box;
}

.md-source {
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 3px;
    padding: 0px;
}

.md-rendered {
    padding: 0px;
}

.md-template-body {
    padding: 0px;
}

.md-button-container {
    display: flex;
    justify-content: flex-end; /* Aligns items to the right */
    align-items: center; /* Center items vertically */
    position: absolute;
    top: -15px;
    right: 0;
    z-index: 100;
}

.md-button-container button {
    background-color: transparent;
    border: none; /* This will remove the border around the button */
    cursor: pointer;
    padding: 0;
    outline: none;
}

.md-button-container img {
    width: 20px; /* This sets the image width */
    height: auto; /* This maintains the image aspect ratio */
    filter: grayscale(100%);
    opacity: 0.6;
    transition: filter 0.3s, opacity 0.3s;
}

.md-button-selected img {
    filter: none !important;
    opacity: 1 !important;
}

.flex-container {
    position: relative;
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0; /* Ensures it can shrink */
    max-height: 100%;
}

.md-scroll-container {
    flex: 1;
    overflow-y: auto;
    height: 100%;
}
</style>
