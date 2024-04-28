<template>
    <svg @mouseover="hover = true" @mouseleave="hover = false"
         @mousedown="active = true" @mouseup="active = false" @click="handleClick"
         style="overflow: visible; cursor: pointer;">

      <rect :x="computedX" :y="computedY"
            :width="buttonMetrics.width" :height="buttonMetrics.height"
            :rx="padding" :ry="padding"
            class="button-rect"/>
      <text :x="computedTextX" :y="computedTextY"
            :font-size="fontSize" :text-anchor="textAnchor">
        {{ label }}
      </text>
    </svg>
</template>

<script setup>
import { ref, computed } from 'vue';
import { defineProps, defineEmits } from 'vue';

const props = defineProps({
  label: String,
  x: Number,
  y: Number,
  fontSize: Number,
  textAnchor: String
});

const emit = defineEmits(['clicked']);
const textRef = ref(null);

const padding = computed(() => parseFloat(props.fontSize) * 0.20);

const buttonMetrics = computed(() => {
  if (textRef.value) {
    const bbox = textRef.value.getBBox();
    const xOffset = (props.textAnchor === 'end') ? -bbox.width : 0;

    return {
      width: bbox.width + 2 * padding.value,
      height: bbox.height + 2 * padding.value
    };
  }
  return { width: 0, height: 0 };
});

const computedX = computed(() => props.x + (props.textAnchor === 'end' ? -buttonMetrics.value.width : 0));
const computedY = computed(() => props.y - buttonMetrics.value.height / 2);
const computedTextX = computed(() => props.x);
const computedTextY = computed(() => props.y);

const handleClick = () => {
  emit('clicked');
};
</script>

<style>
.button-rect {
  fill: orange; /* default fill */
  stroke: black; /* default stroke */
  transition: fill 0.3s ease; /* smooth transition for hover effects */
  stroke-width: 0.001;
  pointer-events: all; /* ensure pointer events apply to the whole rectangle */
}

.button-rect:hover {
  fill: yellow; /* hover color */
}
</style>