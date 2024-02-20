import { reactive } from 'vue';

import { bind_handlers } from '@/emitter';

export const userData = reactive({});

export default {
    install(app, options) {
    // Listen for WebSocket messages to set user data

        bind_handlers({
            ws_set_user_data: ({ uid, name, icon }) => {
                if (!uid) return;

                userData[uid] = { name, icon };
            }
        });
    }
};
