

const md = markdownit({

    // Enable HTML in the markdown source
    html: true,
    linkify: true, // Autoconvert URL-like text to links
    typographer: false, // Enable smart quotes and other typographic substitutions

    // Use highlight.js for syntax highlighting
    highlight: function (str, lang) {
        if (lang && hljs.getLanguage(lang)) {
            try {
                return hljs.highlight(str, {language: lang}).value;
            } catch (__) {}
        }
        return ''; // Use external default escaping
    }
});

if (window.markdownitFootnote) {
    md.use(window.markdownitFootnote);
}
else {
    console.log('markdownitFootnote not found');
}

function escapeHtml(text) {
    var map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
        '\n': '<br>',
    };

    return text.replace(/[&<>"'\n]/g, function(m) { return map[m]; });
}



Vue.component('markdown-viewer', {
    props: {
        markdownContent: {
            type: String,
            default: 'loading...'
        },
        viewMode: {
            type: String,
            default: 'rendered' // Possible values: 'rendered', 'source'
        }
    },
    computed: {
        renderedContent() {
            // Use markdown-it to render markdown content
            return md.render(this.markdownContent);
        }
    },
    methods: {
        showSource() {
            this.viewMode = 'source';
        },
        showRendered() {
            this.viewMode = 'rendered';
        },
    },
    template: `
        <div class="md-doc">
            <div> hello</div>
            <div class="md-button-container">
                <button @click="showSource" :class="{'button-selected': viewMode === 'source', 'button-unselected': viewMode !== 'source'}">
                    <img src="/images/md-source.png" alt="Markdown Source">
                </button>
                <button @click="showRendered" :class="{'button-selected': viewMode === 'rendered', 'button-unselected': viewMode !== 'rendered'}">
                    <img src="/images/md-render.png" alt="Markdown Rendered">
                </button>
            </div>
            <div v-if="viewMode === 'source'">
                <pre><code>{{ markdownContent }}</code></pre>
            </div>
            <div v-else v-html="renderedContent">
            </div>
        </div>
    `
});


function on_ws_open_md(payload) {
    openTab(payload.name, 'markdown-viewer', {
        markdownContent: payload.content || 'Loading...',
        viewMode: payload.viewmode || 'rendered',
    });
}
