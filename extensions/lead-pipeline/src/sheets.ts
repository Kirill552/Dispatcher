import type { LeadRecord, QualifyResult } from "./types.js";

export interface SheetsConfig {
  sheetsId: string;
  sheetsServiceAccountJson: string;
}

export function buildSheetRow(lead: LeadRecord, qualify: QualifyResult): string[] {
  return [
    lead.id.slice(0, 8),
    lead.created_at,
    lead.source,
    lead.source_group ?? "",
    lead.contact,
    lead.contact_url ?? "",
    qualify.from_city && qualify.to_city
      ? `${qualify.from_city}→${qualify.to_city}` : "",
    qualify.cargo ?? "",
    lead.raw_text.slice(0, 500),
    lead.bot_comment_text ?? "",
    "Новый",
    "",
  ];
}

export async function appendLeadToSheets(
  lead: LeadRecord,
  qualify: QualifyResult,
  config: SheetsConfig
): Promise<void> {
  const { google } = await import("googleapis");

  const credentials = JSON.parse(config.sheetsServiceAccountJson);
  const auth = new google.auth.GoogleAuth({
    credentials,
    scopes: ["https://www.googleapis.com/auth/spreadsheets"],
  });

  const sheets = google.sheets({ version: "v4", auth });
  const row = buildSheetRow(lead, qualify);

  await sheets.spreadsheets.values.append({
    spreadsheetId: config.sheetsId,
    range: "Лиды!A:L",
    valueInputOption: "USER_ENTERED",
    requestBody: { values: [row] },
  });
}
