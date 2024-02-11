
const tabsApp = new Vue({
    el: '#tabs-container',
    data: {
        tabs: [],
        activeTabId: null,
    },
    methods: {
        openTab: function(name, component, props) {
            let tab = this.tabs.find(t => t.name === name);
            if (!tab) {
                // Create a new tab if it doesn't exist
                tab = {
                    id: this.tabs.length + 1,
                    name: name,
                    component: component,
                    props: props
                };
                this.tabs.push(tab);
                this.activeTabId = tab.id; // Activate the new tab
            } else {
                // Update existing tab's props
                tab.props = props;
                this.activeTabId = tab.id; // Activate the new tab
            }
        }
    },
    template: `
        <div class="tab-container">
            <ul class="tab-titles">
                <li v-for="tab in tabs" :key="tab.id"
                    @click="activeTabId = tab.id"
                    :class="{ 'active': tab.id === activeTabId }">
                    {{ tab.name }}
                </li>
            </ul>
            <div class="tab-content">
                <div v-for="tab in tabs" :id="'tab-content-' + tab.id" v-show="tab.id === activeTabId" :key="tab.id">
                    <component :is="tab.component" v-bind="tab.props"></component>
                </div>
            </div>
        </div>
    `

});


function openTab(name, component, props) {
    const existingTab = tabsApp.tabs.find(tab => tab.name === name);

    if (!existingTab) {
        // Generate a unique ID for the new tab
        const newTabId = tabsApp.tabs.reduce((maxId, tab) => Math.max(maxId, tab.id), 0) + 1;

        // Instead of using a callback to manipulate the DOM, use it to define the component and props
        const newTab = {
            id: newTabId,
            name: name,
            component: component, // Component to be dynamically loaded
            props: props // Props for the component
        };

        // Add the new tab
        tabsApp.tabs.push(newTab);
        tabsApp.activeTabId = newTabId; // Make the new tab active
    } else {
        // For an existing tab, you might want to update its props or just focus it
        tabsApp.activeTabId = existingTab.id;
    }
}
