$Url = $env:WARM_URL
if (-not $Url) { $Url = "https://scam-agent.onrender.com/health" }

$Interval = if ($env:WARM_INTERVAL_SECONDS) { [int]$env:WARM_INTERVAL_SECONDS } else { 300 }
$Timeout = if ($env:WARM_TIMEOUT_SECONDS) { [int]$env:WARM_TIMEOUT_SECONDS } else { 5 }

Write-Host "Warming $Url every $Interval seconds (timeout $Timeout)"

while ($true) {
    try {
        $resp = Invoke-WebRequest -Uri $Url -TimeoutSec $Timeout -UseBasicParsing
        $body = $resp.Content
        if ($body -and $body.Length -gt 200) { $body = $body.Substring(0, 200) }
        Write-Host "$(Get-Date -Format o) $($resp.StatusCode) $body"
    } catch {
        Write-Host "$(Get-Date -Format o) error $($_.Exception.Message)"
    }
    Start-Sleep -Seconds $Interval
}
