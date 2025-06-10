<template>
    <component :is="activeLayout">
        <template #left-pane>
            <MDForm />
        </template>
        <template #center-pane>
            <Chat />
        </template>
        <template #right-pane>
            <DocTabs />
        </template>
    </component>
</template>

<script setup>
import TwoPaneLayout from './layouts/TwoPaneLayout.vue';
import Chat from './components/Chat.vue';
import MDForm from './components/MDForm.vue';
import DocTabs from './components/DocTabs.vue';

// Default to TwoPaneLayout since ThreePaneLayout will be provided by the application
const activeLayout = TwoPaneLayout;
</script>
