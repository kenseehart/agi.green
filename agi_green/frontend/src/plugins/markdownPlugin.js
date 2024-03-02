import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import mermaid from 'mermaid';
import { createApp } from 'vue';
import MDForm from '@/components/MDForm.vue'; // Update the path as necessary
import Vueform from '@vueform/vueform';

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
