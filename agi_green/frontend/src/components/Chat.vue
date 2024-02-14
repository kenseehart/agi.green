<template>
    <div>
        <div id="messages" class="messages">
            <div v-for="msg in chatMessages" :key="msg.id" class="chat-message-block">
                <Avatar
                    :image="getUserIcon(msg.user)"
                    :alt="`${getUser(msg.user).name}'s avatar`"
                    :title="getUser(msg.user).name"
                    shape="circle"
                />
                <div class="chat-message" v-html="msg.content"></div>
            </div>
        </div>
        <textarea id="chat-input-text" v-model="message" @input="autoResize" placeholder="Type your message here..."></textarea>
        <button @click="onChatInput">Send</button>
    </div>
</template>

<script setup>
    import { ref, onMounted, getCurrentInstance, onBeforeUnmount, inject } from 'vue';
    import MarkdownIt from 'markdown-it';
    import { userData } from '@/plugins/userDataPlugin';
    import emitter, { bind_handlers, unbind_handlers } from '@/emitter';
    import Avatar from 'primevue/avatar';

    const send_ws = inject('send_ws');

    const chatMessages = ref([]);
    const message = ref('');
    const md = new MarkdownIt();

    const autoResize = (event) => {
        event.target.style.height = 'auto';
        event.target.style.height = event.target.scrollHeight + 'px';
    };

    const onChatInput = () => {
        const trimmedMessage = message.value.trim();
            if (trimmedMessage) {
                send_ws('chat_input', { content: trimmedMessage });
                message.value = ''; // Clear the input field after sending
            }
    };

    const { proxy } = getCurrentInstance();

    // Function to get user data or default values
    const getUser = (userId) => {
        return userData[userId] || { name: 'Unknown', icon: '/images/default_avatar.png' };
    };

    // Helper to get user icon
    const getUserIcon = (userId) => {
        return getUser(userId).icon;
    };

    const handlers = {
        ws_append_chat: (msg) => {
            chatMessages.value.push({
                id: Date.now(), // Consider a more robust ID strategy
                user: msg.author,
                content: md.render(msg.content),
            });
        },
    };

    onMounted(() => {
        bind_handlers(handlers);
    });

    // Cleanup event listeners to prevent memory leaks
    onBeforeUnmount(() => {
        unbind_handlers(handlers);
    });
</script>

<style scoped>
/* Your styles remain unchanged */
</style>
