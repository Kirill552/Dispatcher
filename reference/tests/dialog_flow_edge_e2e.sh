#!/usr/bin/env bash
# Edge/E2E диалоговый тест через OpenClaw Chat Completions.
# Цель: проверить нестандартные сообщения и утечки служебных артефактов.

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Использование: $0 <gateway_url> <gateway_token> [client_session_key] [carrier_session_key]"
  echo "Пример: $0 http://127.0.0.1:18790 <TOKEN> agent:main:telegram:direct:90000010101 agent:main:telegram:direct:90000010102"
  exit 2
fi

GATEWAY_URL="$1"
GATEWAY_TOKEN="$2"
CLIENT_SESSION_KEY="${3:-agent:main:telegram:direct:90000010101}"
CARRIER_SESSION_KEY="${4:-agent:main:telegram:direct:90000010102}"

GATEWAY_TOKEN="${GATEWAY_TOKEN//$'\r'/}"

OUT_DIR="reference/tests/out"
mkdir -p "${OUT_DIR}"
OUT_FILE="${OUT_DIR}/dialog_flow_edge_$(date +%Y%m%d_%H%M%S).log"

ensure_mock_mode_or_explicit_real() {
  if [[ "${ATI_TEST_ALLOW_REAL:-0}" == "1" ]]; then
    echo "WARN: ATI_TEST_ALLOW_REAL=1 — разрешён реальный ATI API."
    return
  fi

  local payload tmp_file code body text_json mock_mode
  payload="$(jq -n --arg session_key "${CLIENT_SESSION_KEY}" '{
    tool: "ati_mock_status",
    sessionKey: $session_key,
    args: {}
  }')"

  tmp_file="$(mktemp)"
  code="$(curl -sS -o "${tmp_file}" -w "%{http_code}" \
    -X POST "${GATEWAY_URL}/tools/invoke" \
    -H "Authorization: Bearer ${GATEWAY_TOKEN}" \
    -H "Content-Type: application/json" \
    --data "${payload}")"
  body="$(cat "${tmp_file}")"
  rm -f "${tmp_file}"

  if [[ "${code}" -ge 400 ]]; then
    echo "FAIL: не удалось проверить ati_mock_status (HTTP ${code})."
    echo "Body: ${body}"
    exit 3
  fi

  text_json="$(jq -r '.result.content[0].text // "{}"' <<<"${body}")"
  mock_mode="$(jq -r '.mock_mode // "false"' <<<"${text_json}")"
  if [[ "${mock_mode}" != "true" ]]; then
    echo "FAIL: ATI mock mode выключен. Чтобы тесты не публиковали реальные грузы, включите mockMode=true."
    echo "Если осознанно нужен реальный ATI API, запустите с ATI_TEST_ALLOW_REAL=1."
    exit 3
  fi

  echo "OK: ATI mock mode включён"
}

extract_chat_text() {
  local body="$1"
  jq -r '
    if (.choices | type) == "array" and (.choices[0].message | type) == "object" then
      if (.choices[0].message.content | type) == "string" then
        .choices[0].message.content
      else
        [ .choices[0].message.content[]? | .text // .content // "" ] | join("")
      end
    elif (.output_text | type) == "string" then
      .output_text
    else
      ""
    end
  ' <<<"${body}"
}

chat_turn() {
  local session_key="$1"
  local user_text="$2"
  local tmp_file payload code body answer

  payload="$(jq -n --arg msg "${user_text}" '{
    model: "openclaw",
    stream: false,
    messages: [{ role: "user", content: $msg }]
  }')"

  tmp_file="$(mktemp)"
  code="$(curl -sS -o "${tmp_file}" -w "%{http_code}" \
    -X POST "${GATEWAY_URL}/v1/chat/completions" \
    -H "Authorization: Bearer ${GATEWAY_TOKEN}" \
    -H "Content-Type: application/json" \
    -H "x-openclaw-session-key: ${session_key}" \
    --data "${payload}")"

  body="$(cat "${tmp_file}")"
  rm -f "${tmp_file}"

  if [[ "${code}" -ge 400 ]]; then
    echo "HTTP_${code}: ${body}"
    return 1
  fi

  answer="$(extract_chat_text "${body}")"
  echo "${answer}"
}

run_dialog() {
  local role="$1"
  local session_key="$2"
  shift 2
  local bad_count=0
  local empty_count=0

  local -a banned_patterns=(
    "Error 400"
    "400 Provider returned error"
    "Unable to submit request because Thought signature is not valid"
    "[System Message]"
    "[Action needed]"
    "\"error_code\""
    "tool_call"
    "Exec:"
    "Role \"guest\" does not have access to tool"
    "попробую через браузер"
    "попробую другой подход"
    "возникла техническая проблема с размещением"
  )

  {
    echo "=== Edge сценарий: ${role} ==="
  } >>"${OUT_FILE}"

  for user_text in "$@"; do
    local answer
    answer="$(chat_turn "${session_key}" "${user_text}")" || {
      echo "FAIL: ошибка вызова chat endpoint для '${role}'"
      exit 1
    }

    {
      echo
      echo "USER: ${user_text}"
      echo "BOT:  ${answer}"
    } >>"${OUT_FILE}"

    if [[ -z "${answer//[[:space:]]/}" ]]; then
      echo "WARN: ${role} -> пустой ответ" >&2
      empty_count=$((empty_count + 1))
    fi

    for pattern in "${banned_patterns[@]}"; do
      if grep -Fqi "${pattern}" <<<"${answer}"; then
        echo "WARN: ${role} -> найден артефакт '${pattern}'" >&2
        bad_count=$((bad_count + 1))
      fi
    done
  done

  echo "${bad_count}:${empty_count}"
}

echo "Лог edge-диалогов: ${OUT_FILE}"
ensure_mock_mode_or_explicit_real

client_result="$(
  run_dialog "клиент" "${CLIENT_SESSION_KEY}" \
    "ээээ, ало" \
    "/help" \
    "я хз че писать, нужно перевезти что-то" \
    "бюджет 5000 и только так" \
    "да ты че, делай быстро" \
    "сука вы все мошенники" \
    "ладно: москва казань диван, 300 кг, 3 куба, загрузка завтра, адрес каширское 120, оплата без торга, ставка без ндс 25000"
)"
client_bad="${client_result%%:*}"
client_empty="${client_result##*:}"

carrier_result="$(
  run_dialog "перевозчик" "${CARRIER_SESSION_KEY}" \
    "йо, я перевозчик, есть тачка" \
    "ati id не скажу, но груз дайте" \
    "ладно, ati id 777.0, тент, ставка 25000, погрузка завтра"
)"
carrier_bad="${carrier_result%%:*}"
carrier_empty="${carrier_result##*:}"

echo "Итог edge: артефакты клиент=${client_bad}, перевозчик=${carrier_bad}; пустые клиент=${client_empty}, перевозчик=${carrier_empty}"
echo "Проверьте лог: ${OUT_FILE}"

if [[ "${client_bad}" -gt 0 || "${carrier_bad}" -gt 0 || "${client_empty}" -gt 0 || "${carrier_empty}" -gt 0 ]]; then
  echo "FAIL: найдены артефакты/пустые ответы в edge-сценариях."
  exit 1
fi

echo "OK: edge-сценарии прошли без критичных артефактов."
