import type { QualifyResult } from "./types.js";

export interface QualifyConfig {
  openrouterApiKey: string;
}

const SYSTEM_PROMPT = `Ты анализируешь посты в VK-группах по грузоперевозкам.
Определи: это запрос на перевозку груза МЕЖДУ городами (межгород)?
Ответь ТОЛЬКО валидным JSON без markdown, без пояснений:
{"is_cargo_request": boolean, "from_city": string|null, "to_city": string|null, "cargo": string|null, "weight_kg": number|null}`;

export async function qualifyLead(
  rawText: string,
  config: QualifyConfig
): Promise<QualifyResult | null> {
  try {
    const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${config.openrouterApiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "google/gemini-2.5-flash-lite",
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: rawText.slice(0, 500) },
        ],
        max_tokens: 150,
        temperature: 0,
      }),
    });

    if (!res.ok) return null;

    const data = await res.json() as any;
    const content: string = data?.choices?.[0]?.message?.content ?? "";
    const parsed: QualifyResult = JSON.parse(content);

    if (!parsed.is_cargo_request) return null;
    return parsed;
  } catch {
    return null;
  }
}
