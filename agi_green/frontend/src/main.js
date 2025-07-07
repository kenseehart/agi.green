import { createApp } from 'vue'
import App from './App.vue'
import PrimeVue from 'primevue/config';

import 'primevue/resources/themes/saga-blue/theme.css'; // theme
import 'primevue/resources/primevue.min.css'; // core css
import 'primeicons/primeicons.css'; // icons
import '../public/resizable-layout.css'; // ResizableLayout styles

import WebSocketPlugin from './plugins/websocketPlugin';
import UserDataPlugin from './plugins/userDataPlugin';
import markdownPlugin from './plugins/markdownPlugin';

import DocTabs from './components/DocTabs.vue';
import MarkdownView from './components/Markdown.vue';
import Chat from './components/Chat.vue';
import MDForm from './components/MDForm.vue';
import GameIO from './components/GameIO.vue';
import TwoPaneLayout from './layouts/TwoPaneLayout.vue';
import ResizableLayout from './components/ResizableLayout.vue';
import TaxProgressBar from './components/TaxProgressBar.vue';

import PerfectScrollbar from 'vue3-perfect-scrollbar'
import 'vue3-perfect-scrollbar/dist/vue3-perfect-scrollbar.css'

import Vueform from '@vueform/vueform'
import vueformConfig from './../vueform.config'

const app = createApp(App);

app.use(PrimeVue);
app.use(WebSocketPlugin);
app.use(UserDataPlugin);
app.use(markdownPlugin);
app.use(PerfectScrollbar)
app.use(Vueform, vueformConfig)

app.component('DocTabs', DocTabs);
app.component('MarkdownView', MarkdownView);
app.component('Chat', Chat);
app.component('MDForm', MDForm);
app.component('GameIO', GameIO);
app.component('TwoPaneLayout', TwoPaneLayout);
app.component('ResizableLayout', ResizableLayout);
app.component('TaxProgressBar', TaxProgressBar);
app.component('Vueform', Vueform.Form);
app.mount('#app');

// Components
export { default as Chat } from './components/Chat.vue'
export { default as DocTabs } from './components/DocTabs.vue'
export { default as MDForm } from './components/MDForm.vue'
export { default as GameIO } from './components/GameIO.vue'
export { default as ResizableLayout } from './components/ResizableLayout.vue'
export { default as MarkdownView } from './components/Markdown.vue'
export { default as TaxProgressBar } from './components/TaxProgressBar.vue'

// Layouts
export { default as TwoPaneLayout } from './layouts/TwoPaneLayout.vue'

// Plugins
export { default as markdownPlugin } from './plugins/markdownPlugin'
export { default as websocketPlugin } from './plugins/websocketPlugin'
export { default as userDataPlugin } from './plugins/userDataPlugin'

// Utils
export { emitter, bind_handlers, unbind_handlers } from './emitter'

// Default export for Vue plugin
export default {
    install(app, options) {
        app.use(markdownPlugin)
        app.use(websocketPlugin)
        app.use(userDataPlugin)
    }
}
