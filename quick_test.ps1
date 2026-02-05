# PowerShell commands for testing your API

$API_KEY = "honeypot-2026-03-02"
$LOCAL_URL = "http://localhost:8000/"
$RENDER_URL = "https://scam-agent.onrender.com/"

$headers = @{
    "Content-Type" = "application/json"
    "x-api-key" = $API_KEY
}

$body = @{
    sessionId = "test-session-123"
    message = @{
        sender = "scammer"
        text = "Your bank account will be blocked today. Verify immediately."
    }
} | ConvertTo-Json -Depth 10

Write-Host "=== Testing Local Server ===" -ForegroundColor Green
try {
    $response = Invoke-RestMethod -Uri $LOCAL_URL -Method POST -Headers $headers -Body $body -TimeoutSec 30
    Write-Host "✅ Success!" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Testing Render Deployed (First Call) ===" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri $RENDER_URL -Method POST -Headers $headers -Body $body -TimeoutSec 30
    Write-Host "✅ Success!" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n⏳ Waiting 3 seconds before second call..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

Write-Host "`n=== Testing Render Deployed (Second Call) ===" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri $RENDER_URL -Method POST -Headers $headers -Body $body -TimeoutSec 30
    Write-Host "✅ Success!" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
}
