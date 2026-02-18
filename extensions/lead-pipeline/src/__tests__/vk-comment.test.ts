import { describe, it, expect } from "vitest";
import { buildCommentText } from "../vk-comment.js";

describe("buildCommentText", () => {
  it("содержит маршрут и ссылку на бот", () => {
    const text = buildCommentText("Москва", "Казань", "ai_dispatcher_bot");
    expect(text).toContain("Москва");
    expect(text).toContain("Казань");
    expect(text).toContain("t.me/ai_dispatcher_bot");
  });

  it("работает без маршрута", () => {
    const text = buildCommentText(null, null, "ai_dispatcher_bot");
    expect(text).toContain("t.me/ai_dispatcher_bot");
    expect(text.length).toBeGreaterThan(20);
  });
});
