#!/usr/bin/env bash
# E2E flow-тесты ATI инструментов через OpenClaw /tools/invoke.
# Проверяет:
# 1) Базовые валидации (адрес, дата, вес)
# 2) Детект типа оплаты (ati_detect_payment_type)
# 3) Передачу payment_type в ati_create_cargo
# 4) Сценарий повторного клиента: архив -> повторное размещение (restore/create fallback)

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Использование: $0 <gateway_url> <gateway_token> [session_key]"
  echo "Пример: $0 http://127.0.0.1:18790 <TOKEN> agent:main:telegram:direct:90000000999"
  exit 2
fi

GATEWAY_URL="$1"
GATEWAY_TOKEN="$2"
SESSION_KEY="${3:-agent:main:telegram:direct:90000000999}"

GATEWAY_TOKEN="${GATEWAY_TOKEN//$'\r'/}"
SESSION_KEY="${SESSION_KEY//$'\r'/}"

far_date="$(date -u -d '+70 days' +%Y-%m-%d)"
date_a="$(date -u -d '+1 day' +%Y-%m-%d)"
date_b="$(date -u -d '+2 day' +%Y-%m-%d)"
run_id="$(date +%s)"

invoke_tool() {
  local tool_name="$1"
  local args_json="$2"
  local payload

  payload="$(jq -n \
    --arg tool "$tool_name" \
    --arg session_key "$SESSION_KEY" \
    --argjson args "$args_json" \
    '{
      tool: $tool,
      sessionKey: $session_key,
      args: $args
    }'
  )"

  curl --fail -sS -X POST "${GATEWAY_URL}/tools/invoke" \
    -H "Authorization: Bearer ${GATEWAY_TOKEN}" \
    -H "Content-Type: application/json" \
    --data "${payload}"
}

extract_tool_text_json() {
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
  status_resp="$(invoke_tool "ati_mock_status" "{}")"
  status_json="$(extract_tool_text_json "${status_resp}")"
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

cleanup_cargo_if_any() {
  local cargo_id="$1"
  if [[ -z "${cargo_id}" || "${cargo_id}" == "null" ]]; then
    return
  fi

  local cleanup_resp cleanup_text
  cleanup_resp="$(invoke_tool "ati_delete_cargo" "$(jq -n --arg id "$cargo_id" '{load_id:$id}')")" || true
  cleanup_text="$(jq -r '.result.content[0].text // ""' <<<"${cleanup_resp}")"
  if [[ "${cleanup_text}" == *"Груз удалён с биржи."* ]]; then
    echo "OK: удаление тестового груза (${cargo_id})"
  else
    echo "WARN: не удалось автоматически удалить тестовый груз (${cargo_id})"
  fi
}

echo "== Flow: ATI payment + restore =="
ensure_mock_mode_or_explicit_real

echo "-- Кейс 1: Москва/СПб без адресов -> ADDRESS_REQUIRED"
case1_args='{
  "loading_city_id": 3611,
  "unloading_city_id": 1,
  "cargo_description": "диван",
  "weight": 300,
  "volume": 3,
  "body_type_id": 500,
  "loading_date": "завтра"
}'
case1_resp="$(invoke_tool "ati_create_cargo" "${case1_args}")"
case1_json="$(extract_tool_text_json "${case1_resp}")"
assert_eq "$(jq -r '.error_code' <<<"${case1_json}")" "ADDRESS_REQUIRED" "error_code для кейса 1"

echo "-- Кейс 2: дата > 60 дней -> DATE_OUT_OF_RANGE"
case2_args="$(jq -n --arg d "$far_date" '{
  loading_city_id: 1422,
  unloading_city_id: 80,
  cargo_description: "диван",
  weight: 300,
  volume: 3,
  body_type_id: 500,
  loading_date: $d
}')"
case2_resp="$(invoke_tool "ati_create_cargo" "${case2_args}")"
case2_json="$(extract_tool_text_json "${case2_resp}")"
assert_eq "$(jq -r '.error_code' <<<"${case2_json}")" "DATE_OUT_OF_RANGE" "error_code для кейса 2"

echo "-- Кейс 3: вес < 200 кг -> INVALID_INPUT"
case3_args='{
  "loading_city_id": 1422,
  "unloading_city_id": 80,
  "cargo_description": "диван",
  "weight": 100,
  "volume": 3,
  "body_type_id": 500,
  "loading_date": "завтра"
}'
case3_resp="$(invoke_tool "ati_create_cargo" "${case3_args}")"
case3_json="$(extract_tool_text_json "${case3_resp}")"
assert_eq "$(jq -r '.error_code' <<<"${case3_json}")" "INVALID_INPUT" "error_code для кейса 3"

