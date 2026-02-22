/**
 * Preview manager — updates an iframe with zinewire HTML output.
 * Uses blob URLs to avoid srcdoc size limits and allow external resources.
 */

export class Preview {
  constructor(iframe) {
    this._iframe = iframe;
    this._blobUrl = null;
  }

  update(html) {
    if (this._blobUrl) {
      URL.revokeObjectURL(this._blobUrl);
    }
    const blob = new Blob([html], { type: "text/html" });
    this._blobUrl = URL.createObjectURL(blob);
    this._iframe.src = this._blobUrl;
  }

  showError(message, traceback) {
    const escaped = (s) =>
      s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

    const html = `<!DOCTYPE html>
<html><head><style>
  body { font-family: -apple-system, sans-serif; padding: 2rem; background: #1e1e1e; color: #d4d4d4; }
  h2 { color: #e06c75; margin-bottom: 1rem; }
  pre { background: #252526; padding: 1rem; border-radius: 4px; overflow-x: auto; font-size: 0.85rem; line-height: 1.4; }
</style></head><body>
  <h2>Build Error</h2>
  <p>${escaped(message)}</p>
  ${traceback ? `<pre>${escaped(traceback)}</pre>` : ""}
</body></html>`;

    this.update(html);
  }

  showLoading() {
    const html = `<!DOCTYPE html>
<html><head><style>
  body { display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0;
         font-family: -apple-system, sans-serif; background: #f5f5f5; color: #999; }
</style></head><body>Building...</body></html>`;
    this.update(html);
  }

  destroy() {
    if (this._blobUrl) {
      URL.revokeObjectURL(this._blobUrl);
      this._blobUrl = null;
    }
  }
}
