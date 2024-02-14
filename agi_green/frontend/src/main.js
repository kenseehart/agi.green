import { createApp } from 'vue'
import App from './App.vue'
import PrimeVue from 'primevue/config';

import 'primevue/resources/themes/saga-blue/theme.css'; // theme
import 'primevue/resources/primevue.min.css'; // core css
import 'primeicons/primeicons.css'; // icons

import WebSocketPlugin from './plugins/websocketPlugin';
import UserDataPlugin from './plugins/userDataPlugin';

const app = createApp(App);

app.use(PrimeVue);
app.use(WebSocketPlugin);
app.use(UserDataPlugin);

app.mount('#app');
