import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { Type } from "@sinclair/typebox";

// LanceDB импортируется динамически при старте сервиса
let lancedb: any;

const VECTOR_DIM = 1536; // text-embedding-3-small

const plugin = {
  id: "tenant-memory",
  name: "Tenant Memory",
  description:
    "Per-user isolated RAG memory with shared analytics. Each user gets their own LanceDB table. Admin can search across all.",
  version: "1.0.0",
  configSchema: {
    type: "object" as const,
    properties: {
      embeddingApiKey: { type: "string" as const },
      embeddingModel: { type: "string" as const },
      embeddingBaseUrl: { type: "string" as const },
      dataPath: { type: "string" as const },
      adminUserId: { type: "string" as const },
      maxRecallResults: { type: "number" as const },
    },
  },

  register(api: OpenClawPluginApi) {
    const config = api.pluginConfig as {
      embeddingApiKey: string;
      embeddingModel?: string;
      embeddingBaseUrl?: string;
      dataPath?: string;
      adminUserId: string;
      maxRecallResults?: number;
    };

    const EMBEDDING_MODEL =
      config.embeddingModel || "openai/text-embedding-3-small";
    const EMBEDDING_BASE_URL =
      config.embeddingBaseUrl || "https://openrouter.ai/api/v1";
    const DATA_PATH =
      config.dataPath || "/home/node/.openclaw/tenant-memory";
    const ADMIN_USER_ID = config.adminUserId;
    const MAX_RESULTS = config.maxRecallResults || 5;

    let db: any = null;

    // ========================
    // Embedding API (OpenRouter)
    // ========================

    async function getEmbedding(text: string): Promise<number[]> {
      const resp = await fetch(`${EMBEDDING_BASE_URL}/embeddings`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${config.embeddingApiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: EMBEDDING_MODEL,
          input: text,
        }),
      });

      if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(`Embedding API ${resp.status}: ${errText}`);
      }

      const data = await resp.json();
      return data.data[0].embedding;
    }

    // ========================
    // LanceDB helpers
    // ========================

    async function getDb(): Promise<any> {
      if (!db) {
        // Попробовать новый пакет, fallback на старый
        try {
          lancedb = await import("@lancedb/lancedb");
        } catch {
          lancedb = await import("vectordb");
        }
        db = await lancedb.connect(DATA_PATH);
      }
      return db;
    }

    async function getOrCreateTable(name: string): Promise<any> {
      const database = await getDb();
      const names: string[] = await database.tableNames();

      if (names.includes(name)) {
        return await database.openTable(name);
      }

      // LanceDB требует хотя бы одну строку для создания схемы
      const table = await database.createTable(name, [
        {
          vector: new Array(VECTOR_DIM).fill(0),
          text: "",
          category: "_init",
          user_id: "",
          timestamp: 0,
          metadata: "{}",
        },
      ]);

      api.logger.info(`tenant-memory: created table ${name}`);
      return table;
    }

    function userTableName(userId: string): string {
      const safe = userId.replace(/[^a-zA-Z0-9]/g, "_");
      return `user_${safe}`;
    }

    // Санитизация категории для SQL WHERE
    function safeCategory(cat: string): string {
      return cat.replace(/[^a-zA-Z0-9_]/g, "");
    }

    // Общий поиск по одной таблице
    async function searchTable(
      name: string,
      vector: number[],
      limit: number,
      category?: string
    ): Promise<any[]> {
      const database = await getDb();
      const names: string[] = await database.tableNames();

      if (!names.includes(name)) return [];

      const table = await database.openTable(name);
      let query = table.search(vector).limit(limit);

      if (category) {
        query = query.where(`category = '${safeCategory(category)}'`);
      }

      const results = await query.toArray();
      return results.filter((r: any) => r.category !== "_init");
    }

    // ========================
    // ИНСТРУМЕНТЫ
    // ========================

    // --- tenant_save: сохранить данные клиента ---
    api.registerTool({
      name: "tenant_save",
      label: "Save User Memory",
      description:
        "Save information about a client to their isolated personal memory. Use after collecting order details, client preferences, contact info, or completing a deal. Each user's data is stored separately and never mixes with other users.",
      parameters: Type.Object({
        user_id: Type.String({
          description: "Telegram user ID of the client",
        }),
        text: Type.String({
          description:
            "Text to remember — will be embedded for semantic search. Include key facts: route, weight, volume, cargo type, preferences, deal result.",
        }),
        category: Type.String({
          description:
            "Category: order | preference | deal | contact | note",
        }),
        metadata: Type.Optional(
          Type.String({
            description:
              'JSON string with structured data, e.g. {"route":"Казань→Москва","weight":2000,"price":28000}',
          })
        ),
      }),
      async execute(_toolCallId, params) {
        try {
          const vector = await getEmbedding(params.text);
          const table = await getOrCreateTable(userTableName(params.user_id));

          await table.add([
            {
              vector,
              text: params.text,
              category: params.category,
              user_id: params.user_id,
              timestamp: Date.now(),
              metadata: params.metadata || "{}",
            },
          ]);

          api.logger.info(
            `tenant-memory: saved for user=${params.user_id} category=${params.category}`
          );
          return {
            content: [{ type: "text", text: "Saved to user memory." }],
          };
        } catch (err) {
          api.logger.error(`tenant-memory: save error: ${err}`);
          return {
            content: [
              { type: "text", text: `Memory save error: ${err}` },
            ],
          };
        }
      },
    });

    // --- tenant_recall: поиск по памяти клиента + аналитика ---
    api.registerTool({
      name: "tenant_recall",
      label: "Recall User Memory",
      description:
        "Search a client's personal memory for relevant context. Also searches shared analytics for route/price data. Use at the start of conversation to recall past orders, preferences, or when client asks about previous deals.",
      parameters: Type.Object({
        user_id: Type.String({
          description: "Telegram user ID of the client",
        }),
        query: Type.String({
          description:
            "What to search for, e.g. 'предыдущие заказы Казань' or 'предпочтения клиента'",
        }),
        category: Type.Optional(
          Type.String({
            description:
              "Filter by category: order, preference, deal, contact (optional)",
          })
        ),
      }),
      async execute(_toolCallId, params) {
        try {
          const vector = await getEmbedding(params.query);
          const results: any[] = [];

          // Поиск в таблице пользователя
          const userResults = await searchTable(
            userTableName(params.user_id),
            vector,
            MAX_RESULTS,
            params.category
          );
          for (const r of userResults) {
            results.push({
              text: r.text,
              category: r.category,
              timestamp: r.timestamp,
              metadata: r.metadata,
              source: "user",
              _distance: r._distance,
            });
          }

          // Поиск в общей аналитике (маршруты, цены)
          const analyticsResults = await searchTable(
            "analytics",
            vector,
            3
          );
          for (const r of analyticsResults) {
            results.push({
              text: r.text,
              category: r.category,
              timestamp: r.timestamp,
              metadata: r.metadata,
              source: "analytics",
              _distance: r._distance,
            });
          }

          // Сортировка по релевантности (меньше distance = ближе)
          results.sort(
            (a, b) => (a._distance || 0) - (b._distance || 0)
          );
          const topResults = results.slice(0, MAX_RESULTS);

          if (topResults.length === 0) {
            return {
              content: [
                {
                  type: "text",
                  text: "No memories found for this user.",
                },
              ],
            };
          }

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(topResults, null, 2),
              },
            ],
          };
        } catch (err) {
          api.logger.error(`tenant-memory: recall error: ${err}`);
          return {
            content: [
              { type: "text", text: `Memory recall error: ${err}` },
            ],
          };
        }
      },
    });

    // --- analytics_log: общая аналитика (маршруты, цены, рынок) ---
    api.registerTool({
      name: "analytics_log",
      label: "Log Analytics",
      description:
        "Save anonymized analytics data: route prices, carrier rates, deal outcomes. Shared across all sessions for market intelligence. Do NOT include client names or personal info — only routes, prices, and market data.",
      parameters: Type.Object({
        text: Type.String({
          description:
            "Analytics text, e.g. 'Казань→Москва: перевозчики 25000, 28000, 31000. Сделка 28000+5000 комиссия'",
        }),
        category: Type.String({
          description:
            "Category: route_price | deal_outcome | carrier_rate | market",
        }),
        metadata: Type.Optional(
          Type.String({
            description:
              'JSON with structured data, e.g. {"from":"Казань","to":"Москва","min_price":25000,"avg_price":28000}',
          })
        ),
      }),
      async execute(_toolCallId, params) {
        try {
          const vector = await getEmbedding(params.text);
          const table = await getOrCreateTable("analytics");

          await table.add([
            {
              vector,
              text: params.text,
              category: params.category,
              user_id: "system",
              timestamp: Date.now(),
              metadata: params.metadata || "{}",
            },
          ]);

          api.logger.info(
            `tenant-memory: analytics logged category=${params.category}`
          );
          return {
            content: [{ type: "text", text: "Analytics data saved." }],
          };
        } catch (err) {
          api.logger.error(`tenant-memory: analytics error: ${err}`);
          return {
            content: [
              { type: "text", text: `Analytics save error: ${err}` },
            ],
          };
        }
      },
    });

    // --- telegram_notify: уведомление владельца в Telegram --- 
    api.registerTool({
      name: "telegram_notify",
      label: "Telegram Notify Owner",
      description:
        "Отправляет служебное уведомление владельцу (adminUserId) в Telegram. Используй для эскалаций, негатива, техпроблем и закрытых сделок.",
      parameters: Type.Object({
        text: Type.String({
          description: "Короткий текст уведомления для владельца.",
        }),
        severity: Type.Optional(
          Type.Union([
            Type.Literal("info"),
            Type.Literal("warning"),
            Type.Literal("escalation"),
            Type.Literal("deal"),
            Type.Literal("negative"),
            Type.Literal("technical"),
            Type.Literal("test"),
          ])
        ),
        correlation_id: Type.Optional(
          Type.String({
            description: "Идентификатор корреляции для e2e и трассировки.",
          })
        ),
        user_id: Type.Optional(
          Type.String({
            description: "Telegram user_id клиента (если есть).",
          })
        ),
        route: Type.Optional(
          Type.String({
            description: "Маршрут, например: Москва → Казань.",
          })
        ),
      }),
      async execute(_toolCallId, params) {
        const botToken = process.env.TELEGRAM_BOT_TOKEN?.trim();
        if (!botToken) {
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(
                  {
                    sent: false,
                    error: "TELEGRAM_BOT_TOKEN is not configured",
                  },
                  null,
                  2
                ),
              },
            ],
          };
        }

        const severity = params.severity || "info";
        const prefixBySeverity: Record<string, string> = {
          info: "ℹ️ [INFO]",
          warning: "⚠️ [WARN]",
          escalation: "🚨 [ESCALATION]",
          deal: "✅ [DEAL]",
          negative: "🧯 [NEGATIVE]",
          technical: "🛠 [TECH]",
          test: "🧪 [E2E]",
        };
        const prefix = prefixBySeverity[severity] || prefixBySeverity.info;

        const details: string[] = [];
        if (params.user_id) details.push(`Клиент: ${params.user_id}`);
        if (params.route) details.push(`Маршрут: ${params.route}`);
        if (params.correlation_id) details.push(`corr: ${params.correlation_id}`);

        const messageLines = [`${prefix} ${params.text}`];
        if (details.length > 0) {
          messageLines.push("");
          messageLines.push(...details);
        }

        try {
          const resp = await fetch(
            `https://api.telegram.org/bot${botToken}/sendMessage`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                chat_id: ADMIN_USER_ID,
                text: messageLines.join("\n"),
                disable_web_page_preview: true,
              }),
            }
          );

          const raw = await resp.text();
          let parsed: any = null;
          try {
            parsed = raw ? JSON.parse(raw) : null;
          } catch {
            parsed = null;
          }

          if (!resp.ok || !parsed?.ok) {
            api.logger.error(
              `telegram_notify: failed status=${resp.status} body=${raw.slice(0, 400)}`
            );
            return {
              content: [
                {
                  type: "text",
                  text: JSON.stringify(
                    {
                      sent: false,
                      http_status: resp.status,
                      error: parsed?.description || raw || "telegram api error",
                    },
                    null,
                    2
                  ),
                },
              ],
            };
          }

          const messageId = parsed?.result?.message_id ?? null;
          const corr = params.correlation_id ? ` corr=${params.correlation_id}` : "";
          api.logger.info(
            `telegram_notify: sent chat_id=${ADMIN_USER_ID} message_id=${messageId}${corr}`
          );

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(
                  {
                    sent: true,
                    chat_id: ADMIN_USER_ID,
                    message_id: messageId,
                    correlation_id: params.correlation_id || null,
                  },
                  null,
                  2
                ),
              },
            ],
          };
        } catch (err) {
          api.logger.error(`telegram_notify: exception: ${err}`);
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(
                  {
                    sent: false,
                    error: String(err),
                  },
                  null,
                  2
                ),
              },
            ],
          };
        }
      },
    });

    // --- admin_search: поиск по ВСЕМ таблицам (только админ) ---
    api.registerTool({
      name: "admin_search",
      label: "Admin Memory Search",
      description:
        "Search across ALL user memories and analytics. Admin only (408001372). Use for analytics dashboards, finding specific client data, reviewing deal history across all users, or market analysis by route.",
      parameters: Type.Object({
        query: Type.String({
          description: "Search query",
        }),
        user_id: Type.Optional(
          Type.String({
            description:
              "Search only specific user's table (optional, omit for all)",
          })
        ),
        category: Type.Optional(
          Type.String({
            description: "Filter by category (optional)",
          })
        ),
        limit: Type.Optional(
          Type.Number({
            description: "Max results (default 10)",
          })
        ),
      }),
      async execute(_toolCallId, params) {
        try {
          const vector = await getEmbedding(params.query);
          const database = await getDb();
          const allNames: string[] = await database.tableNames();
          const limit = params.limit || MAX_RESULTS * 2;
          const results: any[] = [];

          // Определяем какие таблицы искать
          const tablesToSearch = params.user_id
            ? [userTableName(params.user_id)]
            : allNames;

          for (const name of tablesToSearch) {
            try {
              const tableResults = await searchTable(
                name,
                vector,
                MAX_RESULTS,
                params.category
              );
              for (const r of tableResults) {
                results.push({
                  text: r.text,
                  category: r.category,
                  user_id: r.user_id,
                  timestamp: r.timestamp,
                  metadata: r.metadata,
                  table: name,
                  _distance: r._distance,
                });
              }
            } catch {
              // Пропускаем таблицы с ошибками
            }
          }

          results.sort(
            (a, b) => (a._distance || 0) - (b._distance || 0)
          );
          const topResults = results.slice(0, limit);

          return {
            content: [
              {
                type: "text",
                text: `${topResults.length} results across ${allNames.length} tables:\n${JSON.stringify(topResults, null, 2)}`,
              },
            ],
          };
        } catch (err) {
          api.logger.error(`tenant-memory: admin search error: ${err}`);
          return {
            content: [
              { type: "text", text: `Admin search error: ${err}` },
            ],
          };
        }
      },
    });

    // ========================
    // СЕРВИС: инициализация LanceDB при старте
    // ========================

    api.registerService({
      id: "tenant-memory-init",
      async start() {
        try {
          await getDb();
          const names: string[] = await db.tableNames();
          api.logger.info(
            `tenant-memory: initialized at ${DATA_PATH}, ${names.length} tables`
          );
        } catch (err) {
          api.logger.error(`tenant-memory: init failed: ${err}`);
        }
      },
      async stop() {
        db = null;
        api.logger.info("tenant-memory: stopped");
      },
    });
  },
};

export default plugin;
