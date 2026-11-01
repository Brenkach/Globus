# Cross-Instance Consistency: a chain of requests through DIFFERENT instances, no sticky sessions.
# Run: .\scripts\test_cross_instance.ps1   (after docker compose up -d --build)
# NOTE: ASCII-only on purpose (PowerShell 5.1 misreads UTF-8 without BOM).
. "$PSScriptRoot\common.ps1"

Write-Host "`n=== Setup test data (through different instances) ===" -ForegroundColor Cyan
$fx = New-TestFixture

Write-Host "`n=== Chain: POST -> app-1, GET -> app-2, PATCH -> app-2, GET -> app-1 ===" -ForegroundColor Cyan
$r = New-TestOrder $fx $APP1
Show "POST /orders" $r
$id = $r.Data.id
Assert ($r.Instance -eq "app-1") "order created by app-1"

$r = Call GET "$APP2/orders/$id"
Show "GET /orders/$id" $r
Assert (($r.Instance -eq "app-2") -and ($r.Data.status -eq "CREATED")) "app-2 sees the order created by app-1 (CREATED)"
Assert ([decimal]$r.Data.total_amount -eq 200) "total calculated on server: 200"

$r = Call PATCH "$APP2/orders/$id/status" @{ status = "ACCEPTED" }
Show "PATCH status=ACCEPTED" $r
Assert ($r.Instance -eq "app-2") "status changed by app-2"

$r = Call GET "$APP1/orders/$id"
Show "GET /orders/$id" $r
Assert (($r.Instance -eq "app-1") -and ($r.Data.status -eq "ACCEPTED")) "app-1 sees the change made by app-2 (ACCEPTED)"

Write-Host "`n=== Assign courier on app-1, verify on app-2 ===" -ForegroundColor Cyan
$r = Call POST "$APP1/orders/$id/assign-courier"
Show "POST assign-courier" $r
Assert ($r.Data.courier_id -eq $fx.Courier) "courier assigned by app-1"
$r = Call GET "$APP2/couriers/$($fx.Courier)"
Show "GET /couriers/$($fx.Courier)" $r
Assert ($r.Data.status -eq "BUSY") "app-2 sees the courier as BUSY"

Write-Host "`n=== 8 requests through the load balancer (round-robin) ===" -ForegroundColor Cyan
$seen = @{}
1..8 | ForEach-Object {
    $r = Call GET "$LB/orders/$id"
    Show "GET via LB #$_" $r
    $seen[$r.Instance] = 1 + [int]$seen[$r.Instance]
}
$summary = ($seen.Keys | Sort-Object | ForEach-Object { $_ + "=" + $seen[$_] }) -join ", "
Assert ($seen.Count -ge 2) "requests were spread across instances: $summary"

Write-Host "`nAll cross-instance consistency checks passed." -ForegroundColor Green