import { reactive } from 'vue';

export const userData = reactive({});

export default {
    install(app, options) {
        app.provide('userData', userData);
    }
};
