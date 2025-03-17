<template>
  <div class="agi-green-layout-container">
    <!-- Interleave panes and splitters: Pane 1, Splitter 1, Pane 2, Splitter 2, Pane 3, etc. -->
    <template v-for="(pane, index) in panes" :key="'pane-' + index">
      <!-- Render Pane -->
      <div
        class="agi-green-pane"
        :class="pane.class"
        :style="{ width: pane.width + '%' }"
      >
        <slot :name="pane.name"></slot>
      </div>
      
      <!-- Render Splitter (except after the last pane) -->
      <div
        v-if="index < panes.length - 1"
        class="agi-green-splitter"
        :class="'splitter-' + index"
        @mousedown="startResize($event, index)"
      ></div>
    </template>
  </div>
</template>

<script>
/**
 * Component: ResizableLayout
 * Description: A flexible multi-pane layout component with resizable panes
 *
 * Props:
 *   - config: Array of pane configurations {name, class, width, minWidth, maxWidth}
 *
 * Example Usage:
 * <ResizableLayout :config="[
 *    { name: 'left', width: 20, minWidth: 10, maxWidth: 50 },
 *    { name: 'center', width: 60, minWidth: 30, maxWidth: 80 },
 *    { name: 'right', width: 20, minWidth: 10, maxWidth: 50 }
 * ]">
 *   <template #left>Left Pane Content</template>
 *   <template #center>Center Pane Content</template>
 *   <template #right>Right Pane Content</template>
 * </ResizableLayout>
 */
export default {
  name: 'ResizableLayout',
  props: {
    // Pane configuration: array of {name, class, width, minWidth, maxWidth}
    config: {
      type: Array,
      required: true
    }
  },
  data() {
    return {
      isResizing: false,
      currentSplitter: null,
      startX: 0,
      panes: [],
      splitters: []
    }
  },
  created() {
    this.initializeLayout();
  },
  mounted() {
    window.addEventListener('mousemove', this.onMouseMove);
    window.addEventListener('mouseup', this.onMouseUp);
    window.addEventListener('mouseleave', this.onMouseUp);
    
    // Load external CSS if not already loaded
    this.loadLayoutStyles();
  },
  beforeUnmount() {
    window.removeEventListener('mousemove', this.onMouseMove);
    window.removeEventListener('mouseup', this.onMouseUp);
    window.removeEventListener('mouseleave', this.onMouseUp);
  },
  methods: {
    loadLayoutStyles() {
      // Check if styles are already loaded
      if (!document.getElementById('agi-green-resizable-layout-styles')) {
        const link = document.createElement('link');
        link.id = 'agi-green-resizable-layout-styles';
        link.rel = 'stylesheet';
        link.href = '/resizable-layout.css';
        document.head.appendChild(link);
      }
    },
    initializeLayout() {
      // Initialize panes from config
      this.panes = this.config.map((item, index) => ({
        name: item.name || `pane-${index}`,
        class: item.class || '',
        width: item.width || 100 / this.config.length,
        minWidth: item.minWidth || 10,
        maxWidth: item.maxWidth || 80
      }));
      
      // No longer need to create splitters array as we handle them in the template
      this.splitters = [];
    },
    startResize(event, splitterIndex) {
      this.isResizing = true;
      this.currentSplitter = {
        leftPaneIndex: splitterIndex,
        rightPaneIndex: splitterIndex + 1
      };
      this.startX = event.clientX;
      
      // Add resizing class for styling
      document.body.classList.add('agi-green-resizing');
      
      // Prevent text selection during resize
      event.preventDefault();
    },
    onMouseMove(event) {
      if (!this.isResizing || !this.currentSplitter) return;
      
      const deltaX = event.clientX - this.startX;
      if (deltaX === 0) return;
      
      const containerWidth = this.$el.clientWidth;
      const deltaPercentage = (deltaX / containerWidth) * 100;
      
      const leftPaneIndex = this.currentSplitter.leftPaneIndex;
      const rightPaneIndex = this.currentSplitter.rightPaneIndex;
      
      // Calculate new widths
      let newLeftWidth = this.panes[leftPaneIndex].width + deltaPercentage;
      let newRightWidth = this.panes[rightPaneIndex].width - deltaPercentage;
      
      // Enforce min/max constraints
      const leftMinWidth = this.panes[leftPaneIndex].minWidth;
      const leftMaxWidth = this.panes[leftPaneIndex].maxWidth;
      const rightMinWidth = this.panes[rightPaneIndex].minWidth;
      const rightMaxWidth = this.panes[rightPaneIndex].maxWidth;
      
      if (newLeftWidth < leftMinWidth) {
        const excess = leftMinWidth - newLeftWidth;
        newLeftWidth = leftMinWidth;
        newRightWidth += excess;
      } else if (newLeftWidth > leftMaxWidth) {
        const excess = newLeftWidth - leftMaxWidth;
        newLeftWidth = leftMaxWidth;
        newRightWidth += excess;
      }
      
      if (newRightWidth < rightMinWidth) {
        const excess = rightMinWidth - newRightWidth;
        newRightWidth = rightMinWidth;
        newLeftWidth -= excess;
      } else if (newRightWidth > rightMaxWidth) {
        const excess = newRightWidth - rightMaxWidth;
        newRightWidth = rightMaxWidth;
        newLeftWidth -= excess;
      }
      
      // Update pane widths
      this.panes[leftPaneIndex].width = newLeftWidth;
      this.panes[rightPaneIndex].width = newRightWidth;
      
      // Update start position for next movement
      this.startX = event.clientX;
    },
    onMouseUp() {
      if (this.isResizing) {
        this.isResizing = false;
        this.currentSplitter = null;
        document.body.classList.remove('agi-green-resizing');
      }
    }
  }
}
</script>
