import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { Type } from "@sinclair/typebox";
import { createHash, randomUUID } from "node:crypto";

// --- Shared state between tools and service ---
interface TrackedCargo {
  cargoId: string;
  externalId: string;
  createdAt: number;
}

interface CarrierResponse {
  firm: string;
  price: number;
  firmId: string;
  loadId: string;
  responseId: string;
  timestamp: number;
}

const activeCargos = new Map<string, TrackedCargo>();
const seenResponseIds = new Set<string>();
const pendingResponses: CarrierResponse[] = [];

// Кэш boardId и contactId (заполняется при старте)
// Общая площадка ATI.SU — постоянный ID, не возвращается через /canAdd
const ATI_COMMON_BOARD_ID = "a0a0a0a0a0a0a0a0a0a0a0a0";
const ATI_MAX_LOADING_DAYS_AHEAD = 60;
const CITIES_REQUIRING_ADDRESS = new Set<number>([
  3611, // Москва
  1, // Санкт-Петербург
]);
const PAYMENT_TYPES = [
  "with-bargaining",
  "without-bargaining",
  "rate-request",
  "auction",
] as const;
let cachedBoardId: string | null = null;
let cachedContactId: string | null = null;

// Очистка грузов старше 48 часов
function cleanupOldCargos() {
  const cutoff = Date.now() - 48 * 60 * 60 * 1000;
  for (const [id, cargo] of activeCargos) {
    if (cargo.createdAt < cutoff) activeCargos.delete(id);
  }
}

type CreateCargoErrorCode =
  | "CONFIG_NOT_READY"
  | "INVALID_INPUT"
  | "DATE_INVALID"
  | "DATE_OUT_OF_RANGE"
  | "ADDRESS_REQUIRED"
  | "DUPLICATE_CONFLICT"
  | "ARCHIVE_DELAY_NOT_ELAPSED"
  | "RESTORE_NOT_AVAILABLE"
  | "ATI_VALIDATION_ERROR"
  | "ATI_AUTH_ERROR"
  | "ATI_UNAVAILABLE";

type CreateCargoErrorResult = {
  success: false;
  error_code: CreateCargoErrorCode;
  user_message: string;
  retryable: boolean;
  required_fields?: string[];
};

type NormalizedLoadingDate =
  | {
      ok: true;
      isoDate: string;
      displayDate: string;
      daysAhead: number;
    }
  | {
      ok: false;
      error: CreateCargoErrorResult;
    };

type CargoPaymentType = (typeof PAYMENT_TYPES)[number];

type PaymentDetectResult = {
  payment_type: CargoPaymentType;
  confidence: "high" | "medium" | "low";
  reason: string;
};

type CreateCargoToolParams = {
  loading_city_id: number;
  unloading_city_id: number;
  cargo_description: string;
  weight: number;
  volume: number;
  body_type_id: number;
  loading_date: string;
  loading_address?: string;
  unloading_address?: string;
  loading_type_id?: number;
  payment_type?: CargoPaymentType;
  payment_hint?: string;
  client_key?: string;
  try_restore_archived?: boolean;
  currency_type?: number;
  rate_with_vat?: number;
  rate_without_vat?: number;
  cash?: number;
  on_card?: boolean;
  auction_start_rate?: number;
  auction_bid_step?: number;
};

type ParsedAtiErrorPayload = {
  error_code?: string;
  reason?: string;
  error_list: Array<{ property?: string; reason?: string; error?: string }>;
};

type LoadForRestore = {
  id: string;
  orderNumber?: string;
  externalId?: string;
  loadingCityId: number | null;
  unloadingCityId: number | null;
  cargoName: string;
  weight: number | null;
  volume: number | null;
  bodyTypeId: number | null;
  archiveDate: string | null;
  canBeRestored: boolean;
};

type MockCargoRecord = {
  cargoId: string;
  cargoNumber: string;
  externalId: string;
  loadingCityId: number;
  unloadingCityId: number;
  cargoDescription: string;
  weight: number;
  volume: number;
  bodyTypeId: number;
  loadingDateIso: string;
  archived: boolean;
  archiveDate: string | null;
  paymentType: CargoPaymentType;
};

const RU_MONTHS: Record<string, number> = {
  январь: 1,
  января: 1,
  янв: 1,
  февраль: 2,
  февраля: 2,
  фев: 2,
  март: 3,
  марта: 3,
  мар: 3,
  апрель: 4,
  апреля: 4,
  апр: 4,
  май: 5,
  мая: 5,
  июнь: 6,
  июня: 6,
  июн: 6,
  июль: 7,
  июля: 7,
  июл: 7,
  август: 8,
  августа: 8,
  авг: 8,
  сентябрь: 9,
  сентября: 9,
  сен: 9,
  октябрь: 10,
  октября: 10,
  окт: 10,
  ноябрь: 11,
  ноября: 11,
  ноя: 11,
  декабрь: 12,
  декабря: 12,
  дек: 12,
};

const RU_MONTHS_GENITIVE = [
  "января",
  "февраля",
  "марта",
  "апреля",
  "мая",
  "июня",
  "июля",
  "августа",
  "сентября",
  "октября",
  "ноября",
  "декабря",
];

function isCargoPaymentType(value: string): value is CargoPaymentType {
  return (PAYMENT_TYPES as readonly string[]).includes(value);
}

