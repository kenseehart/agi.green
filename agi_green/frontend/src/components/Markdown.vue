<template>
    <div class="flex-container">
        <div class="md-button-container">
            <button @click="setViewMode('rendered')"
                :class="{'md-button-selected': viewMode === 'rendered', 'md-button-unselected': viewMode !== 'rendered'}">
                <img :src="renderIcon" alt="Markdown Rendered">
            </button>
            <button @click="setViewMode('source')"
                :class="{'md-button-selected': viewMode === 'source', 'md-button-unselected': viewMode !== 'source'}">
                <img :src="sourceIcon" alt="Markdown Source">
            </button>
        </div>
        <ScrollPanel class="flexy-scroll">
            <div class="md-doc">
                <div v-if="viewMode === 'source'">
                    <pre><code>{{ props.markdownContent }}</code></pre>
                </div>
                <div v-else v-html="renderedContent">
                </div>
            </div>
        </ScrollPanel>
    </div>
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue';
import { md } from '@/plugins/markdownPlugin'; // Adjust the import path as needed
import sourceIcon from '@/assets/md-source.png'; // Import the image
import renderIcon from '@/assets/md-render.png'; // Import the image

const props = defineProps({
    markdownContent: {
        type: String,
        default: 'Loading...'
    }
});

const viewMode = ref('rendered');
const markdownContainer = ref(null);

const setViewMode = (mode) => {
    console.log('Setting view mode to', mode);
    const before = viewMode.value;
    viewMode.value = mode;
    console.log('View mode changed from', before, 'to', viewMode.value);
};

const renderedContent = computed(() => {
    // Initially just return the rendered markdown
    // Transformation to include dynamic components will be handled post-render
    return md.render(props.markdownContent);
});

const injectForms = () => {
    if (!markdownContainer.value || viewMode.value === 'source') return;

    // Example: Find and replace placeholders in the renderedContent here
    // This is where you'd dynamically mount FormRenderer components
    // Note: This is a conceptual example; actual implementation may vary based on your setup
};

// Re-inject forms whenever the markdown content or view mode changes
watch([renderedContent, viewMode], () => {
    // Ensure the DOM is updated before attempting to inject forms
    nextTick(() => {
        injectForms();
    });
});

onMounted(() => {
    injectForms();
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

.flexy-scroll {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0; /* Ensures it can shrink */
    max-height: 100%;
    overflow-y: auto;
}

</style>
