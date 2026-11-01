# Restart / Instance Loss: emergency stop of one instance in the middle of a business scenario.
# Run: .\scripts\test_failover.ps1            (graceful: docker compose stop)
#      .\scripts\test_failover.ps1 -Mode kill (abrupt: docker compose kill, SIGKILL)
# NOTE: ASCII-only on purpose (PowerShell 5.1 misreads UTF-8 without BOM).
param([ValidateSet("stop", "kill")][string]$Mode = "stop")
. "$PSScriptRoot\common.ps1"

Write-Host "`n=== Setup and start of the scenario (through the load balancer) ===" -ForegroundColor Cyan
$fx = New-TestFixture
$r = New-TestOrder $fx $LB
Show "POST /orders (LB)" $r
$id = $r.Data.id
$r = Call PATCH "$LB/orders/$id/status" @{ status = "ACCEPTED" }
Show "PATCH ACCEPTED (LB)" $r
$r = Call POST "$LB/orders/$id/assign-courier"
Show "POST assign-courier (LB)" $r
$r = Call PATCH "$LB/orders/$id/status" @{ status = "COOKING" }
Show "PATCH COOKING (LB)" $r

Write-Host "`n=== Background load: 60 courier location updates through the LB ===" -ForegroundColor Cyan
$job = Start-Job -ArgumentList $LB, $fx.Courier -ScriptBlock {
    param($lb, $courier)
    $ok = 0; $fail = 0
    1..60 | ForEach-Object {
        try {
            $body = @{ lat = 10.0; lng = (10.0 + $_ / 100000) } | ConvertTo-Json
            Invoke-WebRequest -Method PUT -Uri "$lb/couriers/$courier/location" -Body $body -ContentType "application/json" -UseBasicParsing | Out-Null
            $ok++
        } catch { $fail++ }
        Start-Sleep -Milliseconds 100
    }
    [pscustomobject]@{ Ok = $ok; Failed = $fail }
}

Start-Sleep -Seconds 2
Write-Host "`n>>> docker compose $Mode app1  (app-1 is lost in the middle of the scenario)" -ForegroundColor Yellow
docker compose $Mode app1 | Out-Null

Write-Host "`n=== Scenario continues: app-2 must serve everything ===" -ForegroundColor Cyan
$r = Call GET "$LB/orders/$id"
Show "GET /orders/$id (LB)" $r
Assert ($r.Instance -eq "app-2") "after app-1 is lost, app-2 handles the requests"
Assert (($r.Data.status -eq "COOKING") -and ($r.Data.courier_id -eq $fx.Courier)) "order state is not lost (COOKING, courier assigned)"
foreach ($s in @("READY", "PICKED_UP", "DELIVERED")) {
    $r = Call PATCH "$LB/orders/$id/status" @{ status = $s }
    Show "PATCH $s (LB)" $r
    Assert (($r.Instance -eq "app-2") -and ($r.Data.status -eq $s)) "transition to $s done by app-2"
}
$r = Call GET "$LB/couriers/$($fx.Courier)"
Show "GET courier (LB)" $r
Assert ($r.Data.status -eq "AVAILABLE") "courier released automatically after DELIVERED"

$res = Receive-Job $job -Wait -AutoRemoveJob
Write-Host ("Background PUT location: ok {0}, failed {1} (a few failures are possible only for requests that were running on the killed node)" -f $res.Ok, $res.Failed)
Assert ($res.Ok -gt 0) "the remaining location updates went through app-2"

Write-Host "`n=== Restoring app-1 ===" -ForegroundColor Cyan
docker compose start app1 | Out-Null
for ($i = 0; $i -lt 30; $i++) {
    try { Call GET "$APP1/health" | Out-Null; break } catch { Start-Sleep -Seconds 1 }
}
$r = Call GET "$APP1/orders/$id"
Show "GET /orders/$id (app-1)" $r
Assert (($r.Instance -eq "app-1") -and ($r.Data.status -eq "DELIVERED")) "restarted app-1 immediately sees the current state (DELIVERED)"

Write-Host "`nInstance-loss scenario passed: no data lost." -ForegroundColor Green