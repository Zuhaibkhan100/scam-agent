# PowerShell commands to test the API
# Copy and paste these into PowerShell

# Test 1: Root endpoint with full format
$headers = @{
    "Content-Type" = "application/json"
    "x-api-key" = "honeypot-2026-02-03"
}

$body1 = @{
    sessionId = "wertyu-dfghj-ertyui"
    message = @{
        sender = "scammer"
        text = "Your bank account will be blocked today. Verify immediately."
        timestamp = 1770005528731
    }
    conversationHistory = @()
    metadata = @{
        channel = "SMS"
        language = "English"
        locale = "IN"
    }
} | ConvertTo-Json -Depth 10

Write-Host "Testing ROOT endpoint (/):"
try {
    $response1 = Invoke-RestMethod -Uri "http://localhost:8000/" -Method POST -Headers $headers -Body $body1
    Write-Host "✅ Status: Success"
    Write-Host "✅ Response: $($response1 | ConvertTo-Json -Depth 10)"
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)"
}

Write-Host "`n" + "="*60 + "`n"

# Test 2: Detect endpoint with minimal format
$body2 = @{
    sessionId = "test-123"
    message = @{
        sender = "scammer"
        text = "Urgent: Act now"
    }
} | ConvertTo-Json -Depth 10

Write-Host "Testing DETECT endpoint (/detect):"
try {
    $response2 = Invoke-RestMethod -Uri "http://localhost:8000/detect" -Method POST -Headers $headers -Body $body2
    Write-Host "✅ Status: Success"
    Write-Host "✅ Response: $($response2 | ConvertTo-Json -Depth 10)"
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)"
}
