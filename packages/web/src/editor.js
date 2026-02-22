/**
 * Monaco editor setup — loads from CDN, creates a markdown editor.
 */

const MONACO_CDN = "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min";

const DEFAULT_CONTENT = `\
/title My Zine

# My Zine

## A zinewire project

/page
/two-columns

## Getting Started

Write your content in **markdown**. Use zinewire directives to control layout:

- \`/page\` — start a new page
- \`/two-columns\` — switch to two-column layout
- \`/column\` — move to the next column
- \`/cover image.jpg\` — add a cover page

/column

## Why Zines?

- **No gatekeepers** --- publish what you want
- **Cheap** --- a photocopier and stapler is all you need
- **Personal** --- your voice, your rules
- **Tangible** --- a real thing in a digital world

> *"The best zine is the one that exists."*

/page
/one-column

That's it. Edit the markdown on the left and see your zine on the right.

*Made with zinewire.*
`;

/**
 * Load Monaco editor from CDN and create an editor instance.
 * @param {HTMLElement} container
 * @param {function(string): void} onChange - called with editor content on change
 * @returns {Promise<object>} Monaco editor instance
 */
export async function createEditor(container, onChange) {
  // Load Monaco AMD loader
  await new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `${MONACO_CDN}/vs/loader.js`;
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });

  // Configure and load Monaco
  return new Promise((resolve) => {
    window.require.config({
      paths: { vs: `${MONACO_CDN}/vs` },
    });

    window.require(["vs/editor/editor.main"], function (monaco) {
      // Restore content from localStorage or use default
      const saved = localStorage.getItem("zinewire:content");

      const editor = monaco.editor.create(container, {
        value: saved || DEFAULT_CONTENT,
        language: "markdown",
        theme: "vs-dark",
        wordWrap: "on",
        minimap: { enabled: false },
        lineNumbers: "on",
        fontSize: 14,
        fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
        scrollBeyondLastLine: false,
        automaticLayout: true,
        padding: { top: 12 },
      });

      // Debounced change handler
      let timer = null;
      editor.onDidChangeModelContent(() => {
        const content = editor.getValue();
        // Save to localStorage
        localStorage.setItem("zinewire:content", content);
        // Debounce onChange
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => onChange(content), 400);
      });

      resolve(editor);
    });
  });
}
