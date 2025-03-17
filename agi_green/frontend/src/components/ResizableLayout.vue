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
  },
  beforeUnmount() {
    window.removeEventListener('mousemove', this.onMouseMove);
    window.removeEventListener('mouseup', this.onMouseUp);
    window.removeEventListener('mouseleave', this.onMouseUp);
  },
  methods: {
    initializeLayout() {
      // Initialize panes from config
      this.panes = this.config.map((item, index) => ({
        name: item.name || `pane-${index}`,
        class: item.class || '',
        width: item.width || 100 / this.config.length,
        minWidth: item.minWidth || 10,
        maxWidth: item.maxWidth || 80
      }));
      
      // Validate and normalize initial widths to ensure they sum to 100%
      const totalWidth = this.panes.reduce((sum, pane) => sum + pane.width, 0);
      if (Math.abs(totalWidth - 100) > 0.1) {
        // Adjust all panes proportionally
        const factor = 100 / totalWidth;
        this.panes.forEach(pane => {
          pane.width = pane.width * factor;
        });
      }
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
      
      // Get current widths
      const leftWidth = this.panes[leftPaneIndex].width;
      const rightWidth = this.panes[rightPaneIndex].width;
      
      // Calculate new widths
      let newLeftWidth = leftWidth + deltaPercentage;
      let newRightWidth = rightWidth - deltaPercentage;
      
      // Enforce min/max constraints
      const leftMinWidth = this.panes[leftPaneIndex].minWidth;
      const leftMaxWidth = this.panes[leftPaneIndex].maxWidth;
      const rightMinWidth = this.panes[rightPaneIndex].minWidth;
      const rightMaxWidth = this.panes[rightPaneIndex].maxWidth;
      
      if (newLeftWidth < leftMinWidth) {
        newLeftWidth = leftMinWidth;
        newRightWidth = rightWidth - (newLeftWidth - leftWidth);
      } else if (newLeftWidth > leftMaxWidth) {
        newLeftWidth = leftMaxWidth;
        newRightWidth = rightWidth - (newLeftWidth - leftWidth);
      }
      
      if (newRightWidth < rightMinWidth) {
        newRightWidth = rightMinWidth;
        newLeftWidth = leftWidth + (rightWidth - newRightWidth);
      } else if (newRightWidth > rightMaxWidth) {
        newRightWidth = rightMaxWidth;
        newLeftWidth = leftWidth + (rightWidth - newRightWidth);
      }
      
      // Ensure total width hasn't changed
      const widthDelta = (newLeftWidth + newRightWidth) - (leftWidth + rightWidth);
      if (Math.abs(widthDelta) > 0.01) {
        // Adjust to maintain total width
        newRightWidth = rightWidth + (leftWidth - newLeftWidth);
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
