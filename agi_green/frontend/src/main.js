import { createApp } from 'vue'
import App from './App.vue'
import PrimeVue from 'primevue/config';

import 'primevue/resources/themes/saga-blue/theme.css'; // theme
import 'primevue/resources/primevue.min.css'; // core css
import 'primeicons/primeicons.css'; // icons

import WebSocketPlugin from './plugins/websocketPlugin';
import UserDataPlugin from './plugins/userDataPlugin';
//import {md, escapeHtml} from './plugins/markdownPlugin';

import DocTabs from './components/DocTabs.vue';
import MarkdownView from './components/Markdown.vue';
import Chat from './components/Chat.vue';

import PerfectScrollbar from 'vue3-perfect-scrollbar'
import 'vue3-perfect-scrollbar/dist/vue3-perfect-scrollbar.css'

const app = createApp(App);

app.use(PrimeVue);
app.use(WebSocketPlugin);
app.use(UserDataPlugin);
app.use(PerfectScrollbar)
app.component('DocTabs', DocTabs);
app.component('MarkdownView', MarkdownView);
app.component('Chat', Chat);

app.mount('#app');
