const MarkdownViewer = {
    data: function () {
        return {
            markdownContent: 'loading...',
            renderedContent: '',
            viewMode: 'rendered', // Ensure this is initialized
        };
    },
    methods: {
        handleWSMessage: function(payload) {
            console.log('handleWSMessage', payload);
            if (payload.content !== undefined) {
                this.updateContent(payload.content);
            }
            if (payload.viewMode !== undefined) {
                this.updateViewMode(payload.viewMode);
            }
        },

        updateContent: function(newContent) {
            this.markdownContent = newContent;
            this.renderMarkdown();
        },
        updateViewMode: function(newViewMode) {
            this.viewMode = newViewMode;
        },

        renderMarkdown: function() {
            // md is defined in the global scope in agi-green.js
            //const md = new markdownit().use(markdownitFootnote);
            this.renderedContent = md.render(this.markdownContent);
            // Optionally process with Mermaid, MathJax, etc., after rendering
        },
        showSource: function() {
            this.viewMode = 'source';
        },
        showRendered: function() {
            this.viewMode = 'rendered';
        }
    },
    template: `
        <div>
            <div id="md-button-container">
                <button @click="showSource" class="button-unselected">
                    <img src="/images/md-source.png" alt="Markdown Source">
                </button>
                <button @click="showRendered" class="button-selected">
                    <img src="/images/md-render.png" alt="Markdown Rendered">
                </button>
            </div>

            <div v-if="viewMode === 'source'" id="md-source">
                <pre><code>{{ markdownContent }}</code></pre>
            </div>
            <div v-else id="md-render" v-html="renderedContent">
            </div>
        </div>
    `,
};

function createMarkdownViewerInstance(payload) {
    const container = document.createElement('div');
    container.setAttribute('class', 'markdown-viewer-instance');
    document.getElementById('markdown-viewers').appendChild(container);

    new Vue({
        el: container,
        data() {
            return {
                markdownContent: payload.content || 'loading...',
                viewMode: payload.viewMode || 'rendered',
            };
        },
        mixins: [MarkdownViewer], // Mixin the MarkdownViewer component logic
    });
}


on_ws_md = function(payload) {
    app.handleWSMessage(payload);
}

