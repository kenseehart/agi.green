<template>
    <TabView v-model:activeIndex="activeTabIndex">
        <TabPanel v-for="tab in tabs" :key="tab.name" :header="tab.name">
            <!-- Use the component's name for dynamic rendering -->
            <component :is="tab.component" v-bind="tab.props"></component>
        </TabPanel>
    </TabView>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import TabView from 'primevue/tabview';
import TabPanel from 'primevue/tabpanel';
import { bind_handlers, unbind_handlers } from '@/emitter';
import MarkdownView from '@/components/Markdown.vue'; // Example for direct component import
import GameIOView from '@/components/GameIO.vue'; // Example for direct component import

const componentMap = {
    'MarkdownView': MarkdownView,
    'GameIOView': GameIOView,
};

function registerComponent(name, component) {
    componentMap[name] = component;
}

// Reactive state to track tabs and the active tab index
const tabs = ref([]); // Initialize tabs as an empty array
const activeTabIndex = ref(0); // Optionally, initialize to the index of the first tab

function openTab(name, componentName, props) {
    const component = componentMap[componentName]; // Resolve component name to object
    if (!component) {
        console.error(`Component ${componentName} not found.`);
        return;
    }

    const tabIndex = tabs.value.findIndex(tab => tab.name === name);
    if (tabIndex !== -1) {
        // Tab exists, update props and activate it
        tabs.value[tabIndex].props = props;
        activeTabIndex.value = tabIndex;
    } else {
        // Add new tab and activate it
        tabs.value.push({ name, component, props });
        activeTabIndex.value = tabs.value.length - 1;
    }
}

const handlers = {
    ws_open_md: ({name, content, viewMode}) => {
        openTab(name, 'MarkdownView', {
            markdownContent: content || 'Loading...',
            viewMode: viewMode || 'rendered',
        });
    },
    ws_open_game: (gameData) => {
        openTab(gameData.uid, 'GameIOView', gameData);
    },
};

onMounted(() => {
    bind_handlers(handlers);
});

onBeforeUnmount(() => {
    unbind_handlers(handlers);
});
</script>

<style>

.p-tabview {
    flex: 1; /* This makes the tab content fill available space */
    display: flex;
    flex-direction: column;
    min-height: 0; /* Ensures it can shrink */
    max-height: 100%;
    padding-right: 0;
}

.p-tabview-panels {
    flex: 1; /* This makes the tab content fill available space */
    display: flex;
    flex-direction: column;
    min-height: 0; /* Ensures it can shrink */
    max-height: 100%;
}

.p-tabview-panel {
    display: flex;
    flex: 1; /* This makes the tab content fill available space */
    flex-direction: column;
    min-height: 0; /* Ensures it can shrink */
    max-height: 100%;
}

</style>
```
