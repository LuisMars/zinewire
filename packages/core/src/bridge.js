/**
 * ZinewireBridge — main-thread API for communicating with the Pyodide worker.
 *
 * Usage:
 *   import { ZinewireBridge } from '@zinewire/core';
 *   const bridge = new ZinewireBridge('/worker.js');
 *   bridge.onStatus(msg => console.log(msg));
 *   await bridge.init(pythonSources, themeCss);
 *   const { html, pages } = await bridge.build(markdown, tomlConfig, 'print');
 */

export class ZinewireBridge {
  constructor(workerUrl) {
    this._worker = new Worker(workerUrl);
    this._ready = false;
    this._statusCallbacks = [];
    this._pendingInit = null;
    this._pendingBuild = null;

    this._worker.onmessage = (e) => this._handleMessage(e.data);
    this._worker.onerror = (e) => {
      const err = new Error(e.message || "Worker error");
      if (this._pendingInit) this._pendingInit.reject(err);
      if (this._pendingBuild) this._pendingBuild.reject(err);
    };
  }

  /**
   * Initialize Pyodide and load zinewire source.
   * @param {Record<string,string>} sources - Python source files
   * @param {Record<string,string>} themes - CSS theme files
   */
  init(sources, themes) {
    return new Promise((resolve, reject) => {
      this._pendingInit = { resolve, reject };
      this._worker.postMessage({ type: "init", sources, themes });
    });
  }

  /**
   * Build HTML from markdown.
   * @param {string} markdown - Markdown content
   * @param {string} config - TOML config string (or empty)
   * @param {string} mode - 'print' | 'manual' | 'landing'
   * @returns {Promise<{html: string, pages: number, mode: string}>}
   */
  build(markdown, config = "", mode = "print") {
    if (!this._ready) {
      return Promise.reject(new Error("Bridge not initialized. Call init() first."));
    }
    return new Promise((resolve, reject) => {
      this._pendingBuild = { resolve, reject };
      this._worker.postMessage({ type: "build", markdown, config, mode });
    });
  }

  /**
   * Register a callback for status messages during init.
   * @param {function(string): void} callback
   */
  onStatus(callback) {
    this._statusCallbacks.push(callback);
  }

  /** Terminate the worker. */
  destroy() {
    this._worker.terminate();
    this._ready = false;
  }

  /** @returns {boolean} Whether the bridge is initialized and ready. */
  get isReady() {
    return this._ready;
  }

  _handleMessage(data) {
    switch (data.type) {
      case "status":
        for (const cb of this._statusCallbacks) cb(data.msg);
        break;

      case "ready":
        this._ready = true;
        if (this._pendingInit) {
          this._pendingInit.resolve();
          this._pendingInit = null;
        }
        break;

      case "result":
        if (this._pendingBuild) {
          this._pendingBuild.resolve({
            html: data.html,
            pages: data.pages,
            mode: data.mode,
          });
          this._pendingBuild = null;
        }
        break;

      case "error":
        if (this._pendingInit && !this._ready) {
          this._pendingInit.reject(new Error(data.message));
          this._pendingInit = null;
        } else if (this._pendingBuild) {
          const err = new Error(data.message);
          err.traceback = data.traceback;
          this._pendingBuild.reject(err);
          this._pendingBuild = null;
        }
        break;
    }
  }
}
