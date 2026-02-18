#!/usr/bin/env bash
# E2E-тест telegram_notify:
# 1) вызывает tool через OpenClaw /tools/invoke
# 2) проверяет, что Telegram API вернул успешную отправку
# 3) (если доступен docker compose) проверяет запись в логах OpenClaw

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Использование: $0 <gateway_url> <gateway_token> [session_key] [owner_chat_id]"
  echo "Пример: $0 http://127.0.0.1:18790 <TOKEN> agent:main:telegram:direct:90000030101 408001372"
  exit 2
fi

GATEWAY_URL="$1"
GATEWAY_TOKEN="$2"
SESSION_KEY="${3:-agent:main:telegram:direct:90000030101}"
OWNER_CHAT_ID="${4:-408001372}"

GATEWAY_TOKEN="${GATEWAY_TOKEN//$'\r'/}"

OUT_DIR="reference/tests/out"
mkdir -p "${OUT_DIR}"
OUT_FILE="${OUT_DIR}/telegram_notify_$(date +%Y%m%d_%H%M%S).log"

CORR_ID="tg_notify_$(date +%Y%m%d_%H%M%S)_$RANDOM"
TEST_TEXT="Проверка telegram_notify e2e"

echo "Лог telegram-notify e2e: ${OUT_FILE}"
echo "corr_id=${CORR_ID}" | tee -a "${OUT_FILE}"

payload="$(jq -n \
  --arg session_key "${SESSION_KEY}" \
  --arg text "${TEST_TEXT}" \
  --arg corr "${CORR_ID}" \
  '{
    tool: "telegram_notify",
    sessionKey: $session_key,
    args: {
      text: $text,
      severity: "test",
      correlation_id: $corr,
      user_id: "90000030101",
      route: "Москва → Казань"
    }
  }')"

tmp_file="$(mktemp)"
code="$(curl -sS -o "${tmp_file}" -w "%{http_code}" \
  -X POST "${GATEWAY_URL}/tools/invoke" \
  -H "Authorization: Bearer ${GATEWAY_TOKEN}" \
  -H "Content-Type: application/json" \
  --data "${payload}")"
body="$(cat "${tmp_file}")"
rm -f "${tmp_file}"

{
  echo "HTTP: ${code}"
  echo "BODY: ${body}"
} >>"${OUT_FILE}"

if [[ "${code}" -ge 400 ]]; then
  echo "FAIL: tools/invoke вернул HTTP ${code}"
  echo "Body: ${body}"
  exit 1
fi

tool_text="$(jq -r '.result.content[0].text // "{}"' <<<"${body}")"
sent="$(jq -r '.sent // "false"' <<<"${tool_text}")"
chat_id="$(jq -r '.chat_id // ""' <<<"${tool_text}")"
msg_id="$(jq -r '.message_id // ""' <<<"${tool_text}")"

if [[ "${sent}" != "true" ]]; then
  echo "FAIL: telegram_notify не подтвердил отправку."
  echo "Ответ инструмента: ${tool_text}"
  exit 1
fi

if [[ "${chat_id}" != "${OWNER_CHAT_ID}" ]]; then
  echo "FAIL: уведомление отправлено не в тот chat_id."
  echo "Ожидалось: ${OWNER_CHAT_ID}, факт: ${chat_id}"
  exit 1
fi

echo "OK: tool telegram_notify отправил сообщение chat_id=${chat_id}, message_id=${msg_id}"

if [[ -f "docker-compose.yml" ]]; then
  if docker compose logs openclaw --since 3m 2>/dev/null | grep -F "telegram_notify: sent" | grep -F "${CORR_ID}" >/dev/null; then
    echo "OK: запись telegram_notify найдена в логах OpenClaw."
  else
    echo "WARN: в логах OpenClaw не найден corr_id=${CORR_ID} (проверьте вручную)."
  fi
fi

echo "Проверьте входящее сообщение в Telegram у владельца (chat_id ${OWNER_CHAT_ID}), corr_id=${CORR_ID}"
