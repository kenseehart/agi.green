// Import markdownit and any other dependencies
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js'; // Assuming you're using highlight.js for syntax highlighting

const md = new MarkdownIt({
    html: true,
    linkify: true,
    typographer: false,
    highlight: function (str, lang) {
    if (lang && hljs.getLanguage(lang)) {
        try {
        return hljs.highlight(str, { language: lang }).value;
        } catch (_) {}
    }
    return ''; // Use external default escaping
    },
});

const escapeHtml = (text) => {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
        '\n': '<br>',
    };
    return text.replace(/[&<>"'\n]/g, (m) => map[m]);
};

export { md, escapeHtml };
