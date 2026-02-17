# OpenClaw — конвенции проекта

## Версия и установка

- OpenClaw v2026.2.14+ (ранее Moltbot → ClawdBot → OpenClaw, январь 2026)
- GitHub: github.com/openclaw/openclaw (147K+ звёзд)
- Установка: `npm install -g openclaw@latest` → `openclaw onboard --install-daemon`
- Конфиг: `~/.openclaw/openclaw.json` (JSON5 — комментарии и trailing commas разрешены)
- Валидация строгая: неизвестные ключи = gateway не стартует. Лечить: `openclaw doctor --fix`

## Структура проекта на сервере

```
~/.openclaw/
├── openclaw.json              # Наш openclaw.json
├── workspace/
│   ├── SOUL.md                # Персона бота
│   ├── AGENTS.md              # Правила поведения
│   ├── TOOLS.md               # Окружение (ID, параметры)
│   └── MEMORY.md              # Долгосрочная память (бот пишет сам)
├── agents/
│   └── skills/
│       ├── dispatcher-client/SKILL.md
│       └── dispatcher-admin/SKILL.md
└── extensions/
    └── ati-cargo/
        ├── openclaw.plugin.json
        ├── index.ts
        └── src/dictionaries.ts
```

## Workspace файлы — что куда

| Файл | Загружается | Содержимое |
|------|------------|-----------|
| SOUL.md | Всегда | Персона — тон, стиль, запреты |
| AGENTS.md | Всегда | Правила безопасности, эскалация, ограничения |
| TOOLS.md | Всегда | Окружение: ATI board ID, owner ID, бизнес-параметры |
| MEMORY.md | Только в DM | Долгосрочная память — бот накапливает сам |

## Скиллы (SKILL.md)

- Скилл = workflow (КАК делать), данные = MEMORY.md
- Description — КОГДА триггерить, НЕ что делает. Начинай с "Use when..."
- Trigger-фразы на русском языке в кавычках
- "NOT for..." для смежных скиллов
- Обязательные секции: шаги, память, примеры (few-shot)
- Макс 5000 слов в body, макс ~500 символов description

## Расширения (Extensions)

- Каждое расширение: `extensions/<id>/` с `openclaw.plugin.json` + `index.ts`
- `id` в manifest = `id` в index.ts = имя папки
- Параметры инструментов: `@sinclair/typebox` Type.Object
- `execute()` возвращает: `{ content: [{ type: "text", text: "..." }] }`
- Конфиг через `api.pluginConfig` (из openclaw.json plugins.entries.<id>.config)
- OpenClaw загружает TS через jiti (без сборки)

## Модель

- Primary: `openrouter/minimax/minimax-m2.5` — бюджетная, достаточна для диспетчера
- Embedding: `text-embedding-3-small` — для memory-lancedb
- Ключ: `OPENROUTER_API_KEY` (env-переменная, НЕ в коде)

## Каналы

- Telegram: `dmPolicy: "open"`, `streamMode: "block"`
- Сессии: `per-channel-peer` (каждый пользователь — отдельная сессия)

## Безопасность

- `exec.security: "deny"` — запрет выполнения команд
- `clawhub: { enabled: false }` — ClawHub отключён
- Gateway: `bind: "loopback"`, auth token обязателен
- Форк НЕ нужен для нашего MVP
