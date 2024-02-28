import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import jsYaml from 'js-yaml';
import mermaid from 'mermaid';

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
    if (typeof mermaid !== 'undefined') {

        mermaid.init(undefined, document.querySelectorAll('.language-mermaid'));
    } else {
        console.warn("Mermaid not loaded.");
    }

    // Process MathJax if needed
    if (window.MathJax) {
        window.MathJax.typesetPromise();
    } else {
        console.warn("MathJax not loaded.");
    }
}



export { processMarkdown, postRender };
