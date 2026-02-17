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

# OpenClaw форк с RBAC-патчами ядра (блокировка /status и др. для не-админов)
echo "=== 2. Установка OpenClaw (форк с RBAC) ==="
if [ ! -d docker-data/openclaw-fork/.git ]; then
    git clone https://github.com/Kirill552/openclaw.git docker-data/openclaw-fork
    cd docker-data/openclaw-fork
    pnpm install && npm run build
    echo "OpenClaw fork собран: $(node -e "console.log(require('./package.json').version)")"
    cd ../..
else
    echo "OpenClaw fork уже склонирован, пропускаю"
    echo "Для обновления: cd docker-data/openclaw-fork && git pull && pnpm install && npm run build"
fi

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
echo ""
echo "=== Обновление форка ==="
echo "cd docker-data/openclaw-fork && git pull && pnpm install && npm run build"
echo "cd ../.. && docker compose up -d --force-recreate"
