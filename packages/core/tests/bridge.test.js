import { describe, it, expect, vi, beforeEach } from "vitest";
import { ZinewireBridge } from "../src/bridge.js";

// Mock Worker
class MockWorker {
  constructor() {
    this.onmessage = null;
    this.onerror = null;
    this.posted = [];
    this.terminated = false;
  }
  postMessage(data) {
    this.posted.push(data);
  }
  terminate() {
    this.terminated = true;
  }
  // Helper: simulate a message from the worker
  emit(data) {
    if (this.onmessage) this.onmessage({ data });
  }
}

// Patch global Worker so ZinewireBridge can construct one
let mockWorker;
vi.stubGlobal(
  "Worker",
  class {
    constructor() {
      mockWorker = new MockWorker();
      // Bridge sets onmessage/onerror on the returned worker,
      // so we return a proxy that captures those assignments.
      return mockWorker;
    }
  }
);

describe("ZinewireBridge", () => {
  let bridge;

  beforeEach(() => {
    mockWorker = null;
    bridge = new ZinewireBridge("/worker.js");
  });

  it("posts init message with sources and themes", () => {
    const sources = { "config.py": "# python" };
    const themes = { "base.css": "body{}" };
    bridge.init(sources, themes);

    expect(mockWorker.posted).toHaveLength(1);
    expect(mockWorker.posted[0]).toEqual({
      type: "init",
      sources,
      themes,
    });
  });

  it("resolves init when ready message received", async () => {
    const p = bridge.init({}, {});
    mockWorker.emit({ type: "ready" });
    await expect(p).resolves.toBeUndefined();
    expect(bridge.isReady).toBe(true);
  });

  it("rejects init on error message", async () => {
    const p = bridge.init({}, {});
    mockWorker.emit({ type: "error", message: "boom" });
    await expect(p).rejects.toThrow("boom");
  });

  it("fires status callbacks during init", async () => {
    const statuses = [];
    bridge.onStatus((msg) => statuses.push(msg));

    const p = bridge.init({}, {});
    mockWorker.emit({ type: "status", msg: "Loading Pyodide..." });
    mockWorker.emit({ type: "status", msg: "Installing packages..." });
    mockWorker.emit({ type: "ready" });
    await p;

    expect(statuses).toEqual(["Loading Pyodide...", "Installing packages..."]);
  });

  it("rejects build before init", async () => {
    await expect(bridge.build("# hi")).rejects.toThrow("not initialized");
  });

  it("posts build message and resolves with result", async () => {
    // Init first
    const initP = bridge.init({}, {});
    mockWorker.emit({ type: "ready" });
    await initP;

    const buildP = bridge.build("# Hello", '[zine]\ntitle = "T"', "print");

    expect(mockWorker.posted).toHaveLength(2);
    expect(mockWorker.posted[1]).toEqual({
      type: "build",
      markdown: "# Hello",
      config: '[zine]\ntitle = "T"',
      mode: "print",
    });

    mockWorker.emit({
      type: "result",
      html: "<h1>Hello</h1>",
      pages: 1,
      mode: "print",
    });

    const result = await buildP;
    expect(result).toEqual({
      html: "<h1>Hello</h1>",
      pages: 1,
      mode: "print",
    });
  });

  it("rejects build on error with traceback", async () => {
    const initP = bridge.init({}, {});
    mockWorker.emit({ type: "ready" });
    await initP;

    const buildP = bridge.build("bad input");
    mockWorker.emit({
      type: "error",
      message: "Parse error",
      traceback: "Traceback...",
    });

    try {
      await buildP;
      expect.unreachable("should have thrown");
    } catch (err) {
      expect(err.message).toBe("Parse error");
      expect(err.traceback).toBe("Traceback...");
    }
  });

  it("uses default config and mode in build", async () => {
    const initP = bridge.init({}, {});
    mockWorker.emit({ type: "ready" });
    await initP;

    bridge.build("# test");

    expect(mockWorker.posted[1]).toEqual({
      type: "build",
      markdown: "# test",
      config: "",
      mode: "print",
    });
  });

  it("destroy terminates the worker", async () => {
    const initP = bridge.init({}, {});
    mockWorker.emit({ type: "ready" });
    await initP;

    bridge.destroy();
    expect(mockWorker.terminated).toBe(true);
    expect(bridge.isReady).toBe(false);
  });

  it("rejects pending promises on worker error", async () => {
    const p = bridge.init({}, {});
    mockWorker.onerror({ message: "Script error" });
    await expect(p).rejects.toThrow("Script error");
  });
});
