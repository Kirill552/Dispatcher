---
paths: "extensions/ati-cargo/**"
---

# ATI.su Cargo — расширение

## API

- Base URL: `https://api.ati.su`
- Авторизация: `Bearer ${apiToken}` в заголовке Authorization
- Формат: JSON

## Зарегистрированные инструменты

### Поиск и создание

| Tool | Метод | Endpoint | Когда использовать |
|------|-------|----------|-------------------|
| `ati_city_search` | POST | `/gw/gis-dict/v1/autocomplete/suggestions` | Клиент назвал город |
| `ati_create_cargo` | POST | `/v2/cargos` | Все данные заказа собраны и подтверждены |
| `ati_check_responses` | GET | `/v1.0/loads/new/responses` | Прямой запрос откликов к API |
| `ati_get_new_responses` | — | in-memory cache | Новые отклики из фонового мониторинга |

### Управление грузами (admin)

| Tool | Метод | Endpoint | Когда использовать |
|------|-------|----------|-------------------|
| `ati_my_loads` | GET | `/v1.0/loads` | Список активных грузов на бирже |
| `ati_renew_cargo` | PUT | `/v1.0/loads/{loadId}/renew` | Поднять груз в поиске |
| `ati_delete_cargo` | DELETE | `/v1.0/loads/{loadId}` | Удалить/архивировать груз |
| `ati_carrier_info` | GET | `/v1.0/firms/{atiId}/contacts/summary` | Репутация и контакты перевозчика |

### ATI Мессенджер (admin)

| Tool | Метод | Endpoint | Когда использовать |
|------|-------|----------|-------------------|
| `ati_create_chat` | POST | `/messenger/1.1/chats/` | Создать диалог с перевозчиком |
| `ati_send_message` | POST (multipart) | `/messenger/1.2/chats/{chat_id}/messages` | Отправить сообщение перевозчику |
| `ati_get_chat_history` | GET | `/messenger/1.1/chats/{chat_id}/history/` | История сообщений в чате |
| `ati_get_chats` | GET | `/messenger/1.2/subscriptions/` | Список всех чатов/подписок |

### Приглашение

| Tool | Метод | Endpoint | Когда использовать |
|------|-------|----------|-------------------|
| `ati_invite_carrier` | POST | `/v1.2/orders/invites/counter_offer` | Формализовать сделку с перевозчиком |

## Сервис

| Service | Описание |
|---------|----------|
| `ati-monitor` | Фоновый поллинг откликов каждые 30 сек. При старте кэширует boardId и contactId. Отслеживает грузы из `activeCargos`, складывает новые отклики в `pendingResponses` |

## Кэширование при запуске

При старте сервиса `ati-monitor` вызывается `initCache()`:
- `GET /v2/boards/public/boards/canAdd` → первая площадка с `can_add: true` → `cachedBoardId`
- `GET /v1.0/firms/contacts` → первый видимый контакт → `cachedContactId`
- Fallback: `config.boardId` если API не вернул
- Лог: `ati-cargo: cached boardId=... contactId=...`

## Словари (src/dictionaries.ts)

- `BODY_TYPES`: тип кузова → ATI ID (тент=200, реф=300, фургон=500, борт=1100)
- `LOADING_TYPES`: тип загрузки → ATI ID (верхняя=1, боковая=2, задняя=4)
- `UNLOADING_TYPES`: тип выгрузки → ATI ID
- `selectBodyType()`: определяет кузов по описанию груза (regex)

## Бизнес-модель

- **Комиссия:** 5000р (стартовая, корректируется по аналитике)
- **Минимальная комиссия при торге:** 3000р
- **Цена клиенту:** цена перевозчика + комиссия
- **Перевозчик:** везёт за свою цену, отдельно скидывает комиссию на карту
- **Бот представляется:** «диспетчер Кирилл» перевозчикам

## Конфигурация в openclaw.json

```json
"plugins": { "entries": { "ati-cargo": { "enabled": true, "config": {
  "apiToken": "${ATI_API_TOKEN}",
  "boardId": "",
  "monitorIntervalMs": 30000
}}}}
```

`boardId` опционален — авто-получение через API при старте.

## RBAC

**Guest** (все клиенты): `ati_city_search`, `ati_create_cargo`, `ati_check_responses`, `ati_get_new_responses`, `ati_carrier_info`, `memory_search`, `tenant_save`, `tenant_recall`, `analytics_log`

**Admin** (408001372): все инструменты (`*`)

## Паттерны

- `external_id`: `OC_${Date.now()}` — префикс OpenClaw для отслеживания
- Контакт: кэшируется при старте из `/v1.0/firms/contacts`
- Дата загрузки: `YYYY-MM-DDT00:00:00.000Z` — `YYYY-MM-DDT23:59:59.000Z`
- Оплата: `rate-request` (запрос ставки), с/без НДС, наличные
- ATI Мессенджер: между двумя пользователями один диалог, повторное создание возвращает существующий

## Shared State (in-memory)

- `cachedBoardId` — string | null — кэшированный ID площадки
- `cachedContactId` — string | null — кэшированный ID контакта
- `activeCargos` — Map<cargoId, TrackedCargo> — грузы для мониторинга (авто-очистка через 48ч)
- `seenResponseIds` — Set<responseId> — дедупликация откликов
- `pendingResponses` — CarrierResponse[] — очередь новых откликов для LLM

## Tenant Memory (extensions/tenant-memory)

Per-user изолированная RAG-память на LanceDB. Каждый пользователь — отдельная таблица `user_{id}`, общая аналитика — таблица `analytics`.

| Tool | Доступ | Описание |
|------|--------|----------|
| `tenant_save` | Guest + Admin | Сохранить данные клиента (заказы, предпочтения, сделки) |
| `tenant_recall` | Guest + Admin | Семантический поиск по памяти клиента + аналитике |
| `analytics_log` | Guest + Admin | Обезличенная аналитика (маршруты, цены) |
| `admin_search` | Admin only | Поиск по ВСЕМ таблицам (все пользователи + аналитика) |

**Категории:** `order`, `preference`, `deal`, `contact`, `note`, `setting`, `blacklist`, `route_price`, `deal_outcome`, `carrier_rate`, `market`

**Embedding:** `openai/text-embedding-3-small` (1536 dims) через OpenRouter

**Хранение:** Docker named volume `tenant-memory-data` → `/home/node/.openclaw/tenant-memory`

## Reference-файлы

- `reference/ati_client_v2.py` — оригинальный Python клиент
- `reference/ati_dictionaries_new.py` — оригинальные словари
- `reference/ati_api_v2_structure.json` — структура API v2
- `reference/business_logic_new.py` — бизнес-логика (старая, наценка 40%)
- `reference/offers_monitor.py` — мониторинг откликов
