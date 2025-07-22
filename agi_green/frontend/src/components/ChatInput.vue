<template>
  <div class="input-container" style="display: flex;align-items: center;">
    <textarea
    v-model="modelValue"
    :placeholder="props.placeholder"
      @input="handleInput"
      @keyup.enter="onEnterPress"
      class="text-input"
      id="chat-input-text"
    ></textarea>
    <!-- <div @click="triggerFileInput" class="attach-button">
      <img src="../assets/plusIcon.svg" alt="Attach file"  style="width:30px; height:30px;"/>
    </div> -->
    <input
      ref="fileInput"
      type="file"
      accept=".csv,.xlsx"
      @change="handleFileSelect"
      hidden
    />
  </div>
</template>

<script setup>
import { ref } from 'vue';

const emit = defineEmits(['send', 'file', 'input']);
const text = ref('');
const isTyping = ref(false);
const fileInput = ref(null);
const modelValue = defineModel();
const props = defineProps({
  placeholder: {
        type: String,
        default: 'Ask anything or upload a file'
    }
})
function handleInput(e) {
  text.value = e.target.value;
  isTyping.value = !!text.value.trim();
  emit('input', e);
}

function onEnterPress(event) {
  if (event.key === 'Enter') {
    if (event.shiftKey) {
      // Allow newline — do nothing
      return;
    } else {
      event.preventDefault(); // prevent newline
      emit('send');
    }
  }
}

function triggerFileInput() {
  fileInput.value.click();
}

function handleFileSelect(event) {
  const file = event.target.files[0];
  if (file) {
    emit('file', file);
    event.target.value = '';
  }
}
</script>

<style scoped>
.input-container {
display: flex !important;
gap: 10px;
justify-content:center !important;
}

.text-input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  resize: vertical;
  min-height: 50px;
  box-sizing: border-box;
  font-family: inherit;
  height: 40px !important
}

.text-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

.attach-button {
  width: 50px;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background-color: #ffffff;
  cursor: pointer;
  color: #6b7280;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.attach-button img {
  width: 50px;
  height: 50px;
}

.attach-button:hover {
  background-color: #f9fafb;
  border-color: #9ca3af;
  color: #374151;
}
</style>
