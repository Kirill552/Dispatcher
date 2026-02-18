import { describe, it, expect } from "vitest";
import { createDedupeStore } from "../dedupe.js";

describe("createDedupeStore", () => {
  it("возвращает true для нового лида, false для дубля", () => {
    const store = createDedupeStore();
    expect(store.isNew("vk", "vk_wall-123_456")).toBe(true);
    store.markSeen("vk", "vk_wall-123_456");
    expect(store.isNew("vk", "vk_wall-123_456")).toBe(false);
  });

  it("не смешивает источники", () => {
    const store = createDedupeStore();
    store.markSeen("vk", "123");
    expect(store.isNew("profi", "123")).toBe(true);
  });

  it("size() считает все записи", () => {
    const store = createDedupeStore();
    store.markSeen("vk", "a");
    store.markSeen("vk", "b");
    expect(store.size()).toBe(2);
  });
});
