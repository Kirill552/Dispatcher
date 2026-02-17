#!/usr/bin/env bash
# Подготовка Docker-данных на сервере
# Запускать из директории репозитория: cd ~/Dispatcher && bash docker-setup.sh
set -euo pipefail

echo "=== 1. Создание docker-data/ ==="
mkdir -p docker-data

# Копия openclaw.json с реальным gateway token
if [ ! -f docker-data/openclaw.json ]; then
    cp openclaw.json docker-data/openclaw.json
    TOKEN=$(openssl rand -hex 32)
    sed -i "s/GENERATE_WITH_openssl_rand_-hex_32/$TOKEN/" docker-data/openclaw.json
    echo "Gateway token: ${TOKEN:0:8}..."
else
    echo "openclaw.json уже существует, пропускаю"
fi

# models.json
cat > docker-data/models.json << 'EOF'
{
  "openrouter/minimax/minimax-m2.5": {
    "provider": "openrouter",
    "model": "minimax/minimax-m2.5"
  }
}
EOF

# OpenClaw бинарник (node:22-slim не имеет git, npx не работает)
echo "=== 2. Установка OpenClaw в docker-data/openclaw-bin ==="
mkdir -p docker-data/openclaw-bin
cd docker-data/openclaw-bin
if [ ! -f node_modules/openclaw/dist/index.js ]; then
    npm init -y > /dev/null 2>&1
    npm install openclaw@latest
    echo "OpenClaw $(node -e "console.log(require('./node_modules/openclaw/package.json').version)") установлен"
else
    echo "OpenClaw уже установлен, пропускаю"
fi
cd ../..

# npm зависимости для расширений
echo "=== 3. npm install для расширений ==="
cd docker-data
ln -sf ../package.json package.json 2>/dev/null || true
npm install --omit=dev
cd ..

# npm зависимости для сайта (tsx нужен для запуска — ставим все)
echo "=== 4. npm install для сайта ==="
cd site && npm install && cd ..

echo "=== 5. .env файл ==="
if [ ! -f .env ]; then
    cat > .env << 'EOF'
TELEGRAM_BOT_TOKEN=ЗАМЕНИТЬ
OPENROUTER_API_KEY=ЗАМЕНИТЬ
ATI_API_TOKEN=ЗАМЕНИТЬ
EOF
    echo "⚠️  Заполни .env реальными секретами!"
else
    echo ".env уже существует"
fi

echo ""
echo "=== Готово! ==="
echo "1. Заполни .env секретами: nano .env"
echo "2. Запусти: docker compose up -d"
echo "3. Проверь: docker compose logs -f"
