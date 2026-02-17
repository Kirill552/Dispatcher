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
  description: "ATI.su freight exchange integration: create cargos, check responses, search cities, monitor carrier offers",
  version: "2.0.0",
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
      "User-Agent": "openclaw-ati-cargo/2.0",
    };

    // --- Tool: ati_city_search ---
    api.registerTool({
      name: "ati_city_search",
      label: "ATI City Search",
      description:
        "Search for a city ID on ATI.su by name. Use when the client mentions a city for loading or unloading.",
      parameters: Type.Object({
        city_name: Type.String({ description: "City name in Russian, e.g. 'Сарапул'" }),
      }),
      async execute(_toolCallId, params) {
        const resp = await fetch(`${ATI_BASE}/gw/gis-dict/v1/autocomplete/suggestions`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            prefix: params.city_name,
            suggestion_types: 1,
            limit: 5,
            country_id: 1,
          }),
        });
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
        loading_city_id: Type.Number({ description: "ATI city ID for loading point" }),
        unloading_city_id: Type.Number({ description: "ATI city ID for unloading point" }),
        cargo_description: Type.String({ description: "Cargo description, e.g. 'мебель'" }),
        weight: Type.Number({ description: "Weight in kilograms" }),
        volume: Type.Number({ description: "Volume in cubic meters" }),
        body_type_id: Type.Number({
          description: "Body type: 200=tent, 300=reefer, 500=van, 1100=flatbed",
        }),
        loading_date: Type.String({ description: "Loading date YYYY-MM-DD" }),
        loading_type_id: Type.Optional(
          Type.Number({ description: "Loading type: 1=top, 2=side, 4=rear. Default 2" })
        ),
      }),
      async execute(_toolCallId, params) {
        // Get contact ID
        const contactResp = await fetch(`${ATI_BASE}/v1.0/firms/contacts`, { headers });
        const contacts = await contactResp.json();
        const contact =
          contacts.find((c: any) => c.is_visible && !c.is_deleted) || contacts[0];
        if (!contact) {
          return { content: [{ type: "text", text: "Error: no ATI contact found" }] };
        }

        const boardId = config.boardId || "a0a0a0a0a0a0a0a0a0a0a0a0";
        const loadDate = params.loading_date;

        const payload = {
          cargo_application: {
            external_id: `OC_${Date.now()}`,
            route: {
              loading: {
                location: { type: "manual", city_id: params.loading_city_id },
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
                location: { type: "manual", city_id: params.unloading_city_id },
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
            note: "",
            contacts: [contact.id],
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
          const cargoId = String(cargoApp.cargo_application_id || cargoApp.cargo_id || "");

          // Регистрируем груз для мониторинга
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
            description: "Cargo ID to filter responses. If omitted, returns all.",
          })
        ),
      }),
      async execute(_toolCallId, params) {
        const resp = await fetch(`${ATI_BASE}/v1.0/loads/new/responses`, { headers });
        if (!resp.ok) {
          return { content: [{ type: "text", text: `Error ${resp.status}` }] };
        }

        let responses = await resp.json();
        if (params.cargo_id) {
          responses = responses.filter((r: any) => r.LoadId === params.cargo_id);
        }

        const summary = responses.map((r: any) => ({
          firm: r.FirmName,
          price: r.Price,
          firm_id: r.FirmId,
          load_id: r.LoadId,
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
            description: "Filter by cargo ID. If omitted, returns all new responses.",
          })
        ),
      }),
      async execute(_toolCallId, params) {
        let results: CarrierResponse[];
        if (params.cargo_id) {
          results = pendingResponses.filter((r) => r.loadId === params.cargo_id);
          // Убираем выданные из очереди
          const remaining = pendingResponses.filter((r) => r.loadId !== params.cargo_id);
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

    // --- Service: ati-monitor ---
    let monitorTimer: ReturnType<typeof setInterval> | null = null;

    api.registerService({
      id: "ati-monitor",
      async start() {
        const interval = config.monitorIntervalMs || 30000;
        api.logger.info(`ati-monitor: starting, poll every ${interval}ms`);

        async function poll() {
          if (activeCargos.size === 0) return;

          cleanupOldCargos();

          try {
            const resp = await fetch(`${ATI_BASE}/v1.0/loads/new/responses`, { headers });
            if (!resp.ok) {
              api.logger.warn(`ati-monitor: poll failed ${resp.status}`);
              return;
            }

            const responses: any[] = await resp.json();
            let newCount = 0;

            for (const r of responses) {
              const responseId = String(r.ResponseId || r.Id || `${r.FirmId}_${r.LoadId}`);
              const loadId = String(r.LoadId || "");

              // Только отклики на наши грузы
              if (!activeCargos.has(loadId)) continue;
              // Только новые отклики
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

        // Первый поллинг сразу
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
