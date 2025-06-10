# AGI.Green Frontend Components

This directory contains the core components used in the AGI.Green frontend.

## Components

### Chat.vue
Chat component that displays messages and provides a text input for conversation.

### MDForm.vue
Markdown editor component with real-time preview.

### DocTabs.vue
Tabbed document interface for displaying multiple documents.

### ResizableLayout.vue
Resizable multi-pane layout component that provides a flexible grid structure with adjustable panes.

## Usage Examples

### ResizableLayout

The ResizableLayout component provides a flexible way to create resizable pane layouts:

```vue
<template>
  <ResizableLayout :config="paneConfig">
    <template #left-pane>
      <!-- Content for left pane -->
    </template>
    
    <template #center-pane>
      <!-- Content for center pane -->
    </template>
    
    <template #right-pane>
      <!-- Content for right pane -->
    </template>
  </ResizableLayout>
</template>

<script>
import { ResizableLayout } from 'agi.green'

export default {
  components: {
    ResizableLayout
  },
  data() {
    return {
      paneConfig: [
        {
          name: 'left-pane',   // Used as slot name
          class: 'my-left-pane', // Optional custom class
          width: 20,           // Initial width percentage
          minWidth: 20,        // Minimum width percentage 
          maxWidth: 60         // Maximum width percentage
        },
        {
          name: 'center-pane',
          class: 'my-center-pane',
          width: 60,
          minWidth: 20,
          maxWidth: 80
        },
        {
          name: 'right-pane',
          class: 'my-right-pane',
          width: 20,
          minWidth: 20,
          maxWidth: 60
        }
      ]
    }
  }
}
</script>
```

The `config` prop takes an array of pane configurations, with each pane having:
- `name`: The slot name for this pane (required)
- `class`: Custom CSS class (optional)
- `width`: Initial width as percentage (default: evenly divided)
- `minWidth`: Minimum width percentage (default: 10)
- `maxWidth`: Maximum width percentage (default: 80)

Splitters are automatically added between panes, and the resizing behavior is handled by the component.
