---
paths: "extensions/ati-cargo/**"
---

# ATI.su Cargo — расширение

## API

- Base URL: `https://api.ati.su`
- Авторизация: `Bearer ${apiToken}` в заголовке Authorization
- Формат: JSON

## Зарегистрированные инструменты

| Tool | Метод | Endpoint | Когда использовать |
|------|-------|----------|-------------------|
| `ati_city_search` | POST | `/gw/gis-dict/v1/autocomplete/suggestions` | Клиент назвал город |
| `ati_create_cargo` | POST | `/v2/cargos` | Все данные заказа собраны и подтверждены |
| `ati_check_responses` | GET | `/v1.0/loads/new/responses` | Ждём отклики перевозчиков (прямой запрос к API) |
| `ati_get_new_responses` | — | in-memory cache | Получить новые отклики из фонового мониторинга |

## Сервис

| Service | Описание |
|---------|----------|
| `ati-monitor` | Фоновый поллинг откликов каждые 30 сек. Отслеживает грузы из `activeCargos`, складывает новые отклики в `pendingResponses` |

## Словари (src/dictionaries.ts)

- `BODY_TYPES`: тип кузова → ATI ID (тент=200, реф=300, фургон=500, борт=1100)
- `LOADING_TYPES`: тип загрузки → ATI ID (верхняя=1, боковая=2, задняя=4)
- `UNLOADING_TYPES`: тип выгрузки → ATI ID
- `selectBodyType()`: определяет кузов по описанию груза (regex)

## Конфигурация в openclaw.json

```json
"plugins": { "entries": { "ati-cargo": { "enabled": true, "config": {
  "apiToken": "${ATI_API_TOKEN}",
  "boardId": "a0a0a0a0a0a0a0a0a0a0a0a0",
  "monitorIntervalMs": 30000
}}}}
```

## Паттерны

- `external_id`: `OC_${Date.now()}` — префикс OpenClaw для отслеживания
- Контакт: берётся первый видимый из `/v1.0/firms/contacts`
- Дата загрузки: `YYYY-MM-DDT00:00:00.000Z` — `YYYY-MM-DDT23:59:59.000Z`
- Оплата: `rate-request` (запрос ставки), с/без НДС, наличные

## Shared State (in-memory)

- `activeCargos` — Map<cargoId, TrackedCargo> — грузы для мониторинга (авто-очистка через 48ч)
- `seenResponseIds` — Set<responseId> — дедупликация откликов
- `pendingResponses` — CarrierResponse[] — очередь новых откликов для LLM

## TODO (Phase 3)

- Мониторинг статусов грузов (архивирование, снятие)
- Автоматическое уведомление владельца о новых откликах через Telegram

## Reference-файлы

- `reference/ati_client_v2.py` — оригинальный Python клиент
- `reference/ati_dictionaries_new.py` — оригинальные словари
- `reference/ati_api_v2_structure.json` — структура API v2
- `reference/business_logic_new.py` — бизнес-логика (наценка, торг)
- `reference/offers_monitor.py` — мониторинг откликов
