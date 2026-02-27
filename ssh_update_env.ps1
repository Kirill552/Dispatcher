$key = "C:\Users\whirp\.ssh\AI_dispetcher"
$srv = "ai_dispetcher@46.17.250.109"

# Читаем текущий .env
$current = & ssh -i $key $srv 'cat ~/Dispatcher/.env 2>/dev/null || echo NO_ENV_FILE'
Write-Host "=== Текущий .env ===" -ForegroundColor Cyan
$current | ForEach-Object { Write-Host $_ }

# Добавляем переменные по одной
Write-Host "`n=== Добавляем переменные ===" -ForegroundColor Cyan

$vk = 'echo "VK_COMMUNITY_TOKEN=vk1.a.cXG7TpaKRYMYu-VLd-ygoCRKW2Jam8rcjULRHkZ0ahfC3UGYvKwzIHVHV6Ymg9pw-E0dk-PPKeS8tV74g-hCQ1gvXhi3ybQyN044eyiWzo90tEl9vu9Z76p6My23yOQcuTaPVdcUN7TzoXu64L94mwuIHxLwAkwUBWKzjgSmbG-Rw0kBxcNKyVA8aC-kNdQDO0fUtaErl7nFxaSbtqXu4g" >> ~/Dispatcher/.env'
& ssh -i $key $srv $vk
Write-Host "VK_COMMUNITY_TOKEN - добавлен"

$sheets = 'echo "GOOGLE_SHEETS_ID=1LCuEJYhxyAXrQ2cRszDXrQbIZ86JQWatnwlIX0MfwLk" >> ~/Dispatcher/.env'
& ssh -i $key $srv $sheets
Write-Host "GOOGLE_SHEETS_ID - добавлен"

$botname = 'echo "TELEGRAM_BOT_USERNAME=to_da_ce_bot" >> ~/Dispatcher/.env'
& ssh -i $key $srv $botname
Write-Host "TELEGRAM_BOT_USERNAME - добавлен"

$gsa = 'echo "GOOGLE_SERVICE_ACCOUNT_JSON=" >> ~/Dispatcher/.env'
& ssh -i $key $srv $gsa
Write-Host "GOOGLE_SERVICE_ACCOUNT_JSON - добавлен (пустой)"

# Итоговый .env
Write-Host "`n=== Итоговый .env ===" -ForegroundColor Green
$final = & ssh -i $key $srv 'cat ~/Dispatcher/.env'
$final | ForEach-Object { Write-Host $_ }
