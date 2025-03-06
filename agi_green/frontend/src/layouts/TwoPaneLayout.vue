<template>
    <Splitter style="height: 100vh; width: 100%;">
      <SplitterPanel :size="30">
          <Chat />
          <MDForm />
      </SplitterPanel>
      <SplitterPanel :size="70">
        <DocTabs class="doc-tabs"/>
      </SplitterPanel>
    </Splitter>
</template>

<script setup>
import Splitter from 'primevue/splitter';
import SplitterPanel from 'primevue/splitterpanel';
import Chat from '@agi.green/components/Chat.vue';
import MDForm from '@agi.green/components/MDForm.vue';
import DocTabs from '@agi.green/components/DocTabs.vue';

import mermaid from 'mermaid';
mermaid.initialize({ startOnLoad: false }); //, logLevel: 'debug'
</script>

<style scoped>
:deep(.p-splitter) {
    height: 100% !important;
    border: none;
    padding: 0;
}

:deep(.p-splitter-panel) {
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
    padding: 0;
}

.doc-tabs {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
}
</style>
