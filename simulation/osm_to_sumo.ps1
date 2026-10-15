# =============================================================================
# EcoRuta — Conversión del corredor OSM a red SUMO (Windows / PowerShell 5.1+)
# =============================================================================
# Requiere SUMO >= 1.20 ($env:SUMO_HOME) y osmium-tool en el PATH.
# Uso:  powershell -ExecutionPolicy Bypass -File .\osm_to_sumo.ps1
# =============================================================================
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RawDir    = Join-Path $ScriptDir "data\raw"
$OutDir    = Join-Path $ScriptDir "data\sumo_corridor"

$Bbox   = "18.80,-100.50,20.20,-98.00"   # min_lat,min_lon,max_lat,max_lon
$PbfIn  = Join-Path $RawDir "corridor_mexico.osm.pbf"
$OsmIn  = Join-Path $RawDir "corridor_mexico.osm"

if (-not (Test-Path -LiteralPath $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

if (-not (Test-Path -LiteralPath $OsmIn)) {
    Write-Host "[EcoRuta] Recortando el extracto OSM al BBOX del corredor..."
    & osmium extract --bbox $Bbox --strategy complete_ways -o $OsmIn $PbfIn
}

Write-Host "[EcoRuta] Generando red con netconvert..."
& netconvert `
    --osm-files $OsmIn `
    --output-file (Join-Path $OutDir "corridor.net.xml") `
    --geometry.remove `
    --ramps.guess `
    --junctions.join `
    --tls.guess-signals `
    --tls.discard-simple `
    --no-turnarounds true

Write-Host "[EcoRuta] Generando demanda inicial de referencia..."
& python (Join-Path $env:SUMO_HOME "tools\randomTrips.py") `
    -n (Join-Path $OutDir "corridor.net.xml") `
    -o (Join-Path $OutDir "trips.trips.xml") `
    -b 25200 -e 32400 -p 3.0 --fringe-factor 10 --seed 42

Write-Host "[EcoRuta] Red SUMO lista en $OutDir\corridor.net.xml"
