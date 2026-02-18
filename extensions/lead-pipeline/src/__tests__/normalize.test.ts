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

import { buildSheetRow } from "../sheets.js";
import type { LeadRecord, QualifyResult } from "../types.js";

describe("buildSheetRow", () => {
  it("строит строку из 12 колонок", () => {
    const lead: LeadRecord = {
      id: "abcdef1234567890",
      source: "vk",
      source_item_id: "vk_wall-123_456",
      source_group: "cargo_russia",
      contact: "vk:67890",
      contact_url: "https://vk.com/wall-123_456",
      raw_text: "Нужна машина",
      created_at: "2026-02-18T10:00:00.000Z",
    };
    const qualify: QualifyResult = {
      is_cargo_request: true,
      from_city: "Москва",
      to_city: "Екб",
      cargo: "техника",
      weight_kg: 2000,
    };
    const row = buildSheetRow(lead, qualify);
    expect(row).toHaveLength(12);
    expect(row[6]).toBe("Москва→Екб");
    expect(row[10]).toBe("Новый");
  });
});
