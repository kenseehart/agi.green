<template>
    <div class="flex-container">
        <div class="md-button-container">
            <button
                @click="setViewMode('rendered')"
                :class="{'md-button-selected': viewMode === 'rendered', 'md-button-unselected': viewMode !== 'rendered'}">
                <img :src="renderIcon" alt="Markdown Rendered">
            </button>
            <button
                @click="setViewMode('source')"
                :class="{'md-button-selected': viewMode === 'source', 'md-button-unselected': viewMode !== 'source'}">
                <img :src="sourceIcon" alt="Markdown Source">
            </button>
        </div>
        <ScrollPanel class="flexy-scroll">
            <!-- Source Content -->
            <div v-show="viewMode === 'source'" class="md-doc">
                <pre><code>{{ props.markdownContent }}</code></pre>
            </div>
            <!-- Rendered Markdown Content -->
            <div v-show="viewMode === 'rendered'" class="md-doc" v-html="renderedMarkdown" ref="markdownContainer"></div>
        </ScrollPanel>
    </div>
</template>

<script setup>
import { ref, watch, onUpdated, nextTick } from 'vue';
import { processMarkdown, postRender } from '@/plugins/markdownPlugin';
import sourceIcon from '@/assets/md-source.png';
import renderIcon from '@/assets/md-render.png';

const props = defineProps({
    markdownContent: String,
});

const viewMode = ref('rendered');
const renderedMarkdown = ref('');

// Process markdown content initially and on content updates
watch(() => props.markdownContent, (newVal) => {
    renderedMarkdown.value = processMarkdown(newVal);
    // Ensure postRender is called after markdown has been processed and DOM updated
    nextTick(() => {
        if (viewMode.value === 'rendered') {
            postRender();
        }
    });
}, { immediate: true });

const setViewMode = (mode) => {
    viewMode.value = mode;
};
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

.flexy-scroll {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0; /* Ensures it can shrink */
    max-height: 100%;
    overflow-y: auto;
}

</style>
