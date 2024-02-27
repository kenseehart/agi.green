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

md.use(function (md) {
    const defaultRender = md.renderer.rules.html_block || function (tokens, idx, options, env, self) {
        return self.renderToken(tokens, idx, options);
    };

    md.renderer.rules.html_block = function (tokens, idx, options, env, self) {
        const token = tokens[idx];
        if (token.content.startsWith('<!-- Form')) {
            const jsonString = token.content.replace('<!-- Form', '').replace('-->', '').trim();
            try {
                const formData = JSON.parse(jsonString);
                // Store this formData in a way that your Vue component can access
                // For example, by adding it to the environment (env)
                if (!env.forms) env.forms = [];
                env.forms.push(formData);
                return ''; // Don't render the comment directly
            } catch (e) {
                console.error('Error parsing form JSON:', e);
                return '';
            }
        }
        return defaultRender(tokens, idx, options, env, self);
    };
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
