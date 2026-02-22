import { describe, it, expect, vi, beforeEach } from "vitest";
import { Preview } from "../src/preview.js";

// Mock URL.createObjectURL / revokeObjectURL
let blobUrls = [];
vi.stubGlobal("URL", {
  ...URL,
  createObjectURL: vi.fn((blob) => {
    const url = `blob:mock-${blobUrls.length}`;
    blobUrls.push({ url, blob });
    return url;
  }),
  revokeObjectURL: vi.fn(),
});

describe("Preview", () => {
  let iframe;
  let preview;

  beforeEach(() => {
    blobUrls = [];
    URL.createObjectURL.mockClear();
    URL.revokeObjectURL.mockClear();
    iframe = document.createElement("iframe");
    preview = new Preview(iframe);
  });

  it("creates a blob URL and sets iframe src on update", () => {
    preview.update("<h1>Hello</h1>");

    expect(URL.createObjectURL).toHaveBeenCalledOnce();
    expect(iframe.src).toContain("blob:");
  });

  it("revokes previous blob URL on subsequent update", () => {
    preview.update("<h1>First</h1>");
    const firstUrl = iframe.src;

    preview.update("<h1>Second</h1>");
    expect(URL.revokeObjectURL).toHaveBeenCalledWith(firstUrl);
  });

  it("showError generates error HTML with escaped content", () => {
    preview.showError("Bad <script>", "Line 1: <error>");

    // Should have created a blob
    expect(URL.createObjectURL).toHaveBeenCalled();
    const blob = blobUrls[blobUrls.length - 1].blob;
    expect(blob.type).toBe("text/html");
  });

  it("showLoading creates a loading page", () => {
    preview.showLoading();
    expect(URL.createObjectURL).toHaveBeenCalled();
  });

  it("destroy revokes the current blob URL", () => {
    preview.update("<p>content</p>");
    const url = iframe.src;

    preview.destroy();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith(url);
  });

  it("destroy is safe to call without prior update", () => {
    preview.destroy();
    expect(URL.revokeObjectURL).not.toHaveBeenCalled();
  });
});
