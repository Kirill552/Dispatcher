# ATI.su API v2 -- Полный справочник

> Составлено 2026-02-17 из официальной документации https://ati.su/developers/
> Базовый URL: `https://api.ati.su`

---

## Содержание

1. [Авторизация](#1-авторизация)
2. [Требования и ограничения](#2-требования-и-ограничения)
3. [Площадки (Boards)](#3-площадки-boards)
4. [Грузы (Cargoes / Loads)](#4-грузы-cargoes--loads)
5. [Опубликованные грузы -- создание](#5-опубликованные-грузы--создание)
6. [Сценарий: Добавить груз](#6-сценарий-добавить-груз)
7. [Сценарий: Найти исполнителя](#7-сценарий-найти-исполнителя)
8. [Торги (Auctions)](#8-торги-auctions)
9. [Работа с заказами (Orders / Deals)](#9-работа-с-заказами-orders--deals)
10. [АТИ Мессенджер](#10-ати-мессенджер)
11. [Фирмы (Firms)](#11-фирмы-firms)
12. [Словари: Грузы](#12-словари-грузы)
13. [Словари: Гео объекты](#13-словари-гео-объекты)
14. [Вебхуки (Webhooks)](#14-вебхуки-webhooks)
15. [Вебхуки: Тема "Грузы"](#15-вебхуки-тема-грузы)

---

## 1. Авторизация

### Типы токенов

| Тип | Срок жизни | Назначение |
|-----|-----------|------------|
| Временный | 7 дней | Автоматически выдается при тестировании в api-panda-portal |
| Постоянный | До смены пароля / удаления контакта / удаления компании | Для интеграций, создается через `client_id` |

### Получение client_id

**Для клиентов интеграторов:** запросить `client_id` у интегратора.

**Для интеграторов:**
1. Зарегистрироваться на ATI.SU
2. Верифицировать аккаунт
3. Подать тикет в "Консультанты по интеграции (API)" с указанием:
   - ФИО и email ответственного
   - Название ПО
   - Цель использования API

### Создание access_token

Перейти в "Мои токены", ввести `client_id`, нажать "Создать токен".

### Заголовок авторизации

```
Authorization: Bearer {access_token}
```

### Когда токен перестает действовать

- Смена пароля контакта
- Удаление контакта
- Удаление компании
- Нарушение политики (блокировка)

### OAuth 2.0

Доступна альтернативная авторизация через OAuth 2.0 -- см. `/developers/auth/auth-v2/`.

---

## 2. Требования и ограничения

### Rate Limits

| Лимит | Значение | Сброс |
|-------|---------|-------|
| Общий | 10 запросов/сек на контакт | -- |
| POST /v2/cargos (создание) | 500 запросов/24ч на контакт | 00:00 UTC |
| PUT /v2/cargos/{guid} (обновление) | 5000 запросов/24ч на контакт | 00:00 UTC |

Формула для фирмы: `кол-во_контактов * 500 = дневной лимит создания`

При превышении возвращается HTTP `429 Too Many Requests`. Использовать экспоненциальный backoff начиная с 100ms.

### Обязательные заголовки

```http
Accept-Encoding: gzip, deflate, br
User-Agent: ati_integrator_<КОД>
Authorization: Bearer {token}
Content-Type: application/json
Accept: application/json
```

### Требования к протоколу

- HTTPS обязателен (TLS 1.2 или TLS 1.3), с 1 августа 2022
- Поддержка автоматических редиректов (301/302 через `Location`)
- Обработка ошибок сокетов (ECONNRESET, ENOTCONN) с повторными попытками

---

## 3. Площадки (Boards)

Площадки ATI.SU -- сервис распределения грузов между доверенными перевозчиками и экспедиторами. Максимум **100 площадок** на фирму.

### Терминология

- **Board** -- площадка с участниками
- **Participant / Participation** -- запись об участии
- **Type=invited** -- приглашен, но не принял
- **Type=user** -- полноправный участник

### Направления обмена (BoardExchangeDirection)

| Значение | Описание |
|----------|----------|
| `input` | Участники публикуют грузы для владельца |
| `output` | Владелец публикует грузы для участников |
| `exchange` | Двусторонний обмен |

### 3.1 Создание площадки

```
POST /v2/boards/public/boards/create
```

**Request Body:**
```json
{
  "all_departments_allowed": true,
  "board_exchange_direction": "output",
  "board_type": "loads",
  "color": "#FF00FF",
  "departments_ids": [],
  "description": "Описание площадки",
  "name_for_users": "Публичное имя (до 50 символов)",
  "private_name": "Внутреннее имя (до 50 символов)",
  "public": false,
  "responsible_contact_id": 1,
  "rules": "Правила участия"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| all_departments_allowed | boolean | Доступна всем подразделениям |
| board_exchange_direction | enum | input / output / exchange |
| board_type | string | Только `loads` (trucks -- зарезервировано) |
| color | string | Цвет плашки, формат "#RRGGBB" |
| departments_ids | int32[] | ID подразделений (если all_departments_allowed=false) |
| description | string | HTML-теги: b, i, span, u, ul, li, br |
| name_for_users | string | Публичное имя, макс 50 символов |
| private_name | string | Имя для владельца, макс 50 символов |
| public | boolean | true = открытая (заявки), false = закрытая (только приглашения) |
| responsible_contact_id | int32 | ID ответственного контакта |
| rules | string | Правила, HTML-теги допускаются |

**Response 200:**
```json
{
  "id": "507f1f77bcf86cd799439011",
  "name": "Образцово-показательная площадка",
  "board_exchange_direction": "output",
  "board_type": "loads",
  "color": "#FF00FF",
  "owner_firm": 1111111,
  "created_on": 1556201954901,
  "updated_on": 1556201954901,
  "all_departments_allowed": true,
  "departments_ids": [],
  "available_for_contact": true,
  "view_only_own": true
}
```

**cURL:**
```bash
curl 'https://api.ati.su/v2/boards/public/boards/create' \
  -X POST \
  -H 'Authorization: Bearer {token}' \
  -H 'Content-Type: application/json' \
  --data-raw '{"all_departments_allowed":true,"board_exchange_direction":"output","board_type":"loads","color":"#FF00FF","departments_ids":[],"description":"string","name_for_users":"string","private_name":"string","public":false,"responsible_contact_id":1,"rules":"string"}'
```

### 3.2 Получение площадки по ID

```
GET /v2/boards/public/boards/{id}
```

- `id` -- строка из 24 символов

**cURL:**
```bash
curl 'https://api.ati.su/v2/boards/public/boards/507f1f77bcf86cd799439011' \
  -X GET \
  -H 'Authorization: Bearer {token}'
```

### 3.3 Список всех актуальных площадок

```
GET /v2/boards/public/boards/list
```

**Response 200:** массив объектов площадок с дополнительными полями:

| Поле | Тип | Описание |
|------|-----|----------|
| auctions_count | int32 | Количество торгов |
| can_add | boolean | Можно добавлять грузы |
| can_view | boolean | Можно просматривать грузы |
| content_count | int64 | Количество грузов |
| participants_count | int64 | Количество участников |
| tenders_count | int32 | Количество тендеров |

### 3.4 Площадки для добавления груза (canAdd)

```
GET /v2/boards/public/boards/canAdd
```

Возвращает площадки, на которые пользователь может добавлять грузы.

### 3.5 Площадки для просмотра грузов (canView)

```
GET /v2/boards/public/boards/canView
```

### 3.6 Мои площадки (ID)

```
GET /v2/boards/public/boards/my
```

Возвращает массив строковых ID площадок, созданных текущим пользователем.

### 3.7 Площадки с моим участием (ID)

```
GET /v2/boards/public/boards/participating
```

### 3.8 Типы участия на площадках

| Type | Описание |
|------|----------|
| `user` | Полноправный участник |
| `invited` | Приглашение ожидает принятия |
| `invitedViewed` | Приглашение просмотрено |
| `rejected` | Отклонил участие |
| `revoked` | Приглашение отозвано |
| `left` | Покинул площадку |
| `deleted` | Удален с площадки |
| `owner` | Создатель площадки |

### 3.9 Приглашение участника

```
POST /v2/boards/public/participants/invite
```

**Request Body:**
```json
{
  "ati_id": "1234567",
  "board_id": "507f1f77bcf86cd799439011",
  "contact_id": 42
}
```

**Response 200:** строка (ID приглашения)

### 3.10 Мои входящие приглашения

```
GET /v2/boards/public/participants/invite/my
```

**Response 200:** массив объектов:
```json
{
  "board_info": { "...": "данные площадки" },
  "participant": {
    "ati_id": "string",
    "board_id": "string",
    "type": "invited",
    "created_on": "date-time",
    "type_changed": "date-time",
    "sender_ati_id": "string",
    "responsible_contact_id": 0,
    "can_add": false,
    "view_content": true,
    "view_participants": false
  }
}
```

### 3.11 Список участников площадки

```
POST /v2/boards/public/participants/list
```

**Request Body:**
```json
{
  "board_ids": ["507f1f77bcf86cd799439011"],
  "only_my": false,
  "type": "user",
  "offset": 0,
  "limit": 50
}
```

**Response 200:**
```json
{
  "result": [
    {
      "ati_id": "string",
      "board_id": "string",
      "type": "user",
      "created_on": "date-time",
      "type_changed": "date-time",
      "sender_ati_id": "string",
      "responsible_contact_id": 0,
      "can_add": true,
      "view_content": true,
      "view_participants": false
    }
  ],
  "total_count": 1
}
```

### 3.12 Модификация участника

```
PUT /v2/boards/public/participants/{participantId}
```

Позволяет менять права доступа: `can_add`, `view_content`, `view_participants`.

### Legacy API (v1.0) -- устаревшее

| v1.0 | v2 |
|------|-----|
| `/v1.0/boards/external/board/create` | `/v2/boards/public/boards/create` |
| `/v1.0/boards/external/board/{id}` | `/v2/boards/public/boards/{id}` |
| `/v1.0/boards/external/board/list` | `/v2/boards/public/boards/list` |
| `/v1.0/boards/external/board/canAdd` | `/v2/boards/public/boards/canAdd` |
| `/v1.0/boards/external/board/canView` | `/v2/boards/public/boards/canView` |
| `/v1.0/boards/external/invite` | `/v2/boards/public/participants/invite` |
| `/v1.0/boards/external/invite/my` | `/v2/boards/public/participants/invite/my` |

---

## 4. Грузы (Cargoes / Loads)

### Возможности API

**Грузовладелец:**
- Добавление, обновление, редактирование и удаление грузов
- Настройка приоритетного показа
- Получение встречных предложений

**Перевозчик:**
- Поиск грузов на площадках компании
- Добавление и редактирование встречных предложений
- Добавление и редактирование комментариев к грузам

### Дублирование грузов

Система автоматически определяет дубликаты по 21 параметру (тип груза, вес, объем, упаковка, города, типы кузова, даты, ставки и т.д.).

- **Дубликат найден:** HTTP `409` с кодом `load_conflict_error`
- **Частичное совпадение:** HTTP `202` (система мержит записи)

### Коды ошибок

| Код ошибки | Описание |
|-----------|----------|
| `json_validation_error` | Ошибка валидации тела запроса |
| `deserialization_error` | Ошибка десериализации |
| `load_conflict_error` | Обнаружен дубликат груза |
| `load_archive_delay_not_elapsed` | Груз архивирован менее 60 минут назад |
| `access_denied_error` | Недостаточно прав |
| `load_not_found_error` | Груз не найден |
| `city_not_found_error` | Город не найден в системе |
| `dictionary_element_not_found_error` | Элемент справочника не найден |

### Формат ошибок

```json
{
  "Error": "load_not_found_error",
  "Reason": "Груз с указанным ID не найден",
  "ErrorsList": []
}
```

---

## 5. Опубликованные грузы -- создание

### Создать груз (POST /v2/cargos)

```
POST /v2/cargos
```

**Лимит:** макс 500 запросов на создание за 24 часа на один контакт. Сброс в 00:00 UTC.

**Request Body:** объект `cargo_application`:

```json
{
  "cargo_application": {
    "external_id": "ORDER-12345",
    "route": {
      "loading": {
        "location": { "type": "manual" },
        "city_id": 36942,
        "address": "ул. Ленина, 1"
      },
      "unloading": {
        "location": { "type": "manual" },
        "city_id": 36159,
        "address": "ул. Мира, 5"
      },
      "way_points": []
    },
    "cargo": {
      "name": "Стройматериалы",
      "weight": { "value": 20, "unit": "t" },
      "volume": { "value": 82 },
      "packaging": { "type_id": 1, "quantity": 10 },
      "sizes": {
        "length": 13.6,
        "width": 2.45,
        "height": 2.7
      }
    },
    "truck": {
      "trucks_count": 1,
      "load_type": "ftl",
      "body_types": [1, 2],
      "body_loading": { "type_ids": [1, 2] },
      "body_unloading": { "type_ids": [1] },
      "temperature": { "min": -20, "max": -18 },
      "documents": {
        "tir": false,
        "cmr": false,
        "t1": false,
        "medical_card": false
      },
      "requirements": {
        "logging_truck": false,
        "road_train": false,
        "air_suspension": false
      },
      "adr": 0,
      "belts_count": 0,
      "is_tracking": false,
      "required_capacity": 20
    },
    "payment": {
      "type": "with-bargaining",
      "currency_type": 32,
      "rate_with_vat": 150000,
      "rate_without_vat": 125000,
      "cash": 0,
      "payment_mode": "on-unloading",
      "prepayment": {
        "percent": 0,
        "fuel": false
      }
    },
    "boards": [
      {
        "id": "507f1f77bcf86cd799439011",
        "publication_mode": "now",
        "reservation_enabled": true
      }
    ],
    "contacts": [123456],
    "note": "Примечание к грузу (макс 1000 символов)",
    "documents": []
  }
}
```

### Основные поля cargo_application

#### Route (маршрут)

| Поле | Тип | Описание |
|------|-----|----------|
| route.loading | object | Пункт погрузки |
| route.unloading | object | Пункт выгрузки |
| route.way_points | array | Промежуточные точки (loading/unloading/customs/passthrough) |

Каждый пункт:
- `location.type` -- "manual" или "organization"
- `city_id` -- ID города из справочника
- Координаты: longitude (-180..180), latitude (-90..90)
- `address` -- адрес
- Даты и время загрузки/выгрузки

#### Cargo (груз)

| Поле | Тип | Описание |
|------|-----|----------|
| name | string | Наименование, макс 200 символов |
| weight.value | number | Вес (мин 10 кг, макс 9999 т) |
| weight.unit | string | "t" (тонны) или "kg" (килограммы) |
| volume.value | number | Объем в м3 |
| packaging.type_id | int | ID типа упаковки из словаря |
| packaging.quantity | int | Количество мест |
| sizes | object | Длина, ширина, высота, диаметр |

#### Truck (требования к транспорту)

| Поле | Тип | Описание |
|------|-----|----------|
| trucks_count | int | Количество машин |
| load_type | string | "ftl" (полная загрузка) или "dont-care" |
| body_types | int[] | ID типов кузова из словаря |
| body_loading.type_ids | int[] | Типы погрузки |
| body_unloading.type_ids | int[] | Типы выгрузки |
| temperature | object | min/max для рефрижератора |
| documents.tir | bool | Требуется TIR |
| documents.cmr | bool | Требуется CMR |
| documents.t1 | bool | Требуется T1 |
| documents.medical_card | bool | Мед. книжка |
| adr | int | Класс опасности 0-9 |
| belts_count | int | Количество ремней |
| is_tracking | bool | Отслеживание через АТИ Водитель |
| required_capacity | number | Требуемая грузоподъемность |

#### Payment (оплата)

| Поле | Тип | Описание |
|------|-----|----------|
| type | string | "with-bargaining", "without-bargaining", "rate-request", "auction" |
| currency_type | int | ID валюты из словаря |
| rate_with_vat | number | Ставка с НДС |
| rate_without_vat | number | Ставка без НДС |
| cash | number | Наличные |
| payment_mode | string | "on-unloading" или "delayed-payment" |
| prepayment.percent | number | Процент предоплаты |
| prepayment.fuel | bool | Топливная предоплата |

#### Boards (площадки публикации)

| Поле | Тип | Описание |
|------|-----|----------|
| id | string | ID площадки (24 символа) |
| publication_mode | string | "now", "15m", "30m", "1h", "3h", "6h", "exact-time" |
| publication_time | datetime | Время публикации (для exact-time) |
| reservation_enabled | bool | Разрешено бронирование |

### Response 200

```json
{
  "cargo_application": {
    "cargo_application_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "cargo_application_number": "АВТ-123456",
    "snapshot_id": 1,
    "department_id": 100,
    "persistent_user_id": 42,
    "added_at": "2026-02-17T10:00:00Z",
    "updated_at": "2026-02-17T10:00:00Z",
    "refreshed_at": "2026-02-17T10:00:00Z",
    "origin_source": "api",
    "route": { "...": "полные данные маршрута" },
    "truck": { "...": "параметры транспорта" },
    "payment": { "...": "параметры оплаты" },
    "boards": [
      {
        "id": "507f1f77bcf86cd799439011",
        "status": "published"
      }
    ],
    "documents": [],
    "is_archived": false,
    "archive_date": null
  }
}
```

**cURL:**
```bash
curl 'https://api.ati.su/v2/cargos' \
  -X POST \
  -H 'Authorization: Bearer {token}' \
  -H 'Content-Type: application/json' \
  --data-raw '{
    "cargo_application": {
      "external_id": "ORDER-12345",
      "route": {
        "loading": {"location": {"type": "manual"}},
        "unloading": {"location": {"type": "manual"}}
      },
      "truck": {
        "trucks_count": 1,
        "load_type": "ftl",
        "body_types": [1]
      },
      "payment": {"type": "with-bargaining"},
      "contacts": [123456]
    }
  }'
```

### Обновить груз (PUT /v2/cargos/{guid})

```
PUT /v2/cargos/{cargo_application_id}
```

Лимит: 5000 запросов/24ч на контакт.

### Устаревший эндпоинт

```
POST /v1.0/loads  (deprecated)
```

---

## 6. Сценарий: Добавить груз

### Пошаговый процесс

1. **Получить ID площадки**: `GET /v2/boards/public/boards/canAdd` -- список площадок куда можно добавить
2. **Подготовить данные маршрута**: использовать словари городов для city_id
3. **Подготовить данные груза**: типы из словарей (cargoTypes, packTypes, carTypes)
4. **Настроить оплату**: ставки, валюта, режим оплаты
5. **Указать площадки и режим публикации**
6. **Отправить**: `POST /v2/cargos` с полным объектом cargo_application

### Обязательные поля

- Минимум один контакт (contacts)
- Города погрузки и выгрузки (city_id)
- Вес или объем груза
- ID типа груза
- ID типов кузова
- Тип оплаты и валюта
- Минимум одна площадка

---

## 7. Сценарий: Найти исполнителя

### Метод 1: Получить встречные предложения по конкретному грузу

```
GET /v1.0/loads/new/{loadId}/responses
```

**Параметры запроса:**
- `loadId` -- ID груза (обязательный)
- `dateFrom` -- UTC timestamp для фильтрации (опциональный)

**Response 200:** массив встречных предложений:
```json
[
  {
    "ResponseId": "guid",
    "FirmId": 123456,
    "FirmName": "ООО Перевозки",
    "Price": 50000,
    "CurrencyId": 32,
    "NdsPrice": 60000,
    "NdsCurrencyId": 32,
    "NotNdsPrice": 50000,
    "NotNdsCurrencyId": 32,
    "LoadingDate": "2026-02-20T00:00:00Z",
    "PayAttributes": 3,
    "IsOutdated": false,
    "FirmInfo": {
      "TotalScore": 7.5,
      "StatusType": "green"
    },
    "Contact": {
      "Name": "Иван Иванов",
      "Phone": "+79001234567",
      "Email": "ivan@example.com"
    },
    "CounterOfferSource": "search_page"
  }
]
```

**PayAttributes (побитовые флаги):**
- Наличные
- Безнал
- Экспресс-доставка
- С НДС
- Предоплата
- Оплата по выгрузке

### Метод 2: Все встречные предложения фирмы

```
GET /v1.0/loads/new/responses
```

Параметр `dateFrom` (опционально). Возвращает все ВП по всем грузам фирмы.

### Метод 3: Отправить приглашение по встречному предложению

```
POST /v1.2/orders/invites/counter_offer
```

**Request Body:**
```json
{
  "load_id": "7a48a9d3-55cb-48a2-8527-35ff461eeb8c",
  "response_id": "5026ffdd-4c2a-eb11-bb90-0025906a774d",
  "rate_types": [0],
  "cancel_after_in_minutes": 60,
  "is_auto": false,
  "need_archive_on_invite": false
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| load_id | guid | ID груза (обязательный) |
| response_id | guid | ID встречного предложения (обязательный) |
| rate_types | int[] | 0=наличные, 1=безнал с НДС, 2=безнал без НДС |
| cancel_after_in_minutes | int | Авто-отмена: 1-4320 мин (по умолч. 4320 = 3 дня) |
| is_auto | bool | Автоматическое приглашение |
| need_archive_on_invite | bool | Архивировать груз при принятии |

**Response 200:** `null` (успех)

### Метод 4: Прямое приглашение известного перевозчика

```
POST /v1.2/orders/invites
```

**Request Body:**
```json
{
  "load_id": "7a48a9d3-55cb-48a2-8527-35ff461eeb8c",
  "taker_ati_id": "14612",
  "taker_contacts_list": [0],
  "payment": {
    "price": 10000,
    "currency_id": 32,
    "nds_price": 12000,
    "nds_currency_id": 32,
    "not_nds_price": 10000,
    "not_nds_currency_id": 32
  },
  "is_tracking": false
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| load_id | guid | ID груза |
| taker_ati_id | string | ATI ID перевозчика |
| taker_contacts_list | int[] | ID контактов перевозчика |
| payment.price | number | Ставка наличные |
| payment.currency_id | int | ID валюты |
| payment.nds_price | number | Ставка с НДС |
| payment.not_nds_price | number | Ставка без НДС |
| is_tracking | bool | Отслеживание через АТИ Водитель |

### Метод 5: Выбрать победителя торгов

```
POST /v1.2/auction/bet/win/{auctionRateId}
```

Для ситуаций с равными ставками (state=-5). Только ставки с state 0 или -3 можно выбрать.

### Рабочий процесс

1. Опубликовать груз на площадке
2. Получить встречные предложения (GET responses)
3. Оценить перевозчиков (рейтинг TotalScore, статус, контакты)
4. Выбрать перевозчика -- отправить приглашение (counter_offer или invites)
5. Или провести торги и выбрать победителя
6. Перевозчик принимает -- создается заказ

---

## 8. Торги (Auctions)

**Важно:** Торги создаются через API грузов (payment.type = "auction"), а не напрямую.

### 8.1 Получить все торги (грузовладелец)

```
GET /v1.2/auction
```

**Response 200:** массив объектов торгов

### 8.2 Получить торг по ID

```
GET /v1.2/auction/{auctionId}
```

| Параметр | Тип | Описание |
|----------|-----|----------|
| auctionId | uuid | ID торга |
| withDeleted | bool | Включая удаленные |

Ответ зависит от роли: грузовладелец видит все ставки, перевозчик -- только свои.

### 8.3 Получить несколько торгов по ID

```
POST /v1.2/auction/byids
```

**Request Body:**
```json
["3fa85f64-5717-4562-b3fc-2c963f66afa6"]
```

### 8.4 Отменить торг

```
DELETE /v1.2/auction/{auctionId}
```

| HTTP код | Описание |
|----------|----------|
| 200 | Успешно отменен |
| 403 | Есть активные сделки |
| 404 | Торг не найден |

### 8.5 Досрочное завершение торга

```
POST /v1.2/auction/{auctionId}/finish_aot
```

Ответ: объект торга с `finish_type: 2`.

### 8.6 Сменить победителя

```
POST /v1.2/auction/bet/win/{auctionRateId}
```

Только для ставок с state 0 или -3.

### 8.7 Сделать ставку (перевозчик)

```
POST /v1.2/auction/bet
```

**Request Body:**
```json
{
  "auction_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "rate": 50000.00,
  "payment_type": 24,
  "loading_date": "2026-02-20T08:00:00.000Z"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| auction_id | uuid | ID торга (обязательный) |
| rate | double | Сумма ставки (обязательный) |
| payment_type | enum | 1=наличные, 22=любой, 23=картой, 24=с НДС, 25=без НДС |
| loading_date | datetime | Предпочтительная дата погрузки |

**Response:**
```json
{
  "result_status": 0,
  "auction": { "...": "данные торга" },
  "auction_end_date": "2026-02-20T18:00:00Z"
}
```

| result_status | Значение |
|--------------|----------|
| 0 | Ставка принята |
| 1 | Ставка принята, торг завершен |
| 3 | Ставка не лучшая |
| 5 | Ставка принята, торг продлен |
| 6 | Торг уже завершен |

### 8.8 Отменить ставку

```
POST /v1.2/auction/bet/refuse/{auctionRateId}
```

**Ограничение:** отмена возможна только в течение 30 секунд после размещения.

| Результат | Значение |
|-----------|----------|
| 0 | Ставка удалена |
| 2 | Истек период отмены (30 сек) |
| 4 | Торг завершен |
| 5 | Ставка удалена, есть другие |

### 8.9 Отказаться от победы

```
POST /v1.2/auction/{auctionId}/refuse
```

### Статусы торгов

| State | Описание |
|-------|----------|
| -14 | Вручную отменен владельцем |
| -5 | Завершен неоднозначно (требуется ручной выбор) |
| -2 | Ожидание принятия победителем |
| -1 | Завершен, ставок не было |
| 0 | Активен, нет действительных ставок |
| 1 | Активен, есть действительные ставки |

---

## 9. Работа с заказами (Orders / Deals)

### 9.1 Получить заказ по ID

```
GET /v1.2/orders/{dealId}
```

**Response:** подробный объект заказа:
- Данные груза (копия на момент создания заказа)
- Статус сделки
- Параметры оплаты
- Файлы и документы
- Данные водителя и машины (immutable)
- Маршрутные точки с организациями
- Статус выполнения перевозки

### 9.2 Поиск заказов по фильтру

```
POST /v1.2/orders/search
```

**Request Body:**
```json
{
  "role": 0,
  "statuses": [0, 1, 2],
  "load_ids": ["guid"]
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| role | enum | 0 = грузовладелец, 1 = перевозчик |
| statuses | int[] | Фильтр по статусам |
| load_ids | guid[] | Фильтр по ID грузов |

### Статусы заказов

| Статус | Описание |
|--------|----------|
| 0 | Зарезервирован |
| 1-4 | Различные стадии обработки |
| 5 | Завершен / в архиве |
| <0 | Отклонен / отменен |

### Возможности

- Создание заказов с документами и без
- Изменение водителя, машины, маршрута
- Завершение перевозки
- Изменение условий (ставки, даты)

---

## 10. АТИ Мессенджер

### Управление чатами

#### 10.1 Создать чат

```
POST /messenger/1.1/chats/
```

**Request Body:**
```json
{
  "channel_type": "dialog",
  "name": "Название чата",
  "description": "Описание",
  "id": "account_id.contact_id",
  "ati_id": "ati_code.contact_id",
  "is_open": true,
  "members": ["member_id_1", "member_id_2"]
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| channel_type | string | dialog / channel / group / ati_driver |
| name | string | Название (для groups/channels) |
| description | string | Описание |
| id | string | ID собеседника (формат account_id.contact_id) |
| ati_id | string | ATI код (формат ati_code.contact_id) |
| is_open | bool | Открытый канал |
| members | string[] | ID участников |

**Response 200:** объект подписки с метаданными чата

#### 10.2 Обновить метаданные чата

```
PUT /messenger/1.1/chats/{chat_id}/
```

**Request:** `{"name": "string", "description": "string"}`

#### 10.3 Удалить чат

```
DELETE /messenger/1.1/chats/{chat_id}/
```

**Response 204:** помечает все подписки флагом `removed`.

### Подписки (Subscriptions)

#### 10.4 Список всех подписок

```
GET /messenger/1.2/subscriptions/
```

| Параметр | Тип | Описание |
|----------|-----|----------|
| type | string | channel / dialog / group / groups |
| limit | int | Лимит результатов |
| before | int | Timestamp в микросекундах (пагинация) |
| after | int | Timestamp в микросекундах (пагинация) |

#### 10.5 Получить подписку

```
GET /messenger/1.1/subscriptions/{chat_id}/
```

#### 10.6 Принять приглашение в группу

```
PATCH /messenger/1.1/subscriptions/{chat_id}/
```

Response 204: убирает флаг `invite`.

#### 10.7 Выйти из группы

```
DELETE /messenger/1.1/subscriptions/{chat_id}/
```

#### 10.8 Настройки подписки (pin/hide)

```
POST /messenger/1.1/chats/{chat_id}/settings/
```

**Request:** `{"pin": true, "hidden": false}`

### Участники группы

#### 10.9 Список участников

```
GET /messenger/1.1/chats/{chat_id}/users/
```

| Параметр | Тип | Описание |
|----------|-----|----------|
| start | int | Начало пагинации |
| end | int | Конец пагинации |
| with_invite | bool | Включая приглашенных |
| invited | bool | Только приглашенные |

**Response 200:** массив объектов:
```json
{
  "id": "string",
  "code": "string",
  "name": "string",
  "company": "string",
  "email": "string",
  "phone": "string",
  "mobile": "string",
  "skype": "string",
  "fax": "string",
  "icq": "string"
}
```

#### 10.10 Пригласить одного пользователя

```
POST /messenger/1.1/chats/{chat_id}/users/{user_id}/
```

Параметр `ati_id` -- использовать ATI код вместо account ID.

#### 10.11 Пригласить нескольких пользователей

```
POST /messenger/1.1/chats/{chat_id}/users/
```

**Request:** `{"members": ["id1", "id2"]}`

#### 10.12 Удалить участника

```
DELETE /messenger/1.1/chats/{chat_id}/users/{user_id}/
```

### Сообщения

#### 10.13 Отправить сообщение

```
POST /messenger/1.2/chats/{chat_id}/messages
```

**Content-Type:** `multipart/form-data`

| Параметр | Тип | Описание |
|----------|-----|----------|
| text | string | Текст сообщения |
| file | binary | Прикрепленный файл |
| image | binary | Изображение |
| image_height | int | Высота изображения |
| image_width | int | Ширина изображения |
| geo_latitude | float | Широта (градусы) |
| geo_longitude | float | Долгота (градусы) |
| geo_zoom | int | Масштаб карты |

**Response 200:**
```json
{
  "id": "string",
  "ts": 1234567890,
  "text": "Текст сообщения",
  "user": "user_id",
  "from": "sender_info",
  "delivered": true,
  "file_id": "string",
  "file_name": "document.pdf",
  "file_mimetype": "application/pdf",
  "file_size": 1024,
  "document": "string",
  "document_mimetype": "string",
  "document_size": 0
}
```

#### 10.14 История сообщений

```
GET /messenger/1.1/chats/{chat_id}/history/
```

| Параметр | Тип | Описание |
|----------|-----|----------|
| before | int | Timestamp (пагинация) |
| since | int | Timestamp (пагинация) |
| num | int | Лимит результатов |
| with_ts | bool | Включить timestamp прочтения |

#### 10.15 Получить изображение из сообщения

```
GET /messenger/1.2/messages/{message_id}/image
```

| Параметр | Тип | Описание |
|----------|-----|----------|
| height | int | Желаемая высота |
| width | int | Желаемая ширина |
| biggest_side | int | Макс. сторона |

Response: бинарные данные изображения.

#### 10.16 Получить файл из сообщения

```
GET /messenger/1.2/messages/{message_id}/file
```

Response: бинарные данные файла.

#### 10.17 Удалить сообщение

```
DELETE /messenger/1.1/chats/{chat_id}/messages/{ts_or_id}/
```

#### 10.18 Очистить историю чата

```
DELETE /messenger/1.1/chats/{chat_id}/history/
```

### Счетчики непрочитанных

#### 10.19 Количество непрочитанных чатов

```
GET /messenger/1.1/inbox/
```

**Response:** `{"unread": 5}`

#### 10.20 Непрочитанные по типам

```
GET /messenger/1.1/subscriptions/unread/
```

| Параметр | Описание |
|----------|----------|
| with_messages | Включить кол-во сообщений |

**Response:** `{"all": 10, "dialogs": 5, "groups": 5}`

---

## 11. Фирмы (Firms)

### 11.1 Информация об аккаунте

```
GET /v1.2/account
```

Возвращает: логин, email админа, тип фирмы, платные сервисы, контакты, локация, scoring паспорта.

### 11.2 Текущий контакт фирмы

```
GET /v1.0/firms/contact
```

Возвращает: ID контакта, имя, телефон, email, настройки видимости.

### 11.3 Все контакты фирмы

```
GET /v1.0/firms/contacts
```

### 11.4 Краткая информация о контакте другой фирмы

```
GET /v1.0/firms/{atiId}/contacts/{contactId}/summary
```

Возвращает: имя, телефон, количество претензий, рекомендации, данные фирмы.

### 11.5 Все контакты другой фирмы (краткие)

```
GET /v1.0/firms/{atiId}/contacts/summary
```

### 11.6 Email контакта

```
GET /v1.0/firms/contact/{atiId}/{contactId}/email
```

### 11.7 Изменить контакт

```
PUT /v1.0/firms/contacts
```

### 11.8 Реквизиты фирмы по ID

```
GET /v1.0/firms/requisites/{requisiteId}
```

Возвращает: юр. название, ИНН, ОГРН, банковские реквизиты, адреса, подписанты.

### 11.9 Все реквизиты фирмы

```
GET /v1.0/firms/requisites
```

### 11.10 Реквизиты другой фирмы

```
GET /v1.0/firms/{atiId}/requisites
```

### 11.11 Краткая информация о фирме

```
GET /v1.0/firms/summary
```

Возвращает: название, тип, город, рейтинг (score), статус.

### 11.12 Краткая информация о другой фирме

```
GET /v1.0/firms/{atiId}/summary
```

### 11.13 Пакетная информация о фирмах

```
GET /v1.0/firms/summary/batch
```

**Request:** массив ID фирм. Response: массив кратких данных.

### Общие поля ответа

| Поле | Тип | Описание |
|------|-----|----------|
| ati_id | string | Идентификатор фирмы |
| firm_name | string | Название компании |
| ownership | string | Организационная форма |
| inn | string | ИНН |
| ogrn | string | ОГРН |
| city_id | int | ID города |
| score | float | Рейтинг (0-8 звезд) |
| status | enum | Статус паспорта |

### HTTP статусы

| Код | Описание |
|-----|----------|
| 200 | Успех |
| 400 | Некорректный запрос |
| 401 | Не авторизован |
| 402 | Недостаточная лицензия |
| 403 | Запрещено |
| 404 | Не найдено |
| 500 / 504 | Ошибка сервера |

---

## 12. Словари: Грузы

Все словари используют `GET`, авторизация через Bearer token.

### 12.1 Типы кузова

```
GET /v1.0/dictionaries/carTypes
```

| Поле | Тип | Описание |
|------|-----|----------|
| Id | int64 | Числовой ID |
| Id2 | GUID | Строковый ID |
| Name | string | Название (рус) |
| NameEng | string | Название (англ) |
| ShortName | string | Краткое название |
| ShortNameEng | string | Краткое (англ) |
| Attribs | int32 | Атрибуты |
| Position | int32 | Позиция сортировки |
| TypeId | int32 | Тип |

### 12.2 Типы грузов (наименования)

```
GET /v1.0/dictionaries/cargoTypes
```

| Поле | Тип | Описание |
|------|-----|----------|
| Id | int64 | ID |
| Id2 | GUID | GUID |
| Name | string | Название (рус) |
| NameEng | string | Название (англ) |

### 12.3 Валюты

```
GET /v1.0/dictionaries/currencyTypes
```

| Поле | Тип | Описание |
|------|-----|----------|
| Id | int64 | ID |
| Id2 | GUID | GUID |
| Name | string | Название |
| NameEng | string | Название (англ) |
| Modifier | int32 | Множитель (напр. 1000 для "тысяч") |
| CurrencyIdPerKm | int32 | Вариант за км |
| Iso4217Code | string | ISO код ("RUB", "USD") |
| Iso4217DigitalCode | int32 | Цифровой ISO код |

### 12.4 Типы документов для грузов

```
GET /v1.0/dictionaries/documenttypes
```

Response: массив строк.

### 12.5 Типы оплаты

```
GET /v1.0/dictionaries/moneyTypes
```

| Поле | Тип | Описание |
|------|-----|----------|
| Id | int64 | ID |
| Id2 | GUID | GUID |
| Name | string | Название |
| NameEng | string | Название (англ) |

### 12.6 Типы упаковки

```
GET /v1.0/dictionaries/packTypes
```

| Поле | Тип | Описание |
|------|-----|----------|
| Id | int64 | ID |
| Id2 | GUID | GUID |
| Name | string | Название |
| NameEng | string | Название (англ) |
| ShortName | string | Краткое название |

### 12.7 Типы погрузки

```
GET /v1.0/dictionaries/loadingTypes
```

| Поле | Тип | Описание |
|------|-----|----------|
| Id | int64 | ID |
| Id2 | GUID | GUID |
| Name | string | Название |
| NameEng | string | Название (англ) |
| ShortName | string | Краткое название |
| ShortNameEng | string | Краткое (англ) |

### 12.8 Типы выгрузки

```
GET /v1.0/dictionaries/unloadingTypes
```

Формат ответа аналогичен loadingTypes.

### 12.9 Причины отказа в доступе к грузу

```
GET /v1.0/dictionaries/load_access_denied_reasons
```

Response: словарь key-value (string -> string).

---

## 13. Словари: Гео объекты

Базовый URL для гео: `https://api.ati.su/gw/gis-dict/v1/`

### 13.1 Города по ATI ID

```
POST /gw/gis-dict/v1/cities/by-ids
```

**Request:** `{"ids": [36942, 36159]}` (1-1000 элементов)

**Response:** массив городов:
```json
[
  {
    "city_id": 36942,
    "name": "Москва",
    "country_id": 1,
    "region_id": 77,
    "geo_point": {
      "lat": 55.7558,
      "lon": 37.6173
    },
    "fias_id": "0c5b2444-70a0-4932-980c-b4dc0d3f02b5",
    "kladr": "7700000000000"
  }
]
```

### 13.2 Город по координатам

```
POST /gw/gis-dict/v1/cities/by-coordinate
```

**Request:** `{"location": {"lat": 55.7558, "lon": 37.6173}}`

### 13.3 Города по FIAS ID

```
POST /gw/gis-dict/v1/cities/by-fias-ids
```

**Request:** `{"fias_ids": ["uuid1", "uuid2"]}` (1-1000)

### 13.4 Города по КЛАДР кодам

```
POST /gw/gis-dict/v1/cities/by-kladr-codes
```

**Request:** `{"kladr_codes": ["7700000000000"]}` (1-1000)

### 13.5 Типы населенных пунктов

```
GET /gw/gis-dict/v1/city-types
```

**Response:**
```json
[
  {
    "city_type_id": 1,
    "name": "город",
    "short_name": "г."
  }
]
```

### 13.6 Районы по ID

```
POST /gw/gis-dict/v1/districts/by-ids
```

**Request:** `{"ids": [1, 2, 3]}` (1-1000)

**Response:**
```json
[
  {
    "district_id": 1,
    "name": "Название района",
    "region_id": 77
  }
]
```

### 13.7 Федеральные округа

```
GET /gw/gis-dict/v1/federal-districts
```

**Response:**
```json
[
  {
    "federal_district_id": 1,
    "name": "Центральный",
    "country_id": 1
  }
]
```

### 13.8 Регионы по ID

```
POST /gw/gis-dict/v1/regions/by-ids
```

**Request:** `{"ids": [77, 50]}`

**Response:**
```json
[
  {
    "region_id": 77,
    "name": "Москва",
    "fias_id": "uuid",
    "clarified_name": "г. Москва"
  }
]
```

### 13.9 Регион по координатам

```
POST /gw/gis-dict/v1/regions/by-coordinate
```

**Request:** `{"location": {"lat": 55.7558, "lon": 37.6173}}`

### 13.10 Регионы по FIAS ID

```
POST /gw/gis-dict/v1/regions/by-fias-ids
```

**Request:** `{"fias_ids": ["uuid1"]}` (1-1000)

### Дублирующие эндпоинты для OAuth2

Все вышеперечисленные эндпоинты доступны также по пути `/gw/oauth2/...` для авторизации через OAuth 2.0.

---

## 14. Вебхуки (Webhooks)

### Требования к webhook-эндпоинту

- URL не должен быть угадываемым
- Обязательно HTTPS с публичным IPv4
- Поддержка HMAC-SHA-256 аутентификации
- Ответ в течение 20 секунд
- Уникальный URL для каждой подписки

### 14.1 Создать webhook

```
POST /webhooks/v1/create
```

(для OAuth v2: `POST /gw/oauth2/webhooks/v1/create`)

**Request Body:**
```json
{
  "topic": "cargoes",
  "callback": "https://example.com/webhook/ati",
  "subscription_type": "normal",
  "subscription": {
    "channel": "cargoes.on_boards",
    "boards": ["507f1f77bcf86cd799439011"]
  }
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| topic | string | Тема подписки |
| callback | string | HTTPS URL для доставки |
| subscription_type | string | "normal" или "complex" |
| subscription.channel | string | Канал (для complex) |
| subscription.boards | string[] | ID площадок (для complex) |

**Response 202 Accepted:** заголовок `Location` с URL для проверки статуса.

### 14.2 Статус webhook (один)

```
GET /webhooks/v1/status/{id}
```

**Статусы:**
- `created` -- создан
- `verification` -- идет верификация
- `active` -- активен
- `removed` -- удален
- `deactivated` -- деактивирован

### 14.3 Статус webhook (несколько)

```
GET /webhooks/v1/status?statuses=active,deactivated
```

### 14.4 Получить фильтры подписки

```
GET /webhooks/v1/subscriptions/{id}
```

### 14.5 Обновить фильтры подписки

```
PUT /webhooks/v1/subscriptions/{id}
```

**Request:**
```json
{
  "channel": "cargoes.on_boards",
  "boards": ["board_id_1", "board_id_2"]
}
```

### 14.6 Удалить webhook

```
DELETE /webhooks/v1/delete/{id}
```

**Response 202 Accepted.**

### 14.7 Неудачные доставки

```
GET /webhooks/v1/distributions/failed/{id}?since=2026-02-01T00:00:00Z
```

**Response:** массив объектов с `entity_id`, `action_date`, `status`.

### Процесс верификации

1. ATI.SU отправляет GET на callback с параметрами `challenge` и `verification_status=progress`
2. Webhook должен ответить в течение 20 секунд JSON-строкой: `"challenge-value"`
3. При успехе статус меняется на `active`
4. При неудаче -- детали ошибки (TLS, socket, несовпадение challenge)

### Формат доставки сообщений

ATI.SU отправляет POST на callback:

```json
{
  "topic": "cargoes",
  "entities": [
    {
      "entity_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "action_date": "2026-02-17T10:00:00Z",
      "entity": { "...": "данные объекта" }
    }
  ],
  "is_retry": false
}
```

**Заголовки:**
- `Authorization` -- HMAC-SHA-256 подпись
- `ATI-Is-Retry` -- true для повторных доставок
- `Digest` -- SHA-256 хеш тела

**Ожидаемый ответ:** HTTP 2xx в течение 20 секунд.

### Повторные попытки и деактивация

- Неудачные доставки повторяются до успеха
- HTTP `429` с `Retry-After` -- пауза (макс 1 день)
- HTTP `410 Gone` -- webhook удаляется навсегда
- После 4 дней неудач webhook деактивируется
- Повторные доставки маркируются `ATI-Is-Retry: true`

### Доступные темы подписки

| Тема | Описание |
|------|----------|
| `cargoes` | Грузы |
| `cargoes.on_boards` | Грузы на площадках |
| `orders` | Заказы |
| `orders-invites` | Персональные приглашения |
| `auctions` | Торги |
| `auctions.on_boards` | Торги на площадках |
| `autopark` | Автопарк |
| `drivers` | Водители |

---

## 15. Вебхуки: Тема "Грузы"

### Тема: `cargoes`

При событиях с грузами ATI.SU отправляет POST с данными груза.

### Структура payload

```json
{
  "topic": "cargoes",
  "entities": [
    {
      "entity_id": "cargo_application_id",
      "action_date": "2026-02-17T10:00:00Z",
      "entity": {
        "cargo_application_id": "uuid",
        "cargo_application_number": "string",
        "snapshot_id": 1,
        "department_id": 100,
        "persistent_user_id": 42,
        "added_at": "datetime",
        "updated_at": "datetime",
        "refreshed_at": "datetime",
        "route": {
          "loading": { "...": "город, координаты, адрес" },
          "unloading": { "...": "город, координаты, адрес" },
          "way_points": [],
          "round_trip": false
        },
        "cargo": {
          "weight": {},
          "volume": {},
          "dimensions": {},
          "packaging": {}
        },
        "truck": {
          "trucks_count": 1,
          "load_type": "ftl",
          "body_types": [],
          "capacity": 0,
          "temperature": {},
          "documents": {}
        },
        "payment": {
          "type": "with-bargaining",
          "currency_type": 32,
          "rate_with_vat": 0,
          "rate_without_vat": 0,
          "cash": 0,
          "prepayment": {}
        },
        "boards": [
          {
            "id": "board_id",
            "status": "published"
          }
        ]
      }
    }
  ]
}
```

### Удаление груза

При удалении груза поле `entity` возвращается как `null`:

```json
{
  "topic": "cargoes",
  "entities": [
    {
      "entity_id": "cargo_application_id",
      "action_date": "2026-02-17T12:00:00Z",
      "entity": null
    }
  ]
}
```

### Основные секции payload

| Секция | Содержимое |
|--------|-----------|
| Идентификаторы | cargo_application_id, number, snapshot_id |
| Метаданные | department_id, persistent_user_id, timestamps |
| Маршрут | Погрузка, выгрузка, промежуточные точки, круговой маршрут |
| Груз | Вес, объем, габариты, упаковка |
| Транспорт | Кол-во машин, тип загрузки, кузова, температура, документы |
| Оплата | Тип, валюта, ставки (с/без НДС, нал), предоплата |
| Площадки | ID площадки, статус публикации |

---

## Приложения

### A. Базовые URL

| Сервис | URL |
|--------|-----|
| API основной | `https://api.ati.su` |
| Гео словари | `https://api.ati.su/gw/gis-dict/v1/` |
| Мессенджер | `https://api.ati.su/messenger/` |
| Вебхуки | `https://api.ati.su/webhooks/v1/` |
| Вебхуки OAuth2 | `https://api.ati.su/gw/oauth2/webhooks/v1/` |

### B. Типы авторизации по эндпоинтам

| Путь | Авторизация |
|------|------------|
| `/v1.0/*`, `/v1.2/*`, `/v2/*` | Bearer token |
| `/gw/gis-dict/*` | Bearer token |
| `/messenger/*` | Bearer token |
| `/webhooks/*` | Bearer token |
| `/gw/oauth2/*` | OAuth 2.0 |

### C. Полезные ссылки

- Документация: https://ati.su/developers/
- Мои токены: https://ati.su/developers/tokens/
- Чат для вопросов: https://chat.ati.su/ln/nqcx9p3xw6s
- Email: api@ati.su
- Тикеты: https://ati.su/tickets/create/24
- Telegram: https://t.me/apiatisu
