<template>
  <div>
    <Splitter style="height: 100vh;">
      <SplitterPanel size={30}>
          <Chat />
      </SplitterPanel>
      <SplitterPanel size={70}>
        <DocTabs class="doc-tabs"/>
      </SplitterPanel>
    </Splitter>
  </div>
</template>

<script setup>
import Splitter from 'primevue/splitter';
import SplitterPanel from 'primevue/splitterpanel';
import Chat from './components/Chat.vue'; // Adjust the path as necessary

</script>

<style scoped>
.doc-tabs {
  display: flex;
  flex-direction: column;
  flex: 1; /* This makes each container fill available space */
}

.p-splitter-panel {
    display: flex;
    flex: 1; /* This makes the tab content fill available space */
    flex-direction: column;
    min-height: 0; /* Ensures it can shrink */
    max-height: 100%;
}

</style>

