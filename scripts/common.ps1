# Shared helpers for verification scripts. Works with Windows PowerShell 5.1 and PowerShell 7.
# NOTE: this file is ASCII-only on purpose (PowerShell 5.1 misreads UTF-8 without BOM).
$ErrorActionPreference = "Stop"

$LB   = "http://localhost:8000"   # load balancer (round-robin)
$APP1 = "http://localhost:8001"   # instance app-1 directly
$APP2 = "http://localhost:8002"   # instance app-2 directly

function Call([string]$Method, [string]$Url, $Body = $null) {
    $p = @{ Method = $Method; Uri = $Url; UseBasicParsing = $true }
    if ($null -ne $Body) {
        $p.Body = ($Body | ConvertTo-Json -Depth 6)
        $p.ContentType = "application/json"
    }
    $r = Invoke-WebRequest @p
    [pscustomobject]@{
        Status   = [int]$r.StatusCode
        Instance = [string]$r.Headers["X-Instance-ID"]
        Data     = ($r.Content | ConvertFrom-Json)
    }
}

function Show([string]$Label, $Resp) {
    Write-Host ("{0,-34} -> HTTP {1}  X-Instance-ID: {2}" -f $Label, $Resp.Status, $Resp.Instance)
}

function Assert([bool]$Cond, [string]$Message) {
    if (-not $Cond) { throw "CHECK FAILED: $Message" }
    Write-Host "   OK: $Message" -ForegroundColor Green
}

# Creates a restaurant, a dish, a customer and a courier next to the restaurant (no seed needed).
function New-TestFixture {
    $suffix = Get-Random -Minimum 10000000 -Maximum 99999999
    # Random point on the map: no seed/previous-run couriers nearby, so courier assignment is deterministic.
    $lat = [math]::Round((Get-Random -Minimum -60000 -Maximum 60000) / 1000.0, 3)
    $lng = [math]::Round((Get-Random -Minimum -170000 -Maximum 170000) / 1000.0, 3)
    $rest = (Call POST "$APP1/restaurants" @{ name = "LabTest $suffix"; address = "Test st 1"; lat = $lat; lng = $lng }).Data
    $dish = (Call POST "$APP2/restaurants/$($rest.id)/menu" @{ name = "Dish"; price = "100.00" }).Data
    $cust = (Call POST "$APP1/customers" @{ name = "Tester"; phone = "+3805$suffix" }).Data
    $cour = (Call POST "$APP2/couriers" @{ name = "Courier"; phone = "+3806$suffix" }).Data
    Call PATCH "$APP1/couriers/$($cour.id)/status" @{ status = "AVAILABLE" } | Out-Null
    Call PUT "$APP1/couriers/$($cour.id)/location" @{ lat = $lat + 0.0001; lng = $lng + 0.0001 } | Out-Null
    [pscustomobject]@{ Restaurant = $rest.id; Dish = $dish.id; Customer = $cust.id; Courier = $cour.id }
}

function New-TestOrder($Fx, [string]$BaseUrl) {
    Call POST "$BaseUrl/orders" @{
        customer_id = $Fx.Customer; restaurant_id = $Fx.Restaurant
        delivery_address = "Delivery st 2"; delivery_lat = 50.44; delivery_lng = 30.51
        items = @(@{ menu_item_id = $Fx.Dish; quantity = 2 })
    }
}