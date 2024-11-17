import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import python from 'highlight.js/lib/languages/python';
import 'highlight.js/styles/github.css';
import mermaid from 'mermaid';
import { createApp, inject } from 'vue';
import MDForm from '@/components/MDForm.vue'; // Update the path as necessary
import Vueform from '@vueform/vueform';

// Register Python with highlight.js
hljs.registerLanguage('python', python);

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



export { processMarkdown, postRender };
