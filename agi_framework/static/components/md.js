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

function fetchAndRenderMarkdown() {
    const mdDiv = document.getElementById('md-div');
    if (!mdDiv) {
        return;
    }
    const mdSource = document.getElementById('md-source');
    const mdRendered = document.getElementById('md-render');
    const filename = mdDiv.getAttribute('data-src');
    const view = mdDiv.getAttribute('data-view');
    console.log('filename:', filename, 'view:', view);
    fetch(filename+ '?t=' + new Date().getTime()) // fetch the markdown source
        .then(response => response.text())
        .then(text => {
            setTextWithNewlines(mdSource, text);
            autoResize.call(mdSource);
            const renderedContent = md.render(text)
            mdRendered.innerHTML = renderedContent;
            autoResize.call(mdRendered);
            mermaid.init(undefined, mdRendered.querySelectorAll('.language-mermaid'));
            window.MathJax.typesetPromise([mdRendered]);
            if (view === 'source') {
                showSource();
            }
            else {
                showRendered();
            }
        });
}

fetchAndRenderMarkdown();
