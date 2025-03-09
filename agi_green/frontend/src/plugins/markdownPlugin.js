import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import python from 'highlight.js/lib/languages/python';
import 'highlight.js/styles/github.css';
import mermaid from 'mermaid';
import { createApp, inject } from 'vue';
import MDForm from '@agi.green/components/MDForm.vue'; 
import Vueform from '@vueform/vueform';

// Register Python with highlight.js
hljs.registerLanguage('python', python);

// Add this helper function at the top level
function formatElapsedTime(timestamp) {
    const diff = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000);

    const days = Math.floor(diff / (24 * 60 * 60));
    const hours = Math.floor((diff % (24 * 60 * 60)) / (60 * 60));
    const minutes = Math.floor((diff % (60 * 60)) / 60);
    const seconds = diff % 60;

    let result = '';
    if (days > 0) result += `${days}d`;
    if (hours > 0) result += `${hours}h`;
    if (minutes > 0) result += `${minutes}m`;
    if (seconds > 0 || result === '') result += `${seconds}s`;

    return result;
}

const md = new MarkdownIt({
    html: true,
    linkify: true,
    typographer: false,
    highlight: function (str, lang) {
        if (lang && hljs.getLanguage(lang)) {
            try {
                return hljs.highlight(str, { language: lang, ignoreIllegals: true }).value;
            } catch (_) {}
        }
        return ''; // Default escaping
    },
});

// Add custom ws_send protocol handler
const defaultRender = md.renderer.rules.link_open || function(tokens, idx, options, env, self) {
    return self.renderToken(tokens, idx, options);
};

md.renderer.rules.link_open = function (tokens, idx, options, env, self) {
    const token = tokens[idx];
    const hrefIndex = token.attrIndex('href');
    if (hrefIndex >= 0) {
        const href = token.attrs[hrefIndex][1];
        if (href.startsWith('ws_send:')) {
            // Split into command and params
            const [command, paramString] = href.replace('ws_send:', '').split('?');

            // Parse URL params into object
            const params = paramString ?
                Object.fromEntries(new URLSearchParams(paramString)) :
                {};

            // Generate onclick handler with properly escaped quotes
            const jsCall = `send_ws('${command}', ${JSON.stringify(params)})`
                .replace(/"/g, '&quot;');

            console.log(`Converting link: ${href} -> onclick:${jsCall}`);

            // Return complete anchor tag with onclick handler
            return `<a href="#" onclick="${jsCall};return false;">`;
        }
    }
    return defaultRender(tokens, idx, options, env, self);
};

// Add custom elapsed time rule
md.inline.ruler.after('emphasis', 'elapsed_time', function elapsed_time(state, silent) {
    const start = state.pos;

    // Look for [since|<timestamp>] pattern
    const isoRegex = /^\[since\|(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)\]/;
    const text = state.src.slice(start);
    const match = text.match(isoRegex);

    if (!match) return false;

    if (!silent) {
        // Get the full matched text and the timestamp capture group
        const fullMatch = match[0];
        const timestamp = match[1];

        console.log(`Found timestamp match: ${fullMatch} -> ${timestamp}`); // Debug log

        // Create a token that represents the text being replaced
        const token = state.push('elapsed_time', '', 0);
        token.content = timestamp;

        // Tell markdown-it how much source text this token consumes
        token.markup = fullMatch;
        token.map = [start, start + fullMatch.length];

        // Advance parser position past the consumed text
        state.pos = start + fullMatch.length;
    } else {
        // In silent mode, just advance the position
        state.pos = start + match[0].length;
    }

    return true;
});

// Add renderer for elapsed time token
md.renderer.rules.elapsed_time = function(tokens, idx) {
    const timestamp = tokens[idx].content;
    const id = `elapsed-${Math.random().toString(36).substring(2, 9)}`;

    console.log(`Rendering elapsed time for ${timestamp}`); // Debug log

    // Initialize the update interval when the element is mounted
    setTimeout(() => {
        const element = document.getElementById(id);
        if (element) {
            const updateTime = () => {
                element.textContent = formatElapsedTime(timestamp);
            };
            updateTime(); // Initial update
            setInterval(updateTime, 1000); // Update every second
        }
    }, 0);

    return `<span id="${id}">...</span>`;
};

// Add any custom rules or logic here, e.g., for forms or Mermaid

// Export a function to process Markdown content
function processMarkdown(content) {
    return md.render(content);
}

// Post-render function to initialize Mermaid diagrams and MathJax
function postRender() {
    // Mermaid
    if (typeof mermaid !== 'undefined') {
        mermaid.init(undefined, document.querySelectorAll('.language-mermaid'));
    } else {
        console.warn("Mermaid not loaded.");
    }

    // Vueform yaml
    document.querySelectorAll('.language-form-yaml').forEach(block => {
        const yamlContent = block.textContent || block.innerText;
        const formContainer = document.createElement('div');
        const formApp = createApp(MDForm, { yamlSchema: yamlContent });
        formApp.use(Vueform);
        block.parentNode.parentNode.replaceChild(formContainer, block.parentNode);
        formApp.mount(formContainer);
    });

    // Vueform json
    document.querySelectorAll('.language-form-json').forEach(block => {
        const jsonContent = block.textContent || block.innerText;
        const formContainer = document.createElement('div');
        const formApp = createApp(MDForm, { jsonSchema: jsonContent });
        formApp.use(Vueform);
        block.parentNode.parentNode.replaceChild(formContainer, block.parentNode);
        formApp.mount(formContainer);
    });

    // MathJax
    if (window.MathJax) {
        window.MathJax.typesetPromise();
    } else {
        console.warn("MathJax not loaded.");
    }
}

// Add default export for Vue plugin
export default {
    install(app, options) {
        app.provide('processMarkdown', processMarkdown);
        app.provide('postRender', postRender);
    }
};

export { processMarkdown, postRender };
