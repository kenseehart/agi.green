<template>
  <div>
    <Splitter>
      <SplitterPanel size={30}>
        <Chat />
      </SplitterPanel>
      <SplitterPanel size={70}>
        <TabView>
          <TabPanel header="Tab 1">
            Content 1
          </TabPanel>
          <TabPanel header="Tab 2">
            Content 2
          </TabPanel>
          <TabPanel header="Tab 3">
            Content 3
            blah blah blah
            <p>blah blah blah</p>
            <p>blah blah blah</p>
          </TabPanel>
        </TabView>
      </SplitterPanel>
    </Splitter>
  </div>
</template>

<script setup>
import Splitter from 'primevue/splitter';
import SplitterPanel from 'primevue/splitterpanel';
import TabView from 'primevue/tabview';
import TabPanel from 'primevue/tabpanel';
import Chat from './components/Chat.vue'; // Adjust the path as necessary
</script>

<style scoped>
/* Add your custom styles here */
</style>
