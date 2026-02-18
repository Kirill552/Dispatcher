import type { LeadRecord, QualifyResult } from "./types.js";

export interface NotifyConfig {
  telegramBotToken: string;
  notifyUserId: string;
}

export async function notifyOwner(
  lead: LeadRecord,
  qualify: QualifyResult,
  botCommented: boolean,
  config: NotifyConfig
): Promise<void> {
  const sourceEmoji: Record<string, string> = {
    vk: "💙 ВКонтакте",
    yandex_uslugi: "🔴 Яндекс.Услуги",
    profi: "🟣 Профи.ру",
    youdo: "🟡 YouDo",
    telegram_rss: "✈️ Telegram",
    telegram_dm: "✈️ Telegram",
  };

  const route = qualify.from_city && qualify.to_city
    ? `📍 ${qualify.from_city} → ${qualify.to_city}`
    : "📍 Маршрут не определён";

  const cargoLine = qualify.cargo
    ? `📦 ${qualify.cargo}${qualify.weight_kg ? `, ~${qualify.weight_kg} кг` : ""}`
    : "";

  const commentLine = botCommented
    ? `\n💬 Бот уже написал комментарий`
    : "";

  const text = [
    `🆕 Новый лид — ${sourceEmoji[lead.source] ?? lead.source}`,
    "",
    route,
    cargoLine,
    `👤 ${lead.contact}`,
    lead.contact_url ? `🔗 ${lead.contact_url}` : "",
    "",
    `"${lead.raw_text.slice(0, 300)}${lead.raw_text.length > 300 ? "…" : ""}"`,
    commentLine,
  ]
    .filter((l) => l !== undefined)
    .join("\n")
    .trim();

  await fetch(
    `https://api.telegram.org/bot${config.telegramBotToken}/sendMessage`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: config.notifyUserId,
        text,
        parse_mode: "HTML",
        disable_web_page_preview: true,
      }),
    }
  );
}
