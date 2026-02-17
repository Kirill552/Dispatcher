import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { Type } from "@sinclair/typebox";

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
let cachedBoardId: string | null = null;
let cachedContactId: string | null = null;

// Очистка грузов старше 48 часов
function cleanupOldCargos() {
  const cutoff = Date.now() - 48 * 60 * 60 * 1000;
  for (const [id, cargo] of activeCargos) {
    if (cargo.createdAt < cutoff) activeCargos.delete(id);
  }
}

const plugin = {
  id: "ati-cargo",
  name: "ATI.su Cargo",
  description:
    "ATI.su freight exchange integration: create cargos, check responses, search cities, manage loads, messenger, carrier info",
  version: "3.0.0",
  configSchema: {
    type: "object" as const,
    properties: {
      apiToken: { type: "string" as const },
      boardId: { type: "string" as const },
      monitorIntervalMs: { type: "number" as const },
    },
  },

  register(api: OpenClawPluginApi) {
    const config = api.pluginConfig as {
      apiToken: string;
      boardId?: string;
      monitorIntervalMs?: number;
    };

    const ATI_BASE = "https://api.ati.su";
    const headers = {
      Authorization: `Bearer ${config.apiToken}`,
      "Content-Type": "application/json",
      Accept: "application/json",
      "User-Agent": "openclaw-ati-cargo/3.0",
    };

    // --- initCache: авто-получение boardId и contactId при запуске ---
    async function initCache() {
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
        loading_date: Type.String({ description: "Loading date YYYY-MM-DD" }),
        loading_type_id: Type.Optional(
          Type.Number({
            description: "Loading type: 1=top, 2=side, 4=rear. Default 2",
          })
        ),
      }),
      async execute(_toolCallId, params) {
        if (!cachedContactId) {
          return {
            content: [
              {
                type: "text",
                text: "Error: no ATI contact cached. Service may not have started.",
              },
            ],
          };
        }

        const boardId = cachedBoardId || config.boardId || "";
        if (!boardId) {
          return {
            content: [
              {
                type: "text",
                text: "Error: no boardId available. Check config or API access.",
              },
            ],
          };
        }

        const loadDate = params.loading_date;

        const payload = {
          cargo_application: {
            external_id: `OC_${Date.now()}`,
            route: {
              loading: {
                location: {
                  type: "manual",
                  city_id: params.loading_city_id,
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
            payment: {
              type: "rate-request",
              currency_type: 1,
              hide_counter_offers: false,
              direct_offer: false,
              cash_available: true,
              rate_with_nds_available: true,
              rate_without_nds_available: true,
            },
            boards: [
              {
                id: boardId,
                publication_mode: "now",
                publication_time: "1970-01-01T00:00:00.000Z",
                cancel_publish_on_auction_bet: false,
                reservation_enabled: false,
              },
            ],
            note: "Пишите в мессенджер АТИ, на звонки не отвечаю",
            contacts: [Number(cachedContactId)],
          },
        };

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

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(
                  {
                    success: true,
                    cargo_id: cargoId,
                    cargo_number:
                      cargoApp.cargo_application_number || cargoApp.cargo_number,
                  },
                  null,
                  2
                ),
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

        const summary = responses.map((r: any) => ({
          firm: r.FirmName,
          price: r.Price,
          firm_id: r.FirmId,
          load_id: r.LoadId,
          response_id: String(r.ResponseId || r.Id || ""),
        }));

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
        const resp = await fetch(`${ATI_BASE}/v1.0/loads`, { headers });
        if (!resp.ok) {
          return {
            content: [{ type: "text", text: `Error ${resp.status}` }],
          };
        }

        const loads: any[] = await resp.json();
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
