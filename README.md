# EcoRuta — Optimización Multiobjetivo de Rutas en México

**EcoRuta** calcula el **frente de Pareto** entre **Costo Monetario Total ($C$)** y
**Tiempo de Viaje ($T$)** para rutas viales en México, sujeto a restricciones físicas
duras y a horarios dependientes del tiempo.

---

## Principios de diseño (reglas inquebrantables)

1. **Bi-objetivo estricto** — el motor `TD-MOLS` solo optimiza `[costo_mxn, tiempo_s]`.
   La incertidumbre se modela ejecutando el motor sobre perfiles $P_{50}$ (esperado) vs.
   $P_{10}$ (tiempo $P_{90}$ robusto).
2. **Modelo físico de consumo** — nunca rendimiento estático ($km/l$). El consumo se
   calcula con el modelo longitudinal de fuerzas en Rust (aerodinámica, rodadura, gravedad
   por pendiente, inercia por congestión, factor $\kappa_v$).
3. **Regularización FIFO obligatoria** — toda serie temporal debe cumplir
   $\frac{\Delta \tau}{\Delta t} \ge -0.95$.
4. **Subgrafo factible primero** — nunca se ejecuta la búsqueda sobre el grafo nacional
   completo (`SubgraphExtractorService`).
5. **Riesgo delictivo solo municipal** — los datos del SESNSP jamás se interpolan por calle;
   se presentan como auditoría contextual.
6. **Auditoría obligatoria** — toda respuesta JSON incluye `data_provenance_audit`.

---

## Arquitectura

```
ahorro_rutas/
├── database/         # init_db.sql (PostGIS 3.4 + pgRouting 3.6) + seeds
├── rust_core/        # Motor TD-MOLS + física en Rust, expuesto vía PyO3 (ecoruta_core)
├── backend/          # FastAPI + SQLAlchemy 2.0 async + OR-Tools (GTDVRPTW)
├── simulation/       # SUMO (TraCI) + validación del núcleo
├── frontend/         # React 19 + TypeScript + MapLibre GL + deck.gl + Recharts
└── docker-compose.yml
```

### Núcleo Rust (`rust_core`)

| Módulo         | Responsabilidad                                              |
|----------------|-------------------------------------------------------------|
| `physics.rs`   | Modelo longitudinal de fuerzas → `compute_edge_energy_units` |
| `fifo.rs`      | Regularización e interpolación FIFO                          |
| `td_mols.rs`   | Algoritmo de etiquetado multiobjetivo dependiente del tiempo |
| `python.rs`    | Bindings PyO3 (`ecoruta_core`)                               |

API Python expuesta: `VehicleParams`, `EdgeData`, `ParetoRoute`, `solve_td_mols`,
`regularize_fifo`, `interpolate_fifo`, `compute_energy_units`.

---

## Requisitos

- Docker 29+ / Docker Compose v2+ (recomendado para todo el stack)
- Para desarrollo local: Python 3.12, Node 24, Rust 1.99 (toolchain `msvc` en Windows)

---

## Puesta en marcha

### 1. Infraestructura base

```bash
cp .env.example .env          # rellenar tokens reales
docker compose up -d postgis redis valhalla
docker compose logs -f valhalla   # la 1ª vez descarga tiles de México
```

### 2. Cargar el esquema geoespacial (piloto CDMX–Puebla–Toluca)

```bash
python -m pip install -r scripts/requirements.txt
python scripts/test_db_schema.py
python scripts/etl_inegi_rnc_dem.py
```

### 3. Núcleo Rust

```bash
cd rust_core
maturin develop --release          # desarrollo local
# o wheel manylinux:
maturin build --release -i python3.12 --out dist
```

Verificación del frente de Pareto contra enumeración exhaustiva:

```bash
cargo test --release               # requiere libpython; en contenedores usar --no-default-features
```

### 4. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# Swagger: http://localhost:8000/docs
```

### 5. Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # tsc -b && vite build
```

### 6. Stack completo en contenedores

```bash
docker compose --profile full up --build
```

---

## Endpoints principales

| Método | Ruta                              | Descripción                                   |
|--------|-----------------------------------|-----------------------------------------------|
| POST   | `/api/v1/routes/optimize`         | Frente de Pareto origen→destino               |
| POST   | `/api/v1/routes/optimize-multistop` | Secuencia óptima de paradas (GTDVRPTW)      |
| GET    | `/api/v1/vehicles/profiles`       | Perfiles vehiculares con parámetros físicos   |
| POST   | `/api/v1/admin/sync-data`         | Sincroniza precios CNE y cierres CONAGUA      |
| GET    | `/health`                         | Estado del servicio                           |

Toda respuesta incluye `data_provenance_audit` (fuente, resolución espacial y timestamp).

---

## Validación

### Núcleo (contenedor, sin libpython)

```bash
docker run --rm -v "$PWD/rust_core:/app" -w /app rust:1.99 \
  cargo test --release --no-default-features
```

### Wheel + smoke test end-to-end

```bash
docker run --rm --entrypoint bash -v "$PWD/rust_core:/io" -w /io \
  ghcr.io/pyo3/maturin:latest -lc "maturin build --release -i cpython3.12 --out /io/dist"

docker run --rm -v "$PWD/rust_core:/io" -w /io python:3.12-slim \
  bash -lc "pip install --quiet --no-index --find-links /io/dist ecoruta_core && python /io/smoke_test.py"
```

### Simulación SUMO

```bash
bash simulation/osm_to_sumo.sh                    # Linux/WSL2
powershell -File simulation/osm_to_sumo.ps1       # Windows
python simulation/run_validation.py               # MAPE vs. EcoRuta
python simulation/metrics_evaluator.py            # métricas agregadas
```

---

## Stack

PostgreSQL 16 · PostGIS 3.4 · pgRouting 3.6 · Redis 7.4 · Valhalla ·
Rust 2021 (PyO3 0.30, maturin) · Python 3.12 (FastAPI, Pydantic v2, SQLAlchemy 2.0,
OR-Tools) · SUMO · React 19 · TypeScript · Vite · MapLibre GL · deck.gl · Recharts · TailwindCSS.
