/**
 * Component: Chat
 * Description: A chat component that displays chat messages and allows users to send new messages.
 *
 * Props:
 *   - None
 *
 * Data:
 *   - chatMessages: An array of chat messages.
 *   - message: The current message being typed by the user.
 *
 * Methods:
 *   - autoResize: A method that automatically resizes the textarea based on its content.
 *   - onChatInput: A method that sends the chat message when the user clicks the send button.
 *   - getUser: A method that retrieves user data based on the user ID.
 *   - getUserIcon: A method that retrieves the user's avatar icon based on the user ID.
 *
 * Hooks:
 *   - onMounted: A hook that binds event handlers when the component is mounted.
 *   - onBeforeUnmount: A hook that unbinds event handlers when the component is about to be unmounted.
 *
 * Dependencies:
 *   - Vue Composition API
 *   - markdown-it
 *   - userDataPlugin (injected)
 *   - primevue/avatar
 *   - primevue/scrollpanel
 *
 * Slots:
 *   - None
 *
 * Example Usage:
 * <Chat />
 */
<template>
    <div class="flex-container">
        <div id="messages" class="messages">
            <div v-for="msg in chatMessages" :key="msg.id" class="chat-message-block">
                <Avatar
                    :image="getUserIcon(msg.user)"
                    :alt="`${getUser(msg.user).name}'s avatar`"
                    :title="getUser(msg.user).name"
                    shape="circle"
                />
                <div class="message-content">
                <div class="username">{{ getUser(msg.user).name }}</div>
                <div class="chat-message" v-html="msg.content"></div>
                </div>
            </div>
            <div class="input-container">
                <textarea id="chat-input-text" v-model="message" @input="autoResize" @keyup.enter="onEnterPress" placeholder="Type your message here..."></textarea>
                <button class="send-button" @click="onChatInput">
                    <img src="@/assets/send-button.png" alt="Send" />
                </button>
            </div>
        </div>
    </div>
</template>


<script setup>
import { ref, onMounted, getCurrentInstance, onBeforeUnmount, watchEffect, inject, nextTick } from 'vue';
import { processMarkdown, postRender } from '@/plugins/markdownPlugin'; // Assuming this is your custom processing
import { userData } from '@/plugins/userDataPlugin';
import { bind_handlers, unbind_handlers } from '@/emitter';
import Avatar from 'primevue/avatar';
import { useFileDrop } from '@/composables/useFileDrop';

const send_ws = inject('send_ws');

const chatMessages = ref([]);
const message = ref('');

const autoResize = (event) => {
    event.target.style.height = 'auto';
    event.target.style.height = event.target.scrollHeight + 5 + 'px';
};

const onEnterPress = (event) => {
    // Check if only Enter was pressed without Shift
    if (!event.shiftKey) {
        event.preventDefault(); // Prevent the default action to avoid inserting a new line
        onChatInput();
    }
};

const onChatInput = () => {
    const trimmedMessage = message.value.trim();
    if (trimmedMessage) {
        send_ws('chat_input', { content: trimmedMessage });
        message.value = ''; // Clear the input field after sending
    }

    const textarea = document.getElementById('chat-input-text');
    if (textarea) {
        textarea.style.height = '50px';
    }
};

const { proxy } = getCurrentInstance();

// Function to get user data or default values
const getUser = (userId) => {
    return userData[userId] || { name: userId, icon: '/avatars/default_avatar.png' };
};

// Helper to get user icon
const getUserIcon = (userId) => {
    return getUser(userId).icon;
};

const handlers = {
    ws_append_chat: (msg) => {
        chatMessages.value.push({
            t: Date.now(),
            user: msg.author,
            content: processMarkdown(msg.content)
        });
        nextTick(() => {
            postRender();
        });
    },
    ws_set_user_data: ({ uid, name, icon }) => {
        console.log('ws_set_user_data received:', { uid, name, icon });  // Add debug log
        if (!uid) return;
        userData[uid] = { name, icon };
    }
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
.flex-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
}

.messages {
    flex: 1;
    overflow-y: auto;
    padding: 5px;
    padding-bottom: 35px;
    display: flex;
    flex-direction: column;
}

.chat-message-block {
    display: flex;
    align-items: flex-start; /* Keeps items aligned at the top */
    width: 100%; /* Ensures block takes full container width */
}

.avatar {
    width: 40px; /* Set a fixed width */
    height: 40px; /* Set a fixed height */
    margin-right: 10px; /* Add margin between avatar and message */
    flex-shrink: 0; /* Prevents shrinking */
}

.message-content {
    display: flex;
    flex-direction: column;
    flex-grow: 1; /* Allows it to grow and fill available space */
    flex-basis: 0; /* Start with a basis of 0 to grow from there */
    min-width: 0; /* Prevents overflow of the container */
}

.input-container {
    position: relative;
    margin: 1rem;
    display: flex;
    align-items: center;
    height: 80px;
}

textarea {
    width: calc(100% - 50px); /* Adjust based on the send button's width to avoid overlap */
    padding: 10px;
    padding-right: 40px; /* Increase right padding to prevent text from overlapping the send button */
    resize: vertical;
    border-radius: 4px;
    margin: 10px 0;
    box-sizing: border-box;
    flex-grow: 1;
    min-height: 50px;
}

.send-button {
    position: absolute;
    right: 10px;
    bottom: 20px;
    height: 30px;
    width: 30px;
    padding: 10;
    border: none;
    background: none;
    cursor: pointer;
}

.send-button img {
    height: 100%;
    width: 100%;
}

.username {
    font-weight: bold;
    margin-bottom: 5px; /* Space between the username and the message */
}

.chat-message {
    padding: 10px;
    border-radius: 8px;
    word-break: break-word; /* Ensure long words don't overflow */
}
</style>