function normalizeForMatch(text: string): string {
  return text
    .toLowerCase()
    .replace(/ё/g, "е")
    .replace(/[^a-zа-я0-9\s-]/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function tokenize(text: string): string[] {
  return normalizeForMatch(text)
    .split(" ")
    .filter((t) => t.length >= 3);
}

function detectPaymentTypeFromText(input: string): PaymentDetectResult {
  const text = normalizeForMatch(input);
  if (!text) {
    return {
      payment_type: "rate-request",
      confidence: "low",
      reason: "Текст пустой — выбран безопасный тип по умолчанию (запрос ставки).",
    };
  }

  const hasAny = (...parts: string[]): boolean =>
    parts.some((part) => text.includes(normalizeForMatch(part)));

  if (
    hasAny("аукцион", "торги", "тендер", "кто предложит меньше", "ставки в реальном времени")
  ) {
    return {
      payment_type: "auction",
      confidence: "high",
      reason: "В тексте есть признаки формата торгов/аукциона.",
    };
  }

  if (
    hasAny("без торга", "без bargaining", "фикс", "цена окончательная", "не торгуемся")
  ) {
    return {
      payment_type: "without-bargaining",
      confidence: "high",
      reason: "Клиент указал фиксированную цену без торга.",
    };
  }

  if (
    hasAny(
      "запрос ставки",
      "ставку предложите",
      "узнать ставки",
      "посчитайте ставку",
      "груза нет",
      "только цену узнать"
    )
  ) {
    return {
      payment_type: "rate-request",
      confidence: "high",
      reason: "Клиент просит запрос ставок/оценку без фиксированной цены.",
    };
  }

  if (hasAny("торг уместен", "возможен торг", "можно поторговаться")) {
    return {
      payment_type: "with-bargaining",
      confidence: "high",
      reason: "Клиент явно разрешил торг.",
    };
  }

  if (text.includes("торг")) {
    return {
      payment_type: "with-bargaining",
      confidence: "medium",
      reason: "В тексте есть упоминание торга, выбран режим с торгом.",
    };
  }

  return {
    payment_type: "rate-request",
    confidence: "low",
    reason: "Явных маркеров не найдено, выбран безопасный режим запроса ставки.",
  };
}

function resolvePaymentType(
  explicit: CargoPaymentType | undefined,
  hint: string | undefined
): PaymentDetectResult {
  if (explicit) {
    return {
      payment_type: explicit,
      confidence: "high",
      reason: "Тип оплаты передан явно.",
    };
  }
  return detectPaymentTypeFromText(hint || "");
}

function sanitizeExternalChunk(value: string): string {
  return normalizeForMatch(value).replace(/[^a-zа-я0-9]/gi, "_").slice(0, 40);
}

function buildCargoSignature(params: CreateCargoToolParams): string {
  const base = [
    params.loading_city_id,
    params.unloading_city_id,
    normalizeForMatch(params.cargo_description),
    Math.round(params.weight),
    Math.round(params.volume * 10),
    params.body_type_id,
  ].join("|");
  return createHash("sha1").update(base).digest("hex").slice(0, 12);
}

function buildExternalId(clientKey: string | undefined, signature: string): string {
  const prefix = clientKey ? sanitizeExternalChunk(clientKey) : String(Date.now());
  return `OC_${prefix}_${signature}`.slice(0, 250);
}

function toNumberOrNull(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function normalizeCargoName(raw: unknown): string {
  if (typeof raw !== "string") return "";
  return normalizeForMatch(raw);
}

function isCloseEnough(
  candidateValue: number | null,
  expectedValue: number,
  toleranceRatio: number
): boolean {
  if (candidateValue == null || !Number.isFinite(candidateValue)) return true;
  if (expectedValue <= 0) return true;
  const diff = Math.abs(candidateValue - expectedValue);
  return diff <= expectedValue * toleranceRatio;
}

function textLooksSameCargo(a: string, b: string): boolean {
  const left = normalizeForMatch(a);
  const right = normalizeForMatch(b);
  if (!left || !right) return true;
  if (left === right) return true;
  if (left.includes(right) || right.includes(left)) return true;

  const leftTokens = new Set(tokenize(left));
  const rightTokens = new Set(tokenize(right));
  if (leftTokens.size === 0 || rightTokens.size === 0) return false;

  let overlap = 0;
  for (const token of leftTokens) {
    if (rightTokens.has(token)) overlap++;
  }
  const minTokens = Math.min(leftTokens.size, rightTokens.size);
  return overlap >= Math.max(1, Math.ceil(minTokens * 0.6));
}

function extractLoadForRestore(raw: any): LoadForRestore | null {
  const id = String(raw?.Id || raw?.id || "").trim();
  if (!id) return null;

  const loadingCityId =
    toNumberOrNull(raw?.Loading?.CityId) ??
    toNumberOrNull(raw?.loading?.city_id) ??
    toNumberOrNull(raw?.route?.loading?.location?.city_id);

  const unloadingCityId =
    toNumberOrNull(raw?.Unloading?.CityId) ??
    toNumberOrNull(raw?.unloading?.city_id) ??
    toNumberOrNull(raw?.route?.unloading?.location?.city_id);

  const cargoName =
    normalizeCargoName(raw?.Loading?.LoadingCargos?.[0]?.Name) ||
    normalizeCargoName(raw?.loading?.loading_cargos?.[0]?.name) ||
    normalizeCargoName(raw?.Cargo?.CargoType) ||
    normalizeCargoName(raw?.cargo?.cargo_type) ||
    normalizeCargoName(raw?.CargoType) ||
    normalizeCargoName(raw?.cargo_type);

  const weight =
    toNumberOrNull(raw?.Cargo?.Weight) ??
    toNumberOrNull(raw?.cargo?.weight) ??
    toNumberOrNull(raw?.Loading?.LoadingCargos?.[0]?.Weight) ??
    toNumberOrNull(raw?.loading?.loading_cargos?.[0]?.weight);

  const volume =
    toNumberOrNull(raw?.Cargo?.Volume) ??
    toNumberOrNull(raw?.cargo?.volume) ??
    toNumberOrNull(raw?.Loading?.LoadingCargos?.[0]?.Volume) ??
    toNumberOrNull(raw?.loading?.loading_cargos?.[0]?.volume);

  const bodyTypeId =
    toNumberOrNull(raw?.Transport?.CarType) ??
    toNumberOrNull(raw?.transport?.car_type) ??
    toNumberOrNull(raw?.Truck?.BodyTypes?.[0]) ??
    toNumberOrNull(raw?.truck?.body_types?.[0]);

  const archiveDate = String(raw?.ArchiveDate || raw?.archive_date || "").trim() || null;

  return {
    id,
    orderNumber: String(raw?.OrderNumber || raw?.order_number || "").trim() || undefined,
    externalId: String(raw?.ExternalId || raw?.external_id || "").trim() || undefined,
    loadingCityId,
    unloadingCityId,
    cargoName,
    weight,
    volume,
    bodyTypeId,
    archiveDate,
    canBeRestored: Boolean(raw?.CanBeRestored ?? raw?.can_be_restored),
  };
}

function toMockAtiLoad(record: MockCargoRecord): any {
  return {
    Id: record.cargoId,
    LoadNumber: record.cargoNumber,
    OrderNumber: record.cargoNumber,
    ExternalId: record.externalId,
    LoadingCity: record.loadingCityId,
    UnloadingCity: record.unloadingCityId,
    FirstDate: `${record.loadingDateIso}T00:00:00.000Z`,
    ResponseCount: 0,
    OfferCount: 0,
    CanBeRenewed: true,
    ArchiveDate: record.archiveDate,
    CanBeRestored: record.archived,
    Loading: {
      CityId: record.loadingCityId,
      LoadingCargos: [
        {
          Name: record.cargoDescription,
          Weight: record.weight,
          Volume: record.volume,
        },
      ],
    },
    Unloading: {
      CityId: record.unloadingCityId,
    },
    Cargo: {
      CargoType: record.cargoDescription,
      Weight: record.weight,
      Volume: record.volume,
    },
    Transport: {
      CarType: record.bodyTypeId,
    },
  };
}

function matchesArchivedCargo(
  candidate: LoadForRestore,
  params: CreateCargoToolParams,
  expectedExternalId: string
): boolean {
  if (!candidate.archiveDate || !candidate.canBeRestored) return false;

  const candidateExternalKeys = [
    candidate.orderNumber || "",
    candidate.externalId || "",
  ].map((x) => x.toLowerCase());
  if (
    expectedExternalId &&
    candidateExternalKeys.some((x) => x && x === expectedExternalId.toLowerCase())
  ) {
    return true;
  }

  if (candidate.loadingCityId !== params.loading_city_id) return false;
  if (candidate.unloadingCityId !== params.unloading_city_id) return false;
  if (
    candidate.bodyTypeId != null &&
    Number.isFinite(candidate.bodyTypeId) &&
    candidate.bodyTypeId !== params.body_type_id
  ) {
    return false;
  }

  if (!textLooksSameCargo(candidate.cargoName, params.cargo_description)) {
    return false;
  }
  if (!isCloseEnough(candidate.weight, params.weight, 0.15)) return false;
  if (!isCloseEnough(candidate.volume, params.volume, 0.25)) return false;

  return true;
}

function buildPaymentPayload(
  params: CreateCargoToolParams,
  paymentType: CargoPaymentType
): Record<string, unknown> {
  const currencyType = params.currency_type ?? 1;

  if (paymentType === "auction") {
    const startRate =
      params.auction_start_rate ??
      params.rate_with_vat ??
      params.rate_without_vat ??
      params.cash ??
      10000;
    const bidStep = params.auction_bid_step ?? Math.max(100, Math.round(startRate * 0.02));

    return {
      type: "auction",
      hide_counter_offers: false,
      direct_offer: false,
      accept_bids_with_vat: true,
      accept_bids_without_vat: true,
      vat_percents: 20,
      start_rate: startRate,
      auction_currency_type: currencyType,
      bid_step: bidStep,
      time_to_provide_documents: "12:00",
      winner_criteria: "best-rate",
      auction_duration: {
        fixed_duration: "1d",
        count_from_first_bid: false,
      },
      no_winner_end_options: {
        type: "publish-rate-request",
      },
    };
  }

  const payload: Record<string, unknown> = {
    type: paymentType,
    currency_type: currencyType,
    hide_counter_offers: paymentType === "without-bargaining",
    direct_offer: false,
    cash_available: true,
    rate_with_nds_available: true,
    rate_without_nds_available: true,
  };

  if (typeof params.rate_with_vat === "number") {
    payload.rate_with_vat = params.rate_with_vat;
  }
  if (typeof params.rate_without_vat === "number") {
    payload.rate_without_vat = params.rate_without_vat;
  }
  if (typeof params.cash === "number") {
    payload.cash = params.cash;
  }
  if (typeof params.on_card === "boolean") {
    payload.on_card = params.on_card;
  }

  return payload;
}

function jsonContent(data: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
  };
}

function utcDayStart(date: Date): Date {
  return new Date(
    Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate())
  );
}

function addUtcDays(date: Date, days: number): Date {
  const d = new Date(date.getTime());
  d.setUTCDate(d.getUTCDate() + days);
  return d;
}

function dayDiff(from: Date, to: Date): number {
  return Math.floor((to.getTime() - from.getTime()) / (24 * 60 * 60 * 1000));
}

function buildUtcDate(year: number, month: number, day: number): Date | null {
  const date = new Date(Date.UTC(year, month - 1, day));
  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  ) {
    return null;
  }
  return date;
}

