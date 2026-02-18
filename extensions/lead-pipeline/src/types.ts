export type LeadSource =
  | "vk"
  | "yandex_uslugi"
  | "profi"
  | "youdo"
  | "telegram_rss"
  | "telegram_dm";

export interface LeadRecord {
  id: string;               // hash-отпечаток: sha256(source+source_item_id)
  source: LeadSource;
  source_item_id: string;   // ID поста/заявки в источнике
  source_group?: string;    // VK: short_name группы
  contact: string;          // @username, телефон или имя
  contact_url?: string;     // ссылка на профиль/пост
  from_city?: string;
  to_city?: string;
  cargo?: string;
  weight_kg?: number;
  loading_date?: string;
  raw_text: string;
  created_at: string;       // ISO timestamp
  bot_action?: string;      // "vk_comment" | "notified_owner"
  bot_comment_text?: string;
}

export interface QualifyResult {
  is_cargo_request: boolean;
  from_city: string | null;
  to_city: string | null;
  cargo: string | null;
  weight_kg: number | null;
}
