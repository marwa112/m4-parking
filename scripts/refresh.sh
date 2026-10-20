#!/usr/bin/env bash
# Rebuilds docs/data.json. Run from the repo root.
#   City parking + cleaning data (Göteborgs Stad open WFS): every run.
#   OpenStreetMap addresses + streets: only when REFRESH_OSM=1 or the cache is missing,
#   because they rarely change and OSM asks for light use of its API.
set -euo pipefail
ROOT=$(pwd)
mkdir -p build data/osm && cd build
python3 ../scripts/fetch_city.py
python3 ../scripts/build_segments.py
if [[ "${REFRESH_OSM:-0}" == "1" || ! -s "$ROOT/data/osm/m_addr.json" ]]; then
  python3 ../scripts/fetch_osm.py
  cp m_addr.json m_roads.json "$ROOT/data/osm/"
else
  cp "$ROOT/data/osm/m_addr.json" "$ROOT/data/osm/m_roads.json" .
fi
python3 ../scripts/fetch_other.py
python3 ../scripts/pack.py