function toIsoDate(date: Date): string {
  const y = date.getUTCFullYear();
  const m = String(date.getUTCMonth() + 1).padStart(2, "0");
  const d = String(date.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function toRuDate(date: Date): string {
  return `${date.getUTCDate()} ${RU_MONTHS_GENITIVE[date.getUTCMonth()]} ${date.getUTCFullYear()}`;
}

function normalizeLoadingDate(input: string): NormalizedLoadingDate {
  const raw = input.trim().toLowerCase();
  if (!raw) {
    return {
      ok: false,
      error: {
        success: false,
        error_code: "DATE_INVALID",
        user_message:
          "Нужна дата загрузки. Укажите дату в формате ДД.ММ.ГГГГ или «25 февраля».",
        retryable: true,
      },
    };
  }

  const today = utcDayStart(new Date());
  let parsedDate: Date | null = null;

  if (raw === "сегодня") parsedDate = today;
  if (raw === "завтра") parsedDate = addUtcDays(today, 1);
  if (raw === "послезавтра") parsedDate = addUtcDays(today, 2);

  if (!parsedDate) {
    const isoMatch = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (isoMatch) {
      parsedDate = buildUtcDate(
        Number(isoMatch[1]),
        Number(isoMatch[2]),
        Number(isoMatch[3])
      );
    }
  }

  if (!parsedDate) {
    const dmyMatch = raw.match(
      /^(\d{1,2})[.\-/](\d{1,2})(?:[.\-/](\d{2,4}))?$/
    );
    if (dmyMatch) {
      const day = Number(dmyMatch[1]);
      const month = Number(dmyMatch[2]);
      const yearRaw = dmyMatch[3];
      if (yearRaw) {
        const parsedYear = Number(yearRaw);
        const year = yearRaw.length === 2 ? 2000 + parsedYear : parsedYear;
        parsedDate = buildUtcDate(year, month, day);
      } else {
        const currentYear = today.getUTCFullYear();
        const thisYear = buildUtcDate(currentYear, month, day);
        const nextYear = buildUtcDate(currentYear + 1, month, day);
        if (thisYear && thisYear.getTime() >= today.getTime()) {
          parsedDate = thisYear;
        } else {
          parsedDate = nextYear;
        }
      }
    }
  }

  if (!parsedDate) {
    const clean = raw.replace(/[,]+/g, " ").replace(/\s+/g, " ").trim();
    const ruDateMatch = clean.match(/^(\d{1,2})\s+([а-яё]+)(?:\s+(\d{2,4}))?$/);
    if (ruDateMatch) {
      const day = Number(ruDateMatch[1]);
      const monthName = ruDateMatch[2];
      const month = RU_MONTHS[monthName];
      const yearRaw = ruDateMatch[3];
      if (month) {
        if (yearRaw) {
          const parsedYear = Number(yearRaw);
          const year = yearRaw.length === 2 ? 2000 + parsedYear : parsedYear;
          parsedDate = buildUtcDate(year, month, day);
        } else {
          const currentYear = today.getUTCFullYear();
          const thisYear = buildUtcDate(currentYear, month, day);
          const nextYear = buildUtcDate(currentYear + 1, month, day);
          if (thisYear && thisYear.getTime() >= today.getTime()) {
            parsedDate = thisYear;
          } else {
            parsedDate = nextYear;
          }
        }
      }
    }
  }

  if (!parsedDate) {
    return {
      ok: false,
      error: {
        success: false,
        error_code: "DATE_INVALID",
        user_message:
          "Не понял дату загрузки. Укажите дату в формате ДД.ММ.ГГГГ или «25 февраля».",
        retryable: true,
      },
    };
  }

  const daysAhead = dayDiff(today, parsedDate);
  if (daysAhead < 0 || daysAhead > ATI_MAX_LOADING_DAYS_AHEAD) {
    return {
      ok: false,
      error: {
        success: false,
        error_code: "DATE_OUT_OF_RANGE",
        user_message: `Дата загрузки должна быть в диапазоне от сегодня до ${ATI_MAX_LOADING_DAYS_AHEAD} дней вперёд. Укажите ближайшую дату.`,
        retryable: true,
      },
    };
  }

  return {
    ok: true,
    isoDate: toIsoDate(parsedDate),
    displayDate: toRuDate(parsedDate),
    daysAhead,
  };
}

function parseAtiErrorPayload(errText: string): ParsedAtiErrorPayload | null {
  try {
    const parsed = JSON.parse(errText);
    const errorCode = String(
      parsed?.error_code || parsed?.Error || parsed?.errorCode || ""
    ).trim();
    const reason = String(parsed?.reason || parsed?.Reason || "").trim();

    const rawList = Array.isArray(parsed?.error_list)
      ? parsed.error_list
      : Array.isArray(parsed?.ErrorsList)
        ? parsed.ErrorsList
        : [];

    const errorList = rawList.map((item: any) => ({
      property: String(item?.property || item?.Property || "").trim() || undefined,
      reason: String(item?.reason || item?.Reason || "").trim() || undefined,
      error: String(item?.error || item?.Error || "").trim() || undefined,
    }));

    return {
      error_code: errorCode || undefined,
      reason: reason || undefined,
      error_list: errorList,
    };
  } catch {
    return null;
  }
}

function mapCreateCargoApiError(
  status: number,
  errText: string,
  operation: "create" | "restore" = "create"
): CreateCargoErrorResult {
  if (status === 401 || status === 403) {
    return {
      success: false,
      error_code: "ATI_AUTH_ERROR",
      user_message:
        "Ошибка авторизации ATI API. Нужна проверка токена в настройках сервера.",
      retryable: false,
    };
  }

  const parsed = parseAtiErrorPayload(errText);
  const errors = parsed?.error_list || [];
  const errorCode = parsed?.error_code?.toLowerCase();

  if (errorCode === "load_archive_delay_not_elapsed") {
    return {
      success: false,
      error_code: "ARCHIVE_DELAY_NOT_ELAPSED",
      user_message:
        "Архивный груз пока нельзя поднять: после архивации должно пройти до 60 минут.",
      retryable: true,
    };
  }

  if (errorCode === "load_conflict_error") {
    return {
      success: false,
      error_code: "DUPLICATE_CONFLICT",
      user_message:
        "Похожий груз уже размещён. Обновите существующую заявку или измените параметры.",
      retryable: true,
    };
  }

  if (operation === "restore" && status === 404) {
    return {
      success: false,
      error_code: "RESTORE_NOT_AVAILABLE",
      user_message:
        "Архивный груз для восстановления не найден. Создаю новую заявку.",
      retryable: true,
    };
  }

  const addressErrors = errors.filter((e) => e.error === "no_address");
  if (addressErrors.length > 0) {
    const requiredFields: string[] = [];
    if (addressErrors.some((e) => e.property?.includes(".loading"))) {
      requiredFields.push("loading_address");
    }
    if (addressErrors.some((e) => e.property?.includes(".unloading"))) {
      requiredFields.push("unloading_address");
    }

    return {
      success: false,
      error_code: "ADDRESS_REQUIRED",
      user_message:
        "Для Москвы и Санкт-Петербурга нужен точный адрес (улица и дом). Уточните адреса погрузки/разгрузки.",
      retryable: true,
      required_fields: requiredFields.length ? requiredFields : undefined,
    };
  }

  const dateErrors = errors.filter(
    (e) =>
      e.error === "outbounds" || e.property?.includes("cargo_application.route.loading.dates.first_date")
  );
  if (dateErrors.length > 0) {
    return {
      success: false,
      error_code: "DATE_OUT_OF_RANGE",
      user_message: `Дата загрузки должна быть в пределах ${ATI_MAX_LOADING_DAYS_AHEAD} дней. Укажите ближайшую дату.`,
      retryable: true,
    };
  }

  if (status >= 500) {
    return {
      success: false,
      error_code: "ATI_UNAVAILABLE",
      user_message:
        "Сервис ATI временно недоступен. Попробуйте повторить отправку через несколько минут.",
      retryable: true,
    };
  }

  return {
    success: false,
    error_code: "ATI_VALIDATION_ERROR",
    user_message:
      parsed?.reason ||
      "Не удалось разместить заявку из-за ограничений ATI. Уточните данные и попробуйте снова.",
    retryable: true,
  };
}

const plugin = {
  id: "ati-cargo",
  name: "ATI.su Cargo",
  description:
    "ATI.su freight exchange integration: create cargos, check responses, search cities, manage loads, messenger, carrier info",
  version: "3.2.0",
  configSchema: {
    type: "object" as const,
    properties: {
      apiToken: { type: "string" as const },
      boardId: { type: "string" as const },
      monitorIntervalMs: { type: "number" as const },
      mockMode: { type: "boolean" as const },
    },
  },

  register(api: OpenClawPluginApi) {
    const config = api.pluginConfig as {
      apiToken: string;
      boardId?: string;
      monitorIntervalMs?: number;
      mockMode?: boolean | string;
    };

    const ATI_BASE = "https://api.ati.su";
    const mockModeRaw =
      config.mockMode ?? process.env.ATI_MOCK_MODE ?? process.env.OPENCLAW_ATI_MOCK_MODE;
    const isMockMode =
      mockModeRaw === true ||
      String(mockModeRaw || "")
        .trim()
        .toLowerCase() === "true" ||
      String(mockModeRaw || "")
        .trim()
        .toLowerCase() === "1";
    const mockCargos = new Map<string, MockCargoRecord>();
    let mockCargoSeq = 15540;
    const headers = {
      Authorization: `Bearer ${config.apiToken}`,
      "Content-Type": "application/json",
      Accept: "application/json",
      "User-Agent": "openclaw-ati-cargo/3.2",
    };

    if (isMockMode) {
      api.logger.warn(
        "ati-cargo: MOCK MODE ENABLED — реальные запросы на публикацию/удаление грузов в ATI отключены."
      );
    }

    // --- initCache: авто-получение boardId и contactId при запуске ---
    async function initCache() {
      if (isMockMode) {
        cachedBoardId = config.boardId || ATI_COMMON_BOARD_ID;
        cachedContactId = "0";
        api.logger.info(
          `ati-cargo: mock cache boardId=${cachedBoardId} contactId=${cachedContactId}`
        );
        return;
      }

      // boardId: попробовать получить через API, fallback на общую площадку
      try {
        const resp = await fetch(`${ATI_BASE}/v2/boards/public/boards/canAdd`, {
          headers,
        });
        if (resp.ok) {
          const boards: any[] = await resp.json();
          const board = boards.find((b: any) => b.can_add);
          if (board?.id) {
            cachedBoardId = board.id;
          }
        }
      } catch (err) {
        api.logger.warn(`ati-cargo: failed to fetch boardId: ${err}`);
      }

      // Fallback: конфиг → общая площадка ATI
      if (!cachedBoardId) {
        cachedBoardId = config.boardId || ATI_COMMON_BOARD_ID;
      }

      // contactId: первый видимый контакт
      // Поле в API: is_visibled (не is_visible — особенность ATI API)
      // contact.id может быть 0 (валидное значение)
      try {
        const resp = await fetch(`${ATI_BASE}/v1.0/firms/contacts`, { headers });
        if (resp.ok) {
          const contacts: any[] = await resp.json();
          const contact = contacts.find(
            (c: any) => c.is_visibled && !c.is_deleted
          );
          if (contact && contact.id != null) {
            cachedContactId = String(contact.id);
          } else if (contacts.length > 0 && contacts[0].id != null) {
            cachedContactId = String(contacts[0].id);
          }
        }
      } catch (err) {
        api.logger.warn(`ati-cargo: failed to fetch contactId: ${err}`);
      }

      api.logger.info(
        `ati-cargo: cached boardId=${cachedBoardId} contactId=${cachedContactId}`
      );
    }

    async function getOwnLoads(): Promise<any[]> {
      if (isMockMode) {
        return Array.from(mockCargos.values()).map(toMockAtiLoad);
      }

      const resp = await fetch(`${ATI_BASE}/v1.0/loads`, { headers });
      if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(`loads_list ${resp.status}: ${errText}`);
      }
      const loads = await resp.json();
      return Array.isArray(loads) ? loads : [];
    }

    async function findRestorableArchivedLoad(
      params: CreateCargoToolParams,
      expectedExternalId: string
    ): Promise<LoadForRestore | null> {
      const loads = await getOwnLoads();
      const candidates = loads
        .map(extractLoadForRestore)
        .filter((item): item is LoadForRestore => Boolean(item))
        .filter((item) => matchesArchivedCargo(item, params, expectedExternalId))
        .sort((a, b) =>
          String(b.archiveDate || "").localeCompare(String(a.archiveDate || ""))
        );

      return candidates[0] || null;
    }

    function buildCargoPayload(
      params: CreateCargoToolParams,
      args: {
        boardId: string;
        contactId: number;
        externalId: string;
        normalizedDate: NormalizedLoadingDate & { ok: true };
        loadingAddress?: string;
        unloadingAddress?: string;
        paymentType: CargoPaymentType;
      }
    ) {
      const loadDate = args.normalizedDate.isoDate;

      return {
        cargo_application: {
          external_id: args.externalId,
          route: {
            loading: {
              location: {
                type: "manual",
                city_id: params.loading_city_id,
                ...(args.loadingAddress ? { address: args.loadingAddress } : {}),
              },
              dates: {
                type: "from-date",
                first_date: `${loadDate}T00:00:00.000Z`,
                last_date: `${loadDate}T23:59:59.000Z`,
                time: { type: "bounded" },
              },
              cargos: [
                {
                  id: 1,
                  name: params.cargo_description,
                  weight: { type: "kilos", quantity: params.weight },
                  volume: { quantity: params.volume },
                },
              ],
            },
            unloading: {
              location: {
                type: "manual",
                city_id: params.unloading_city_id,
                ...(args.unloadingAddress ? { address: args.unloadingAddress } : {}),
              },
            },
          },
          truck: {
            trucks_count: 1,
            load_type: "ftl",
            body_types: [params.body_type_id],
            body_loading: {
              types: [params.loading_type_id || 2],
              is_all_required: false,
            },
            body_unloading: {
              types: [params.loading_type_id || 2],
              is_all_required: false,
            },
          },
          payment: buildPaymentPayload(params, args.paymentType),
          boards: [
            {
              id: args.boardId,
              publication_mode: "now",
              publication_time: "1970-01-01T00:00:00.000Z",
              cancel_publish_on_auction_bet: false,
              reservation_enabled: false,
            },
          ],
          note: "Пишите в мессенджер АТИ, на звонки не отвечаю",
          contacts: [args.contactId],
        },
      };
    }

    // ========================
    // ИНСТРУМЕНТЫ: Поиск и создание
    // ========================

    // --- Tool: ati_city_search ---
    api.registerTool({
      name: "ati_city_search",
      label: "ATI City Search",
      description:
        "Search for a city ID on ATI.su by name. Use when the client mentions a city for loading or unloading.",
      parameters: Type.Object({
        city_name: Type.String({
          description: "City name in Russian, e.g. 'Сарапул'",
        }),
      }),
      async execute(_toolCallId, params) {
        if (isMockMode) {
          const mockCities = [
            { city_id: 3611, city_name: "Москва", region: "Москва" },
            { city_id: 1, city_name: "Санкт-Петербург", region: "Санкт-Петербург" },
            { city_id: 80, city_name: "Казань", region: "Татарстан" },
            { city_id: 1422, city_name: "Екатеринбург", region: "Свердловская область" },
            { city_id: 213, city_name: "Новосибирск", region: "Новосибирская область" },
          ];
          const needle = normalizeForMatch(params.city_name);
          const results = mockCities.filter((c) =>
            normalizeForMatch(c.city_name).includes(needle)
          );
          return jsonContent(results);
        }

        const resp = await fetch(
          `${ATI_BASE}/gw/gis-dict/v1/autocomplete/suggestions`,
          {
            method: "POST",
            headers,
            body: JSON.stringify({
              prefix: params.city_name,
              suggestion_types: 1,
              limit: 5,
              country_id: 1,
            }),
          }
        );
        const data = await resp.json();
        const suggestions = data.suggestions || [];
        const results = suggestions.map((s: any) => ({
          city_id: s.city?.id,
          city_name: s.city?.name,
          region: s.region?.name,
        }));
        return {
          content: [{ type: "text", text: JSON.stringify(results, null, 2) }],
        };
      },
    });

    // --- Tool: ati_detect_payment_type ---
    api.registerTool({
      name: "ati_detect_payment_type",
      label: "ATI Detect Payment Type",
      description:
        "Detect ATI payment type from client phrase. Returns one of: with-bargaining, without-bargaining, rate-request, auction.",
      parameters: Type.Object({
        text: Type.String({
          description:
            "Client phrase about payment format, bargaining or auction mode.",
        }),
      }),
      async execute(_toolCallId, params) {
        return jsonContent(detectPaymentTypeFromText(params.text));
      },
    });

    // --- Tool: ati_mock_status ---
    api.registerTool({
      name: "ati_mock_status",
      label: "ATI Mock Status",
      description:
        "Return ATI mock mode status. Use in tests to ensure cargo publication is mocked and no real loads are created.",
      parameters: Type.Object({}),
      async execute() {
        return jsonContent({
          mock_mode: isMockMode,
          note: isMockMode
            ? "ATI mock mode включён: публикация и удаление грузов работают локально."
            : "ATI mock mode выключен: инструменты работают с реальным ATI API.",
        });
      },
    });

    // --- Tool: ati_create_cargo ---
    api.registerTool({
      name: "ati_create_cargo",
      label: "ATI Create Cargo",
      description:
        "Create a cargo listing on ATI.su freight exchange. Use after all order data is collected and confirmed by the client.",
      parameters: Type.Object({
        loading_city_id: Type.Number({
          description: "ATI city ID for loading point",
        }),
        unloading_city_id: Type.Number({
          description: "ATI city ID for unloading point",
        }),
        cargo_description: Type.String({
          description: "Cargo description, e.g. 'мебель'",
        }),
        weight: Type.Number({ description: "Weight in kilograms" }),
        volume: Type.Number({ description: "Volume in cubic meters" }),
        body_type_id: Type.Number({
          description:
            "Body type: 200=tent, 300=reefer, 500=van, 1100=flatbed",
        }),
        loading_date: Type.String({
          description:
            "Loading date. Supports YYYY-MM-DD, DD.MM.YYYY, or Russian format like '25 февраля'.",
        }),
        loading_address: Type.Optional(
          Type.String({
            description:
              "Exact loading address (street, house). Required for Moscow/SPb.",
          })
        ),
        unloading_address: Type.Optional(
          Type.String({
            description:
              "Exact unloading address (street, house). Required for Moscow/SPb.",
          })
        ),
        loading_type_id: Type.Optional(
          Type.Number({
            description: "Loading type: 1=top, 2=side, 4=rear. Default 2",
          })
        ),
        payment_type: Type.Optional(
          Type.Union(
            [
              Type.Literal("with-bargaining"),
              Type.Literal("without-bargaining"),
              Type.Literal("rate-request"),
              Type.Literal("auction"),
            ],
            {
              description:
                "ATI payment type. If omitted, it will be detected from payment_hint or defaults to rate-request.",
            }
          )
        ),
        payment_hint: Type.Optional(
          Type.String({
            description:
              "Original client phrase about payment format. Used for automatic payment type detection.",
          })
        ),
        client_key: Type.Optional(
          Type.String({
            description:
              "Stable client identifier (usually Telegram user_id) for repeat-route archive restore.",
          })
        ),
        try_restore_archived: Type.Optional(
          Type.Boolean({
            description:
              "Try to restore matching archived cargo before creating a new one. Default true.",
          })
        ),
        currency_type: Type.Optional(
          Type.Number({
            description: "Currency type for payment block. Default 1 (RUB).",
          })
        ),
        rate_with_vat: Type.Optional(
          Type.Number({
            description: "Optional fixed rate with VAT.",
          })
        ),
        rate_without_vat: Type.Optional(
          Type.Number({
            description: "Optional fixed rate without VAT.",
          })
        ),
        cash: Type.Optional(
          Type.Number({
            description: "Optional fixed cash rate.",
          })
        ),
        on_card: Type.Optional(
          Type.Boolean({
            description:
              "Whether cash payment to card is allowed (on_card).",
          })
        ),
        auction_start_rate: Type.Optional(
          Type.Number({
            description: "Auction start rate (used when payment_type=auction).",
          })
        ),
        auction_bid_step: Type.Optional(
          Type.Number({
            description: "Auction bid step (used when payment_type=auction).",
          })
        ),
      }),
      async execute(_toolCallId, rawParams) {
        const params = rawParams as CreateCargoToolParams;

        if (isMockMode) {
          if (!cachedBoardId) cachedBoardId = config.boardId || ATI_COMMON_BOARD_ID;
          if (!cachedContactId) cachedContactId = "0";
        }

        if (!cachedContactId) {
          return jsonContent({
            success: false,
            error_code: "CONFIG_NOT_READY",
            user_message:
              "Сервис размещения ещё инициализируется. Повторите отправку через 1-2 минуты.",
            retryable: true,
          } as CreateCargoErrorResult);
        }

        const boardId = cachedBoardId || config.boardId || "";
        if (!boardId) {
          return jsonContent({
            success: false,
            error_code: "CONFIG_NOT_READY",
            user_message:
              "Не удалось определить площадку ATI для размещения. Нужна проверка конфигурации.",
            retryable: false,
          } as CreateCargoErrorResult);
        }

        const contactId = Number(cachedContactId);
        if (!Number.isFinite(contactId)) {
          return jsonContent({
            success: false,
            error_code: "CONFIG_NOT_READY",
            user_message:
              "Не удалось определить контакт ATI для размещения. Нужна проверка конфигурации.",
            retryable: false,
          } as CreateCargoErrorResult);
        }

        if (params.weight < 200) {
          return jsonContent({
            success: false,
            error_code: "INVALID_INPUT",
            user_message:
              "Минимальный вес для размещения на этом сервисе — 200 кг. Уточните данные груза.",
            retryable: false,
          } as CreateCargoErrorResult);
        }

        if (params.volume <= 0) {
          return jsonContent({
            success: false,
            error_code: "INVALID_INPUT",
            user_message:
              "Для размещения нужен корректный объём груза (м3 больше нуля).",
            retryable: false,
          } as CreateCargoErrorResult);
        }

        if (!params.cargo_description.trim()) {
          return jsonContent({
            success: false,
            error_code: "INVALID_INPUT",
            user_message: "Нужно указать описание груза для размещения заявки.",
            retryable: false,
          } as CreateCargoErrorResult);
        }

        if (params.payment_type && !isCargoPaymentType(params.payment_type)) {
          return jsonContent({
            success: false,
            error_code: "INVALID_INPUT",
            user_message:
              "Неизвестный тип оплаты. Допустимо: with-bargaining, without-bargaining, rate-request, auction.",
            retryable: false,
          } as CreateCargoErrorResult);
        }

        const normalizedDate = normalizeLoadingDate(params.loading_date);
        if (!normalizedDate.ok) {
          return jsonContent(normalizedDate.error);
        }
        const normalizedDateOk = normalizedDate;

        const loadingAddress = params.loading_address?.trim();
        const unloadingAddress = params.unloading_address?.trim();

        const requiredFields: string[] = [];
        if (
          CITIES_REQUIRING_ADDRESS.has(params.loading_city_id) &&
          !loadingAddress
        ) {
          requiredFields.push("loading_address");
        }
        if (
          CITIES_REQUIRING_ADDRESS.has(params.unloading_city_id) &&
          !unloadingAddress
        ) {
          requiredFields.push("unloading_address");
        }
        if (requiredFields.length > 0) {
          return jsonContent({
            success: false,
            error_code: "ADDRESS_REQUIRED",
            user_message:
              "Для Москвы и Санкт-Петербурга обязателен точный адрес (улица и дом). Уточните адрес.",
            retryable: true,
            required_fields: requiredFields,
          } as CreateCargoErrorResult);
        }

        const paymentDetect = resolvePaymentType(
          params.payment_type,
          params.payment_hint
        );
        const hasAnyRate =
          typeof params.rate_with_vat === "number" ||
          typeof params.rate_without_vat === "number" ||
          typeof params.cash === "number";
        if (paymentDetect.payment_type === "without-bargaining" && !hasAnyRate) {
          return jsonContent({
            success: false,
            error_code: "INVALID_INPUT",
            user_message:
              "Для режима оплаты «без торга» нужна хотя бы одна ставка: с НДС, без НДС или наличными.",
            retryable: true,
            required_fields: ["rate_with_vat", "rate_without_vat", "cash"],
          } as CreateCargoErrorResult);
        }
        const cargoSignature = buildCargoSignature(params);
        const externalId = buildExternalId(params.client_key, cargoSignature);

        const payload = buildCargoPayload(params, {
          boardId,
          contactId,
          externalId,
          normalizedDate: normalizedDateOk,
          loadingAddress,
          unloadingAddress,
          paymentType: paymentDetect.payment_type,
        });

        if (params.try_restore_archived !== false) {
          try {
            const archivedMatch = await findRestorableArchivedLoad(
              params,
              externalId
            );

            if (archivedMatch) {
              if (isMockMode) {
                const record = mockCargos.get(archivedMatch.id);
                if (record) {
                  record.archived = false;
                  record.archiveDate = null;
                  record.loadingDateIso = normalizedDateOk.isoDate;
                  record.paymentType = paymentDetect.payment_type;

                  activeCargos.set(record.cargoId, {
                    cargoId: record.cargoId,
                    externalId: record.externalId,
                    createdAt: Date.now(),
                  });

                  return jsonContent({
                    success: true,
                    operation: "restored",
                    restored_from_cargo_id: archivedMatch.id,
                    cargo_id: record.cargoId,
                    cargo_number: record.cargoNumber,
                    external_id: externalId,
                    resolved_payment_type: paymentDetect.payment_type,
                    payment_detection_confidence: paymentDetect.confidence,
                    payment_detection_reason: paymentDetect.reason,
                    normalized_loading_date: normalizedDateOk.isoDate,
                    loading_date_display: normalizedDateOk.displayDate,
                    mock_mode: true,
                  });
                }
              }

              api.logger.info(
                `ati_create_cargo: try restore archived cargo ${archivedMatch.id} for external_id=${externalId}`
              );
              const restoreResp = await fetch(
                `${ATI_BASE}/v2/cargos/${archivedMatch.id}/restore`,
                {
                  method: "POST",
                  headers,
                  body: JSON.stringify(payload),
                }
              );

              if (restoreResp.ok) {
                const restoreResult = await restoreResp.json();
                const cargoApp = restoreResult.cargo_application || {};
                const restoredCargoId = String(
                  cargoApp.cargo_application_id ||
                    cargoApp.cargo_id ||
                    archivedMatch.id
                );

                activeCargos.set(restoredCargoId, {
                  cargoId: restoredCargoId,
                  externalId: payload.cargo_application.external_id,
                  createdAt: Date.now(),
                });

                return jsonContent({
                  success: true,
                  operation: "restored",
                  restored_from_cargo_id: archivedMatch.id,
                  cargo_id: restoredCargoId,
                  cargo_number:
                    cargoApp.cargo_application_number || cargoApp.cargo_number,
                  external_id: externalId,
                  resolved_payment_type: paymentDetect.payment_type,
                  payment_detection_confidence: paymentDetect.confidence,
                  payment_detection_reason: paymentDetect.reason,
                  normalized_loading_date: normalizedDateOk.isoDate,
                  loading_date_display: normalizedDateOk.displayDate,
                });
              }

              const restoreErrText = await restoreResp.text();
              const mappedRestoreError = mapCreateCargoApiError(
                restoreResp.status,
                restoreErrText,
                "restore"
              );

              if (
                mappedRestoreError.error_code ===
                "ARCHIVE_DELAY_NOT_ELAPSED"
              ) {
                return jsonContent(mappedRestoreError);
              }

              api.logger.warn(
                `ati_create_cargo: restore fallback to create, status=${restoreResp.status}, body=${restoreErrText}`
              );
            }
          } catch (restoreErr) {
            api.logger.warn(
              `ati_create_cargo: restore check failed, fallback to create: ${restoreErr}`
            );
          }
        }

        if (isMockMode) {
          const cargoId = randomUUID();
          const cargoNumber = `BWSM${String(++mockCargoSeq).padStart(5, "0")}`;
          const record: MockCargoRecord = {
            cargoId,
            cargoNumber,
            externalId,
            loadingCityId: params.loading_city_id,
            unloadingCityId: params.unloading_city_id,
            cargoDescription: params.cargo_description.trim(),
            weight: params.weight,
            volume: params.volume,
            bodyTypeId: params.body_type_id,
            loadingDateIso: normalizedDateOk.isoDate,
            archived: false,
            archiveDate: null,
            paymentType: paymentDetect.payment_type,
          };
          mockCargos.set(cargoId, record);
          activeCargos.set(cargoId, {
            cargoId,
            externalId,
            createdAt: Date.now(),
          });

          return jsonContent({
            success: true,
            operation: "created",
            cargo_id: cargoId,
            cargo_number: cargoNumber,
            external_id: externalId,
            resolved_payment_type: paymentDetect.payment_type,
            payment_detection_confidence: paymentDetect.confidence,
            payment_detection_reason: paymentDetect.reason,
            normalized_loading_date: normalizedDateOk.isoDate,
            loading_date_display: normalizedDateOk.displayDate,
            mock_mode: true,
          });
        }

        const resp = await fetch(`${ATI_BASE}/v2/cargos`, {
          method: "POST",
          headers,
          body: JSON.stringify(payload),
        });

        if (resp.ok) {
          const result = await resp.json();
          const cargoApp = result.cargo_application || {};
          const cargoId = String(
            cargoApp.cargo_application_id || cargoApp.cargo_id || ""
          );

          if (cargoId) {
            activeCargos.set(cargoId, {
              cargoId,
              externalId: payload.cargo_application.external_id,
              createdAt: Date.now(),
            });
            api.logger.info(`ati-cargo: tracking cargo ${cargoId}`);
          }

          return jsonContent({
            success: true,
            operation: "created",
            cargo_id: cargoId,
            cargo_number:
              cargoApp.cargo_application_number || cargoApp.cargo_number,
            external_id: externalId,
            resolved_payment_type: paymentDetect.payment_type,
            payment_detection_confidence: paymentDetect.confidence,
            payment_detection_reason: paymentDetect.reason,
            normalized_loading_date: normalizedDateOk.isoDate,
            loading_date_display: normalizedDateOk.displayDate,
          });
        } else {
          const errText = await resp.text();
          api.logger.warn(
            `ati_create_cargo: API ${resp.status}, body=${errText}`
          );
          return jsonContent(mapCreateCargoApiError(resp.status, errText));
        }
      },
    });

    // --- Tool: ati_check_responses ---
    api.registerTool({
      name: "ati_check_responses",
      label: "ATI Check Responses",
      description:
        "Check carrier responses for a specific cargo. Use when waiting for carrier offers after creating a cargo.",
      parameters: Type.Object({
        cargo_id: Type.Optional(
          Type.String({
            description:
              "Cargo ID to filter responses. If omitted, returns all.",
          })
        ),
      }),
      async execute(_toolCallId, params) {
        let summary: Array<{
          firm: string;
          price: number;
          firm_id: string;
          load_id: string;
          response_id: string;
        }> = [];

        if (isMockMode) {
          const responses = params.cargo_id
            ? pendingResponses.filter((r) => r.loadId === params.cargo_id)
            : pendingResponses;
          summary = responses.map((r) => ({
            firm: r.firm,
            price: r.price,
            firm_id: r.firmId,
            load_id: r.loadId,
            response_id: r.responseId,
          }));
        } else {
          const resp = await fetch(`${ATI_BASE}/v1.0/loads/new/responses`, {
            headers,
          });
          if (!resp.ok) {
            return {
              content: [{ type: "text", text: `Error ${resp.status}` }],
            };
          }

          let responses = await resp.json();
          if (params.cargo_id) {
            responses = responses.filter(
              (r: any) => r.LoadId === params.cargo_id
            );
          }

          summary = responses.map((r: any) => ({
            firm: r.FirmName,
            price: r.Price,
            firm_id: r.FirmId,
            load_id: r.LoadId,
            response_id: String(r.ResponseId || r.Id || ""),
          }));
        }

        return {
          content: [
            {
              type: "text",
              text: `Found ${summary.length} responses:\n${JSON.stringify(summary, null, 2)}`,
            },
          ],
        };
      },
    });

    // --- Tool: ati_get_new_responses ---
    api.registerTool({
      name: "ati_get_new_responses",
      label: "ATI Get New Responses",
      description:
        "Get new carrier responses collected by the background monitor. Use when the client asks about offers or when you need to inform the client about carrier responses for their cargo.",
      parameters: Type.Object({
        cargo_id: Type.Optional(
          Type.String({
            description:
              "Filter by cargo ID. If omitted, returns all new responses.",
          })
        ),
      }),
      async execute(_toolCallId, params) {
        let results: CarrierResponse[];
        if (params.cargo_id) {
          results = pendingResponses.filter(
            (r) => r.loadId === params.cargo_id
          );
          const remaining = pendingResponses.filter(
            (r) => r.loadId !== params.cargo_id
          );
          pendingResponses.length = 0;
          pendingResponses.push(...remaining);
        } else {
          results = pendingResponses.splice(0);
        }

        if (results.length === 0) {
          return {
            content: [
              {
                type: "text",
                text: `No new responses. Active cargos being monitored: ${activeCargos.size}`,
              },
            ],
          };
        }

        return {
          content: [
            {
              type: "text",
              text: `${results.length} new carrier responses:\n${JSON.stringify(results, null, 2)}`,
            },
          ],
        };
      },
    });

    // ========================
    // ИНСТРУМЕНТЫ: Управление грузами
    // ========================

    // --- Tool: ati_my_loads ---
    api.registerTool({
      name: "ati_my_loads",
      label: "ATI My Loads",
      description:
        "List my active cargo listings on ATI.su. Use to see all current loads, their response counts, and statuses.",
      parameters: Type.Object({}),
      async execute() {
        let loads: any[] = [];
        try {
          loads = await getOwnLoads();
        } catch (err) {
          return {
            content: [{ type: "text", text: `Error: ${String(err)}` }],
          };
        }

        if (isMockMode) {
          loads = loads.filter((l: any) => !l.ArchiveDate && !l.archive_date);
        }

        const summary = loads.map((l: any) => ({
          id: l.Id,
          load_number: l.LoadNumber,
          loading_city: l.LoadingCity || l.Loading?.City,
          unloading_city: l.UnloadingCity || l.Unloading?.City,
          date: l.FirstDate || l.Loading?.FirstDate,
          response_count: l.ResponseCount ?? 0,
          offer_count: l.OfferCount ?? 0,
          can_be_renewed: l.CanBeRenewed ?? false,
        }));

        return {
          content: [
            {
              type: "text",
              text: `${summary.length} active loads:\n${JSON.stringify(summary, null, 2)}`,
            },
          ],
        };
      },
    });

    // --- Tool: ati_renew_cargo ---
    api.registerTool({
      name: "ati_renew_cargo",
      label: "ATI Renew Cargo",
      description:
        "Renew (bump) a cargo listing in ATI.su search results. Use to push a load higher in search when it has been active for a while.",
      parameters: Type.Object({
        load_id: Type.String({ description: "Load ID to renew" }),
      }),
      async execute(_toolCallId, params) {
        if (isMockMode) {
          const record = mockCargos.get(params.load_id);
          if (!record || record.archived) {
            return {
              content: [
                {
                  type: "text",
                  text: "Груз не найден или уже в архиве.",
                },
              ],
            };
          }
          return {
            content: [{ type: "text", text: "Груз успешно обновлён в поиске." }],
          };
        }

        const resp = await fetch(
          `${ATI_BASE}/v1.0/loads/${params.load_id}/renew`,
          {
            method: "PUT",
            headers,
          }
        );

        if (resp.ok) {
          const result = await resp.json();
          const status = result.Status ?? result.status;
          if (status === 0) {
            return {
              content: [
                { type: "text", text: "Груз успешно обновлён в поиске." },
              ],
            };
          } else if (status === 2) {
            return {
              content: [
                {
                  type: "text",
                  text: "Слишком рано для обновления. Попробуйте позже.",
                },
              ],
            };
          }
          return {
            content: [
              {
                type: "text",
                text: `Renew status: ${JSON.stringify(result)}`,
              },
            ],
          };
        } else {
          const errText = await resp.text();
          return {
            content: [{ type: "text", text: `Error ${resp.status}: ${errText}` }],
          };
        }
      },
    });

    // --- Tool: ati_delete_cargo ---
    api.registerTool({
      name: "ati_delete_cargo",
      label: "ATI Delete Cargo",
      description:
        "Delete (archive) a cargo listing from ATI.su. Use when a load is no longer needed.",
      parameters: Type.Object({
        load_id: Type.String({ description: "Load ID to delete" }),
      }),
      async execute(_toolCallId, params) {
        if (isMockMode) {
          const record = mockCargos.get(params.load_id);
          if (record) {
            record.archived = true;
            record.archiveDate = new Date().toISOString();
          }
          activeCargos.delete(params.load_id);
          return {
            content: [{ type: "text", text: "Груз удалён с биржи." }],
          };
        }

        const resp = await fetch(
          `${ATI_BASE}/v1.0/loads/${params.load_id}`,
          {
            method: "DELETE",
            headers,
          }
        );

        if (resp.ok) {
          activeCargos.delete(params.load_id);
          return {
            content: [{ type: "text", text: "Груз удалён с биржи." }],
          };
        } else {
          const errText = await resp.text();
          return {
            content: [{ type: "text", text: `Error ${resp.status}: ${errText}` }],
          };
        }
      },
    });

    // --- Tool: ati_carrier_info ---
    api.registerTool({
      name: "ati_carrier_info",
      label: "ATI Carrier Info",
      description:
        "Get information about a carrier on ATI.su: name, rating, claims, contacts. Use to evaluate a carrier before accepting their offer.",
      parameters: Type.Object({
        ati_id: Type.String({
          description: "ATI firm ID (numeric string)",
        }),
      }),
      async execute(_toolCallId, params) {
        const resp = await fetch(
          `${ATI_BASE}/v1.0/firms/${params.ati_id}/contacts/summary`,
          { headers }
        );

        if (!resp.ok) {
          return {
            content: [{ type: "text", text: `Error ${resp.status}` }],
          };
        }

        const data = await resp.json();
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(data, null, 2),
            },
          ],
        };
      },
    });

    // ========================
    // ИНСТРУМЕНТЫ: ATI Мессенджер
    // ========================

    // --- Tool: ati_create_chat ---
    api.registerTool({
      name: "ati_create_chat",
      label: "ATI Create Chat",
      description:
        "Create a dialog with a carrier in ATI Messenger. Use to start communication with a carrier about a load. Between two users only one dialog exists — re-creating returns the existing one.",
      parameters: Type.Object({
        ati_id: Type.String({
          description:
            "ATI ID in format 'firm_code.contact_id', e.g. '777.0'",
        }),
        name: Type.Optional(
          Type.String({ description: "Chat name, e.g. carrier firm name" })
        ),
        description: Type.Optional(
          Type.String({ description: "Chat description, e.g. route info" })
        ),
      }),
      async execute(_toolCallId, params) {
        const resp = await fetch(`${ATI_BASE}/messenger/1.1/chats/`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            channel_type: "dialog",
            name: params.name || "Диалог",
            description: params.description || "",
            ati_id: params.ati_id,
          }),
        });

        if (!resp.ok) {
          const errText = await resp.text();
          return {
            content: [{ type: "text", text: `Error ${resp.status}: ${errText}` }],
          };
        }

        const chat = await resp.json();
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                { chat_id: chat.id, name: chat.name },
                null,
                2
              ),
            },
          ],
        };
      },
    });

    // --- Tool: ati_send_message ---
    api.registerTool({
      name: "ati_send_message",
      label: "ATI Send Message",
      description:
        "Send a message in an ATI Messenger chat. Use to communicate with carriers about loads, negotiate prices, or confirm deals.",
      parameters: Type.Object({
        chat_id: Type.String({ description: "Chat ID from ati_create_chat" }),
        text: Type.String({ description: "Message text to send" }),
      }),
      async execute(_toolCallId, params) {
        // ATI Messenger v1.2 требует multipart/form-data
        const boundary = `----OCBoundary${Date.now()}`;
        const body = [
          `--${boundary}`,
          `Content-Disposition: form-data; name="text"`,
          "",
          params.text,
          `--${boundary}--`,
        ].join("\r\n");

        const resp = await fetch(
          `${ATI_BASE}/messenger/1.2/chats/${params.chat_id}/messages`,
          {
            method: "POST",
            headers: {
              Authorization: headers.Authorization,
              "Content-Type": `multipart/form-data; boundary=${boundary}`,
              Accept: "application/json",
              "User-Agent": headers["User-Agent"],
            },
            body,
          }
        );

        if (!resp.ok) {
          const errText = await resp.text();
          return {
            content: [{ type: "text", text: `Error ${resp.status}: ${errText}` }],
          };
        }

        const msg = await resp.json();
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  message_id: msg.id,
                  text: msg.text,
                  delivered: msg.delivered ?? true,
                },
                null,
                2
              ),
            },
          ],
        };
      },
    });

    // --- Tool: ati_get_chat_history ---
    api.registerTool({
      name: "ati_get_chat_history",
      label: "ATI Chat History",
      description:
        "Get message history from an ATI Messenger chat. Use to check what a carrier replied or to review conversation.",
      parameters: Type.Object({
        chat_id: Type.String({ description: "Chat ID" }),
      }),
      async execute(_toolCallId, params) {
        const resp = await fetch(
          `${ATI_BASE}/messenger/1.1/chats/${params.chat_id}/history/`,
          { headers }
        );

        if (!resp.ok) {
          return {
            content: [{ type: "text", text: `Error ${resp.status}` }],
          };
        }

        const messages: any[] = await resp.json();
        const summary = messages.map((m: any) => ({
          text: m.text,
          from: m.from || m.user,
          ts: m.ts || m.timestamp,
        }));

        return {
          content: [
            {
              type: "text",
              text: `${summary.length} messages:\n${JSON.stringify(summary, null, 2)}`,
            },
          ],
        };
      },
    });

    // --- Tool: ati_get_chats ---
    api.registerTool({
      name: "ati_get_chats",
      label: "ATI Get Chats",
      description:
        "List all ATI Messenger subscriptions/chats. Use to see active conversations with carriers.",
      parameters: Type.Object({}),
      async execute() {
        const resp = await fetch(`${ATI_BASE}/messenger/1.2/subscriptions/`, {
          headers,
        });

        if (!resp.ok) {
          return {
            content: [{ type: "text", text: `Error ${resp.status}` }],
          };
        }

        const subs: any[] = await resp.json();
        const summary = subs.map((s: any) => ({
          id: s.id,
          name: s.name,
          partner: s.partner,
          unread: s.unread ?? 0,
          last_message: s.tail?.text || null,
        }));

        return {
          content: [
            {
              type: "text",
              text: `${summary.length} chats:\n${JSON.stringify(summary, null, 2)}`,
            },
          ],
        };
      },
    });

    // ========================
    // ИНСТРУМЕНТЫ: Приглашение перевозчика
    // ========================

    // --- Tool: ati_invite_carrier ---
    api.registerTool({
      name: "ati_invite_carrier",
      label: "ATI Invite Carrier",
      description:
        "Invite a carrier by sending a counter offer. Use after agreeing on terms with a carrier to formalize the deal on ATI.su.",
      parameters: Type.Object({
        load_id: Type.String({ description: "Load ID" }),
        response_id: Type.String({ description: "Carrier response ID" }),
        rate_type: Type.Optional(
          Type.Number({
            description:
              "Payment type: 0=cash, 1=non-cash with VAT, 2=non-cash without VAT. Default 0",
          })
        ),
      }),
      async execute(_toolCallId, params) {
        const rateType = params.rate_type ?? 0;

        const resp = await fetch(
          `${ATI_BASE}/v1.2/orders/invites/counter_offer`,
          {
            method: "POST",
            headers,
            body: JSON.stringify({
              load_id: params.load_id,
              response_id: params.response_id,
              rate_types: [rateType],
              cancel_after_in_minutes: 4320,
              is_auto: false,
              need_archive_on_invite: false,
            }),
          }
        );

        if (resp.ok) {
          const result = await resp.json();
          return {
            content: [
              {
                type: "text",
                text: `Приглашение отправлено.\n${JSON.stringify(result, null, 2)}`,
              },
            ],
          };
        } else {
          const errText = await resp.text();
          return {
            content: [{ type: "text", text: `Error ${resp.status}: ${errText}` }],
          };
        }
      },
    });

    // ========================
    // СЕРВИС: Мониторинг откликов
    // ========================

    let monitorTimer: ReturnType<typeof setInterval> | null = null;

    api.registerService({
      id: "ati-monitor",
      async start() {
        // Инициализируем кэш до начала поллинга
        await initCache();

        const interval = config.monitorIntervalMs || 30000;
        api.logger.info(`ati-monitor: starting, poll every ${interval}ms`);

        async function poll() {
          if (activeCargos.size === 0) return;
          if (isMockMode) return;

          cleanupOldCargos();

          try {
            const resp = await fetch(`${ATI_BASE}/v1.0/loads/new/responses`, {
              headers,
            });
            if (!resp.ok) {
              api.logger.warn(`ati-monitor: poll failed ${resp.status}`);
              return;
            }

            const responses: any[] = await resp.json();
            let newCount = 0;

            for (const r of responses) {
              const responseId = String(
                r.ResponseId || r.Id || `${r.FirmId}_${r.LoadId}`
              );
              const loadId = String(r.LoadId || "");

              if (!activeCargos.has(loadId)) continue;
              if (seenResponseIds.has(responseId)) continue;

              seenResponseIds.add(responseId);
              pendingResponses.push({
                firm: r.FirmName || r.Firm || "unknown",
                price: r.Price || 0,
                firmId: String(r.FirmId || ""),
                loadId,
                responseId,
                timestamp: Date.now(),
              });
              newCount++;
            }

            if (newCount > 0) {
              api.logger.info(`ati-monitor: ${newCount} new responses found`);
            }
          } catch (err) {
            api.logger.error(`ati-monitor: poll error: ${err}`);
          }
        }

        await poll();
        monitorTimer = setInterval(poll, interval);
      },
      async stop() {
        if (monitorTimer) {
          clearInterval(monitorTimer);
          monitorTimer = null;
        }
        api.logger.info("ati-monitor: stopped");
      },
    });
  },
};

export default plugin;
