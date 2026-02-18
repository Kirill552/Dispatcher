import { describe, it, expect } from "vitest";
import { normalizeVkPost } from "../normalize.js";

describe("normalizeVkPost", () => {
  it("извлекает contact из from_id и строит lead", () => {
    const post = {
      id: 12345,
      from_id: 67890,
      owner_id: -100123,
      text: "Нужна машина Москва-Екатеринбург, 3 тонны, дата 25 февраля",
      date: 1708300800,
    };
    const lead = normalizeVkPost(post, "cargo_russia");

    expect(lead.source).toBe("vk");
    expect(lead.source_item_id).toBe("vk_wall-100123_12345");
    expect(lead.source_group).toBe("cargo_russia");
    expect(lead.contact).toBe("vk:67890");
    expect(lead.contact_url).toBe("https://vk.com/wall-100123_12345");
    expect(lead.raw_text).toBe(post.text);
    expect(lead.id).toHaveLength(64); // sha256 hex
  });

  it("обрезает текст длиннее 2000 символов", () => {
    const post = { id: 1, from_id: 2, owner_id: -3, text: "x".repeat(3000), date: 0 };
    const lead = normalizeVkPost(post, "g");
    expect(lead.raw_text.length).toBeLessThanOrEqual(2000);
  });
});
