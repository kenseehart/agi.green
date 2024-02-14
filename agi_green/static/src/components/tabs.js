const { createApp, ref } = Vue;
const { TabPanel, TabView } = primevue;

const tabsApp = createApp({
    setup() {
        const tabs = ref([]);
        const activeTabId = ref(null);

        function openTab(name, component, props) {
            let tab = tabs.value.find(t => t.name === name);
            if (!tab) {
                // Create a new tab if it doesn't exist
                tab = {
                    id: tabs.value.length + 1,
                    name: name,
                    component: component,
                    props: props
                };
                tabs.value.push(tab);
                activeTabId.value = tab.id; // Activate the new tab
            } else {
                // Update existing tab's props
                tab.props = props;
                activeTabId.value = tab.id; // Activate the new tab
            }
        }

        return {
            tabs,
            activeTabId,
            openTab
        };
    },
    template: `
        <TabView v-model:activeIndex="activeTabId">
            <TabPanel v-for="tab in tabs" :key="tab.id" :header="tab.name">
                <component :is="tab.component" v-bind="tab.props"></component>
            </TabPanel>
        </TabView>
    `
});

tabsApp.use(PrimeVue);

tabsApp.mount('#tabs-container');
