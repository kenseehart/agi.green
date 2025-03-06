<template>
    <component :is="activeLayout" />
</template>

<script setup>
import TwoPaneLayout from '@agi.green/layouts/TwoPaneLayout.vue';

// For now, just use TwoPaneLayout directly
// Later this can be configured by the application
const activeLayout = TwoPaneLayout;
</script>
