#!/usr/bin/env bash
# Безопасный запуск диалогового e2e-теста с временным включением ATI mock mode.
# Важно: скрипт запускается на сервере в корне проекта (где есть docker-compose.yml).

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Использование: $0 <gateway_url> <gateway_token> [client_session_key] [carrier_session_key]"
  echo "Пример: $0 http://127.0.0.1:18790 <TOKEN> agent:main:telegram:direct:90000002101 agent:main:telegram:direct:90000002102"
  exit 2
fi

GATEWAY_URL="$1"
GATEWAY_TOKEN="$2"
CLIENT_SESSION_KEY="${3:-agent:main:telegram:direct:90000002101}"
CARRIER_SESSION_KEY="${4:-agent:main:telegram:direct:90000002102}"

if [[ ! -f "docker-data/openclaw.json" || ! -f "docker-compose.yml" ]]; then
  echo "FAIL: запустите скрипт из корня проекта (ожидались docker-data/openclaw.json и docker-compose.yml)."
  exit 2
fi

backup_file="$(mktemp /tmp/openclaw_json_backup_XXXXXX.json)"
cp docker-data/openclaw.json "${backup_file}"

restore_config() {
  cp "${backup_file}" docker-data/openclaw.json
  docker compose restart openclaw >/dev/null 2>&1 || true
  rm -f "${backup_file}"
}
trap restore_config EXIT

wait_gateway_ready() {
  local max_attempts=60
  local attempt=1
  local body_file http_code
  body_file="$(mktemp /tmp/mock_status_resp_XXXXXX.json)"

  while [[ "${attempt}" -le "${max_attempts}" ]]; do
    http_code="$(curl -sS -o "${body_file}" -w "%{http_code}" \
      -X POST "${GATEWAY_URL}/tools/invoke" \
      -H "Authorization: Bearer ${GATEWAY_TOKEN}" \
      -H "Content-Type: application/json" \
      --data '{"tool":"ati_mock_status","sessionKey":"test:gateway:health","args":{}}' \
      2>/dev/null || true)"

    if [[ "${http_code}" == "200" ]]; then
      rm -f "${body_file}"
      return 0
    fi

    sleep 2
    attempt=$((attempt + 1))
  done

  echo "FAIL: gateway не стал готов к тесту (ati_mock_status)."
  echo "Последний ответ:"
  cat "${body_file}" || true
  rm -f "${body_file}"
  return 1
}

tmp_file="$(mktemp /tmp/openclaw_json_mock_XXXXXX.json)"
jq '.plugins.entries["ati-cargo"].config.mockMode = true' docker-data/openclaw.json > "${tmp_file}"
mv "${tmp_file}" docker-data/openclaw.json

echo "ATI mock mode: ON (временно для теста)"
docker compose restart openclaw >/dev/null
wait_gateway_ready

bash reference/tests/dialog_flow_chat_e2e.sh \
  "${GATEWAY_URL}" \
  "${GATEWAY_TOKEN}" \
  "${CLIENT_SESSION_KEY}" \
  "${CARRIER_SESSION_KEY}"

echo "ATI mock mode: будет восстановлен автоматически."
