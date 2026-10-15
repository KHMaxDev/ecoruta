#!/usr/bin/env bash
# =============================================================================
# EcoRuta — Conversión del corredor OSM a red SUMO (Linux/WSL2)
# =============================================================================
# Requiere SUMO >= 1.20 y osmium-tool instalados en el PATH.
#   sudo apt-get install sumo sumo-tools osmium-tool
# Uso:  ./osm_to_sumo.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAW_DIR="${SCRIPT_DIR}/data/raw"
OUT_DIR="${SCRIPT_DIR}/data/sumo_corridor"

BBOX="18.80,-100.50,20.20,-98.00"   # min_lat,min_lon,max_lat,max_lon (CDMX-Puebla-Toluca)
PBF_IN="${RAW_DIR}/corridor_mexico.osm.pbf"
OSM_IN="${RAW_DIR}/corridor_mexico.osm"

mkdir -p "${OUT_DIR}"

if [[ ! -f "${OSM_IN}" ]]; then
  echo "[EcoRuta] Recortando el extracto OSM al BBOX del corredor…"
  osmium extract --bbox "${BBOX}" --strategy complete_ways -o "${OSM_IN}" "${PBF_IN}"
fi

echo "[EcoRuta] Generando red con netconvert…"
netconvert \
  --osm-files "${OSM_IN}" \
  --output-file "${OUT_DIR}/corridor.net.xml" \
  --geometry.remove \
  --ramps.guess \
  --junctions.join \
  --tls.guess-signals \
  --tls.discard-simple \
  --no-turnarounds true

echo "[EcoRuta] Generando demanda inicial con od2trips (matriz aleatoria de referencia)…"
python "${SUMO_HOME}/tools/randomTrips.py" \
  -n "${OUT_DIR}/corridor.net.xml" \
  -o "${OUT_DIR}/trips.trips.xml" \
  -b 25200 -e 32400 -p 3.0 --fringe-factor 10 --seed 42

echo "[EcoRuta] Red SUMO lista en ${OUT_DIR}/corridor.net.xml"
