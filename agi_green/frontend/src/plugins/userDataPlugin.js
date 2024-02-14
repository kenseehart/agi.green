import { reactive } from 'vue';

import { emitter, bind_handlers, unbind_handlers } from '@/emitter';

export const userData = reactive({});

export default {
    install(app) {
    // Listen for WebSocket messages to set user data

        bind_handlers({
            on_ws_set_user_data: ({ uid, name, icon }) => {
                if (!uid) return;

                userData[uid] = { name, icon };
            }
        });
    }
};
