import { describe, it, expect, vi, beforeEach } from "vitest";
import { qualifyLead } from "../qualify.js";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

function makeLlmResponse(json: object) {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve({
      choices: [{ message: { content: JSON.stringify(json) } }]
    })
  });
}

describe("qualifyLead", () => {
  beforeEach(() => { mockFetch.mockReset(); });

  it("возвращает QualifyResult для запроса на перевозку", async () => {
    mockFetch.mockReturnValue(makeLlmResponse({
      is_cargo_request: true,
      from_city: "Москва",
      to_city: "Екатеринбург",
      cargo: "оборудование",
      weight_kg: 3000
    }));

    const result = await qualifyLead(
      "Нужна машина Москва-Екатеринбург 3 тонны оборудование",
      { openrouterApiKey: "test-key" }
    );

    expect(result).not.toBeNull();
    expect(result!.is_cargo_request).toBe(true);
    expect(result!.from_city).toBe("Москва");
    expect(result!.weight_kg).toBe(3000);
  });

  it("возвращает null при is_cargo_request=false", async () => {
    mockFetch.mockReturnValue(makeLlmResponse({
      is_cargo_request: false,
      from_city: null, to_city: null, cargo: null, weight_kg: null
    }));

    const result = await qualifyLead("Продам грузовик", { openrouterApiKey: "test-key" });
    expect(result).toBeNull();
  });

  it("возвращает null при ошибке парсинга JSON от LLM", async () => {
    mockFetch.mockReturnValue(Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        choices: [{ message: { content: "не JSON" } }]
      })
    }));

    const result = await qualifyLead("что-то", { openrouterApiKey: "test-key" });
    expect(result).toBeNull();
  });
});
