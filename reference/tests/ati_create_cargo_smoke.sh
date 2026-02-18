#!/usr/bin/env bash
# Smoke-тесты инструмента ati_create_cargo через OpenClaw /tools/invoke
# Проверяет критичные сценарии без моков:
# 1) Адрес обязателен для Москва/СПб
# 2) Дата дальше 60 дней блокируется
# 3) Вес < 200 кг блокируется
# 4) Корректные данные создают груз и нормализуют дату

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Использование: $0 <gateway_url> <gateway_token> [session_key]"
  echo "Пример: $0 http://127.0.0.1:18790 <TOKEN> agent:main:telegram:direct:90000000999"
  exit 2
fi

GATEWAY_URL="$1"
GATEWAY_TOKEN="$2"
SESSION_KEY="${3:-agent:main:telegram:direct:90000000999}"

# Защита от CRLF при передаче токена из Windows/PowerShell
GATEWAY_TOKEN="${GATEWAY_TOKEN//$'\r'/}"
SESSION_KEY="${SESSION_KEY//$'\r'/}"

FAR_DATE="$(date -u -d '+70 days' +%Y-%m-%d)"

invoke_named_tool() {
  local tool_name="$1"
  local args_json="$2"
  local payload

  payload="$(jq -n \
    --arg tool_name "$tool_name" \
    --arg session_key "$SESSION_KEY" \
    --argjson args "$args_json" \
    '{
      tool: $tool_name,
      sessionKey: $session_key,
      args: $args
    }'
  )"

  curl --fail -sS -X POST "${GATEWAY_URL}/tools/invoke" \
    -H "Authorization: Bearer ${GATEWAY_TOKEN}" \
    -H "Content-Type: application/json" \
    --data "${payload}"
}

invoke_tool() {
  local args_json="$1"
  invoke_named_tool "ati_create_cargo" "${args_json}"
}

extract_text_json() {
  local response_json="$1"
  local text_json
  text_json="$(jq -r '.result.content[0].text' <<<"${response_json}")"
  jq -c . <<<"${text_json}"
}

ensure_mock_mode_or_explicit_real() {
  if [[ "${ATI_TEST_ALLOW_REAL:-0}" == "1" ]]; then
    echo "WARN: ATI_TEST_ALLOW_REAL=1 — разрешён реальный ATI API."
    return
  fi

  local status_resp status_json mock_mode
  status_resp="$(invoke_named_tool "ati_mock_status" "{}")"
  status_json="$(extract_text_json "${status_resp}")"
  mock_mode="$(jq -r '.mock_mode // "false"' <<<"${status_json}")"

  if [[ "${mock_mode}" != "true" ]]; then
    echo "FAIL: ATI mock mode выключен. Чтобы не публиковать реальные грузы, включите mockMode=true в конфиге плагина."
    echo "Если осознанно нужен реальный ATI API, запустите с ATI_TEST_ALLOW_REAL=1."
    exit 3
  fi

  echo "OK: ATI mock mode включён"
}

assert_eq() {
  local actual="$1"
  local expected="$2"
  local label="$3"

  if [[ "${actual}" != "${expected}" ]]; then
    echo "FAIL: ${label}: ожидалось '${expected}', получено '${actual}'"
    exit 1
  fi
  echo "OK: ${label}"
}

assert_true() {
  local value="$1"
  local label="$2"

  if [[ "${value}" != "true" ]]; then
    echo "FAIL: ${label}: ожидалось true, получено '${value}'"
    exit 1
  fi
  echo "OK: ${label}"
}

echo "== Smoke: ati_create_cargo =="
ensure_mock_mode_or_explicit_real

echo "-- Кейс 1: Москва/СПб без адресов -> ADDRESS_REQUIRED"
case1_resp="$(invoke_tool '{
  "loading_city_id": 3611,
  "unloading_city_id": 1,
  "cargo_description": "диван",
  "weight": 300,
  "volume": 3,
  "body_type_id": 500,
  "loading_date": "завтра"
}')"
case1_json="$(extract_text_json "${case1_resp}")"
case1_code="$(jq -r '.error_code' <<<"${case1_json}")"
assert_eq "${case1_code}" "ADDRESS_REQUIRED" "error_code для кейса 1"

echo "-- Кейс 2: дата > 60 дней -> DATE_OUT_OF_RANGE"
case2_resp="$(invoke_tool "{
  \"loading_city_id\": 1422,
  \"unloading_city_id\": 80,
  \"cargo_description\": \"диван\",
  \"weight\": 300,
  \"volume\": 3,
  \"body_type_id\": 500,
  \"loading_date\": \"${FAR_DATE}\"
}")"
case2_json="$(extract_text_json "${case2_resp}")"
case2_code="$(jq -r '.error_code' <<<"${case2_json}")"
assert_eq "${case2_code}" "DATE_OUT_OF_RANGE" "error_code для кейса 2"

echo "-- Кейс 3: вес < 200 кг -> INVALID_INPUT"
case3_resp="$(invoke_tool '{
  "loading_city_id": 1422,
  "unloading_city_id": 80,
  "cargo_description": "диван",
  "weight": 100,
  "volume": 3,
  "body_type_id": 500,
  "loading_date": "завтра"
}')"
case3_json="$(extract_text_json "${case3_resp}")"
case3_code="$(jq -r '.error_code' <<<"${case3_json}")"
assert_eq "${case3_code}" "INVALID_INPUT" "error_code для кейса 3"

echo "-- Кейс 4: валидные данные -> success=true, normalized_loading_date"
case4_resp="$(invoke_tool '{
  "loading_city_id": 1422,
  "unloading_city_id": 80,
  "cargo_description": "диван",
  "weight": 300,
  "volume": 3,
  "body_type_id": 500,
  "loading_date": "завтра"
}')"
case4_json="$(extract_text_json "${case4_resp}")"
case4_success="$(jq -r '.success' <<<"${case4_json}")"
case4_norm_date="$(jq -r '.normalized_loading_date // ""' <<<"${case4_json}")"
case4_cargo_id="$(jq -r '.cargo_id // ""' <<<"${case4_json}")"
assert_true "${case4_success}" "success для кейса 4"
if [[ ! "${case4_norm_date}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  echo "FAIL: normalized_loading_date для кейса 4 не похожа на YYYY-MM-DD: '${case4_norm_date}'"
  exit 1
fi
echo "OK: normalized_loading_date для кейса 4"

if [[ -n "${case4_cargo_id}" ]]; then
  cleanup_payload="$(jq -n \
    --arg session_key "$SESSION_KEY" \
    --arg cargo_id "$case4_cargo_id" \
    '{tool:"ati_delete_cargo", sessionKey:$session_key, args:{load_id:$cargo_id}}'
  )"
  cleanup_resp="$(curl --fail -sS -X POST "${GATEWAY_URL}/tools/invoke" \
    -H "Authorization: Bearer ${GATEWAY_TOKEN}" \
    -H "Content-Type: application/json" \
    --data "${cleanup_payload}"
  )"
  cleanup_text="$(jq -r '.result.content[0].text // ""' <<<"${cleanup_resp}")"
  if [[ "${cleanup_text}" == *"Груз удалён с биржи."* ]]; then
    echo "OK: удаление тестового груза (${case4_cargo_id})"
  else
    echo "WARN: тестовый груз ${case4_cargo_id} не удалён автоматически"
  fi
fi

echo "== Smoke завершён успешно =="
