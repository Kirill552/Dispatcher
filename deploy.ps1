$key = "C:\Users\whirp\.ssh\AI_dispetcher"
$srv = "ai_dispetcher@46.17.250.109"
Start-Sleep -Seconds 5
$l = & ssh -i $key $srv 'cd ~/Dispatcher && docker compose logs openclaw --no-log-prefix 2>&1'
$l | ForEach-Object { Write-Host $_ }
