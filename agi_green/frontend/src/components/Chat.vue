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
    <div class="agi-green-flex-container">
        <div id="messages" class="agi-green-messages">
            <div v-for="msg in chatMessages" :key="msg.id" class="agi-green-chat-message-block">
                <Avatar
                    :image="getUserIcon(msg.user)"
                    :alt="`${getUser(msg.user).name}'s avatar`"
                    :title="getUser(msg.user).name"
                    shape="circle"
                />
                <div class="agi-green-message-content">
                <div class="agi-green-username">{{ getUser(msg.user).name }}</div>
                <div class="agi-green-chat-message" v-html="msg.content"></div>
                </div>
            </div>
            <div class="agi-green-chat-input-container">
                <textarea id="chat-input-text" v-model="message" @input="autoResize" @keyup.enter="onEnterPress" placeholder="Type your message here..."></textarea>
                <button class="agi-green-chat-send-button" @click="onChatInput">
                    <img src="../assets/send-button.png" alt="Send" />
                </button>
            </div>
        </div>
    </div>
</template>


<script setup>
import { ref, onMounted, getCurrentInstance, onBeforeUnmount, watchEffect, inject, nextTick } from 'vue';
import { processMarkdown, postRender } from '../plugins/markdownPlugin';
import { userData } from '../plugins/userDataPlugin';
import { bind_handlers, unbind_handlers } from '../emitter';
import Avatar from 'primevue/avatar';
import { useFileDrop } from '../composables/useFileDrop';

const send_ws = inject('send_ws');

const chatMessages = ref([]);
const message = ref('');

const autoResize = (event) => {
    // Store the original scroll position
    const messagesContainer = document.getElementById('messages');
    const scrollTop = messagesContainer ? messagesContainer.scrollTop : 0;
    
    // Get the original height for comparison
    const originalHeight = event.target.style.height;
    
    // Reset height to properly calculate the new scrollHeight
    event.target.style.height = 'auto';
    
    // Set new height based on content
    const newHeight = event.target.scrollHeight + 5 + 'px';
    event.target.style.height = newHeight;
    
    // If this is an expansion (not first load or shrinking), maintain the scroll position
    if (messagesContainer && originalHeight && parseInt(newHeight) > parseInt(originalHeight)) {
        messagesContainer.scrollTop = scrollTop;
    }
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
            scrollToBottom();
        });
    },
    ws_set_user_data: ({ uid, name, icon }) => {
        console.log('ws_set_user_data received:', { uid, name, icon });
        if (!uid) return;
        userData[uid] = { name, icon };
    }
};

// Scroll to the bottom of the chat
const scrollToBottom = () => {
    const messagesContainer = document.getElementById('messages');
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
};

onMounted(() => {
    bind_handlers(handlers);
    // Initial scroll to bottom
    nextTick(() => {
        scrollToBottom();
    });
});

// Cleanup event listeners to prevent memory leaks
onBeforeUnmount(() => {
    unbind_handlers(handlers);
});
</script>

<style scoped>
textarea {
    width: calc(100% - 50px);
    padding: 10px;
    padding-right: 40px;
    resize: vertical;
    border-radius: 4px;
    margin: 10px 0 0 0;
    box-sizing: border-box;
    flex-grow: 1;
    min-height: 50px;
    position: relative;
    top: 0;
}

.avatar {
    width: 40px;
    height: 40px;
    margin-right: 10px;
    flex-shrink: 0;
}
</style>