echo "-- Кейс 4: детект типа оплаты по фразам"
declare -a payment_cases=(
  "без торга, цена фикс|without-bargaining"
  "давайте запрос ставки на направление|rate-request"
  "можно поторговаться по цене|with-bargaining"
  "хочу торги в формате аукциона|auction"
)

for item in "${payment_cases[@]}"; do
  phrase="${item%%|*}"
  expected="${item##*|}"
  resp="$(invoke_tool "ati_detect_payment_type" "$(jq -n --arg text "$phrase" '{text:$text}')")"
  json="$(extract_tool_text_json "${resp}")"
  actual="$(jq -r '.payment_type' <<<"${json}")"
  assert_eq "${actual}" "${expected}" "ati_detect_payment_type: '${phrase}'"
done

echo "-- Кейс 5: create с payment_type=without-bargaining"
case5_client_key="flow_payment_${run_id}"
case5_args="$(jq -n --arg d "$date_a" --arg ck "$case5_client_key" '{
  loading_city_id: 1422,
  unloading_city_id: 80,
  cargo_description: "диван тест payment",
  weight: 300,
  volume: 3,
  body_type_id: 500,
  loading_date: $d,
  payment_type: "without-bargaining",
  rate_without_vat: 25000,
  client_key: $ck
}')"
case5_resp="$(invoke_tool "ati_create_cargo" "${case5_args}")"
case5_json="$(extract_tool_text_json "${case5_resp}")"
assert_true "$(jq -r '.success' <<<"${case5_json}")" "success для кейса 5"
assert_eq "$(jq -r '.resolved_payment_type // ""' <<<"${case5_json}")" "without-bargaining" "resolved_payment_type для кейса 5"
case5_cargo_id="$(jq -r '.cargo_id // ""' <<<"${case5_json}")"
cleanup_cargo_if_any "${case5_cargo_id}"

echo "-- Кейс 6: повторный клиент/маршрут: архив -> повторная публикация"
restore_client_key="flow_restore_${run_id}"

case6a_args="$(jq -n --arg d "$date_a" --arg ck "$restore_client_key" '{
  loading_city_id: 1422,
  unloading_city_id: 80,
  cargo_description: "диван тест restore",
  weight: 350,
  volume: 3.5,
  body_type_id: 500,
  loading_date: $d,
  payment_type: "rate-request",
  client_key: $ck,
  try_restore_archived: true
}')"
case6a_resp="$(invoke_tool "ati_create_cargo" "${case6a_args}")"
case6a_json="$(extract_tool_text_json "${case6a_resp}")"
assert_true "$(jq -r '.success' <<<"${case6a_json}")" "success для кейса 6a (первичное создание)"
case6a_cargo_id="$(jq -r '.cargo_id // ""' <<<"${case6a_json}")"
if [[ -z "${case6a_cargo_id}" ]]; then
  echo "FAIL: кейс 6a не вернул cargo_id"
  exit 1
fi

delete6_resp="$(invoke_tool "ati_delete_cargo" "$(jq -n --arg id "$case6a_cargo_id" '{load_id:$id}')")"
delete6_text="$(jq -r '.result.content[0].text // ""' <<<"${delete6_resp}")"
if [[ "${delete6_text}" != *"Груз удалён с биржи."* ]]; then
  echo "FAIL: кейс 6 не смог отправить груз в архив"
  exit 1
fi
echo "OK: кейс 6a груз отправлен в архив (${case6a_cargo_id})"

case6b_args="$(jq -n --arg d "$date_b" --arg ck "$restore_client_key" '{
  loading_city_id: 1422,
  unloading_city_id: 80,
  cargo_description: "диван тест restore",
  weight: 350,
  volume: 3.5,
  body_type_id: 500,
  loading_date: $d,
  payment_type: "rate-request",
  client_key: $ck,
  try_restore_archived: true
}')"
case6b_resp="$(invoke_tool "ati_create_cargo" "${case6b_args}")"
case6b_json="$(extract_tool_text_json "${case6b_resp}")"
assert_true "$(jq -r '.success' <<<"${case6b_json}")" "success для кейса 6b (повторная заявка)"

case6b_operation="$(jq -r '.operation // ""' <<<"${case6b_json}")"
case6b_cargo_id="$(jq -r '.cargo_id // ""' <<<"${case6b_json}")"
if [[ "${case6b_operation}" == "restored" ]]; then
  echo "OK: кейс 6b выполнен через restore архивного груза"
else
  echo "WARN: кейс 6b выполнен без restore (operation=${case6b_operation:-unknown}), использован fallback create"
fi

cleanup_cargo_if_any "${case6b_cargo_id}"

echo "== Flow завершён успешно =="
