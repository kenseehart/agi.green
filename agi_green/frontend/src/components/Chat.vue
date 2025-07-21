/**
 * Component: Chat
 * Description: A chat component that displays chat messages and allows users to send new messages.
 *
 * Props:
 *   - ariaFeedbackLike: A string that is used as the aria-label for the like button.
 *   - ariaFeedbackDislike: A string that is used as the aria-label for the dislike button.
 *   - placeholder: A string that is used as the placeholder for the textarea.
 *
 * Data:
 *   - chatMessages: An array of chat messages.
 *   - message: The current message being typed by the user.
 *   - messageFeedback: An object that tracks feedback state for each message.
 *
 * Methods:
 *   - autoResize: A method that automatically resizes the textarea based on its content.
 *   - onChatInput: A method that sends the chat message when the user clicks the send button.
 *   - getUser: A method that retrieves user data based on the user ID.
 *   - getUserIcon: A method that retrieves the user's avatar icon based on the user ID.
 *   - sendFeedback: A method that sends feedback for a message.
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
                <Avatar :image="getUserIcon(msg.user)" :alt="`${getUser(msg.user).name}'s avatar`"
                    :title="getUser(msg.user).name" shape="circle" />
                <div class="agi-green-message-content">
                    <div class="agi-green-username">{{ getUser(msg.user).name }}</div>
                    <div class="agi-green-chat-message" v-html="msg.content"></div>
                    <!-- Add feedback to the message if the user is Aria and the message is not a welcome message -->
                    <template id="message-feedback-template"
                        v-if="shouldShowFeedback(msg)">
                        <div class="message-feedback-section">
                            <button class="feedback-button thumbs-up" :title="props.ariaFeedbackLike">
                                <span class="material-symbols-outlined" :aria-label="props.ariaFeedbackLike"
                                    :class="{ 'feedback-selected': messageFeedback[msg.id] === true }"
                                    @click="sendFeedback(msg.id, true)">thumb_up</span>
                            </button>
                            <button class="feedback-button thumbs-down" :title="props.ariaFeedbackDislike">
                                <span class="material-symbols-outlined" :aria-label="props.ariaFeedbackDislike"
                                    :class="{ 'feedback-selected': messageFeedback[msg.id] === false }"
                                    @click="sendFeedback(msg.id, false)">thumb_down</span>
                            </button>
                        </div>
                    </template>
                    <!-- End of feedback -->
                </div>
            </div>


            <!-- Tax Progress Bar -->
            <div v-if="showTaxProgress" class="agi-green-chat-message-block">
                <Avatar
                    :image="getUserIcon('Aria')"
                    :alt="'Aria\'s avatar'"
                    :title="'Aria'"
                    shape="circle"
                />
                <div class="agi-green-message-content">
                <div class="agi-green-username">Aria</div>
                <div class="agi-green-chat-message">
                    <TaxProgressBar
                        :status="taxProgressStatus"
                        :current-step="taxProgressStep"
                        :total-steps="5"
                        :status-text="taxProgressText"
                    />
                </div>
                </div>

            </div>

            <ChatInput v-model="message" @input="autoResize" @send="onChatInput" @file="handleFileUpload" :placeholder="props.placeholder"/>
        </div>
    </div>
</template>


<script setup>
import { ref, onMounted, getCurrentInstance, onBeforeUnmount, watchEffect, inject, nextTick } from 'vue';
import { processMarkdown, postRender } from '../plugins/markdownPlugin';
import { userData } from '../plugins/userDataPlugin';
import { bind_handlers, unbind_handlers } from '../emitter';
import Avatar from 'primevue/avatar';
import ChatInput from './ChatInput.vue';
import TaxProgressBar from './TaxProgressBar.vue';
import { useFileDrop } from '../composables/useFileDrop';
import { array } from '@vueform/vueform';
import MDForm from './MDForm.vue';
const send_ws = inject('send_ws');

const chatMessages = ref([]);
const message = ref('');
const isProgressMessage = ref(false);
const messageFeedback = ref({}); // Track feedback state for each message
const props = defineProps({
    agentName: {
        type: String,
        default: 'Aria'
    },
    skipFeedback: {
        type: Array,
        default: () => ['Welcome', 'How can I']
    },
    ariaFeedbackLike: {
        type: String,
        default: 'Like'
    },
    ariaFeedbackDislike: {
        type: String,
        default: 'Dislike'
    },

    placeholder: {
        type: String,
        default: 'Ask anything or upload a file'
    },
     showFileUpload: {
        type: Boolean,
        default: true
    }
});

// Tax progress tracking
const showTaxProgress = ref(false);
const taxProgressStatus = ref('idle');
const taxProgressStep = ref(0);
const taxProgressText = ref('Ready to process');

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
    chatMessages.value.push({
        t: Date.now(),
        user: 'user',
        content: trimmedMessage
    });
    nextTick(() => {
        postRender();
        scrollToBottom();
    });
};

const sendFeedback = (messageId, isPositive) => {
    // Add feedback to the message
    // Clear any existing feedback for this message
    messageFeedback.value = {
        ...messageFeedback.value,
        [messageId]: isPositive
    };

    send_ws('feedback', {
        content: isPositive ? props.ariaFeedbackLike : props.ariaFeedbackDislike,
        message_id: messageId
    });
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


// Utility to strip HTML tags
function stripHtml(html) {
    const div = document.createElement('div');
    div.innerHTML = html;
    return div.textContent || div.innerText || '';
}


const shouldShowFeedback = (msg) => {
  return getUser(msg.user).name === props.agentName &&
         !props.skipFeedback.some(text => msg.content.includes(text));
};


const handlers = {
    ws_append_chat: (msg) => {
        // Check if this is a progress-related message that we should handle with the progress bar
        const content = msg.content.toLowerCase();
         isProgressMessage.value = content.includes('received file') ||
                                 content.includes('processing tax file') ||
                                 content.includes('analysis complete') ||
                                 content.includes('excel file is ready') ||
                                 content.includes('csv file detected') ||
                                 content.includes('note: csv file');
        if (isProgressMessage.value && showTaxProgress.value) {
            // Update progress based on message content
            if (content.includes('csv file detected') || content.includes('note: csv file')) {
                // CSV warning - keep at step 1 but update text
                taxProgressStep.value = 1;
                taxProgressText.value = stripHtml(msg.content);
            } else if (content.includes('received file')) {
                taxProgressStep.value = 1;
                taxProgressText.value = msg.content;
            } else if (content.includes('processing tax file')) {
                taxProgressStep.value = 2;
                taxProgressText.value = extractFileNameFromProcessingMsg(msg.content);
            } else if (content.includes('analysis complete')) {
                taxProgressStep.value = 4;
                taxProgressStatus.value = 'complete';
                taxProgressText.value = stripHtml(msg.content);
            } else if (content.includes('excel file is ready')) {
                // This is the final message, set to 100%
                taxProgressStep.value = 5;
                taxProgressStatus.value = 'complete';
                taxProgressText.value = stripHtml(msg.content);

                // Hide progress bar after a delay
                setTimeout(() => {
                    showTaxProgress.value = false;
                    taxProgressStatus.value = 'idle';
                    taxProgressStep.value = 0;
                    isProgressMessage.value = false
                }, 5000); // Show for 5 seconds after completion
            }
        } else {
            // Regular chat message - add to chat
            chatMessages.value.push({
                t: Date.now(),
                user: msg.author,
                content: processMarkdown(msg.content)
            });
            nextTick(() => {
                postRender();
                scrollToBottom();
            });
        }
    },
    ws_set_user_data: ({ uid, name, icon }) => {
        console.log('ws_set_user_data received:', { uid, name, icon });
        if (!uid) return;
        userData[uid] = { name, icon };
    }
};

// Helper to extract just the file name from the processing message
function extractFileNameFromProcessingMsg(msg) {
    // Example: Processing tax file: <span style="color: blue;">ConEd_Golden_5 (1).csv</span>. This may take a few minutes...
    // We want to extract just the file name
    const match = msg.match(/Processing tax file: (.*?)(\.|<|$)/i);
    if (match) {
        // If it's HTML, strip tags
        return stripHtml(match[1]);
    }
    // Fallback: strip all HTML
    return stripHtml(msg);
}

// Scroll to the bottom of the chat
const scrollToBottom = () => {
    const messagesContainer = document.getElementById('messages');
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
};

// Handle file upload from the plus icon button
const handleFileUpload = async (file) => {
    console.log('File selected for upload:', file.name);

    // Validate file type
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (ext !== '.csv' && ext !== '.xlsx') {
        console.error('Invalid file type:', ext);
        return;
    }

    // Validate file size (10GB limit as per backend)
    const maxSize = 10_000_000_000; // 10GB
    if (file.size > maxSize) {
        console.error('File too large:', file.size);
        return;
    }

    // Show progress bar and start progress
     showTaxProgress.value = true;
    // taxProgressStatus.value = 'processing';
    // taxProgressStep.value = 1;
    // taxProgressText.value = `Received file: ${file.name}. Starting analysis...`;

    try {
        const formData = new FormData();
        formData.append('file', file);

        // Include socket_id for response routing
        const socket_id = window.socket_id;
        if (!socket_id) {
            console.error('No socket_id available');
            return;
        }
        formData.append('socket_id', socket_id);

        console.log(`Uploading ${file.name} to /upload/tax with socket_id ${socket_id}`);

        const response = await fetch('/upload/tax', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`);
        }

        // console.log('File uploaded successfully:', file.name);

        // // Update progress to show processing
        // taxProgressStep.value = 2;
        // taxProgressText.value = `Processing tax file: ${file.name}. This may take a few minutes...`;

    } catch (error) {
        console.error('Upload error:', error);
        taxProgressStatus.value = 'error';
        taxProgressText.value = `Upload failed: ${error.message}`;
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

.material-symbols-outlined {
    cursor: pointer;
    transition: color 0.2s ease;
    font-variation-settings: 'FILL' 0;
}


.feedback-button {
    background: none;
    border: none;
    padding: 4px;
    cursor: pointer;
    display: flex;
    align-items: center;
}

.feedback-button:hover .material-symbols-outlined {
    opacity: 0.8;
}

.message-feedback-section {
    margin-top: 8px;
    display: flex;
    gap: 8px;
}

/* .feedback-selected {
    color: #2196F3 !important;
    font-variation-settings: 'FILL' 1 !important;
} */

/* Add link to Material Symbols font if not already present */
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,0');

.agi-green-message-content {
    flex: 1;
    display: flex;
    flex-direction: column;
}

.agi-green-chat-message {
    margin-bottom: 4px;
}
</style>
