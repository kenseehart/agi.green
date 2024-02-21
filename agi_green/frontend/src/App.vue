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
}
</style>

