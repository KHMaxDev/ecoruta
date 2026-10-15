# EcoRuta — Documentación Técnica Completa

> Sistema para la **optimización multiobjetivo de rutas viales en México** sobre la
> **red vial real** (OpenStreetMap vía OSRM y Valhalla): calcula el **frente de Pareto**
> entre el **Costo Monetario Total ($C$)** y el **Tiempo de Viaje ($T$)**, aplicando un
> modelo físico de consumo, un peaje estimado y un ajuste temporal por congestión.

---

## Tabla de contenidos

1. [Descripción general](#1-descripción-general)
2. [Arquitectura](#2-arquitectura)
3. [Stack tecnológico](#3-stack-tecnológico)
4. [Estructura del repositorio](#4-estructura-del-repositorio)
5. [Requisitos previos](#5-requisitos-previos)
6. [Configuración (.env)](#6-configuración-env)
7. [Puesta en marcha](#7-puesta-en-marcha)
8. [Motor de rutas reales (OSRM + Valhalla)](#8-motor-de-rutas-reales-osrm--valhalla)
9. [Modelo de costos: combustible, peaje y congestión](#9-modelo-de-costos-combustible-peaje-y-congestión)
10. [Frente de Pareto y recomendaciones](#10-frente-de-pareto-y-recomendaciones)
11. [Núcleo físico en Rust](#11-núcleo-físico-en-rust)
12. [Base de datos (PostgreSQL/PostGIS)](#12-base-de-datos-postgresqlpostgis)
13. [API REST](#13-api-rest)
14. [Frontend](#14-frontend)
15. [Comparativa con Google Maps, OSRM y Valhalla](#15-comparativa-con-google-maps-osrm-y-valhalla)
16. [Auditoría de procedencia de datos](#16-auditoría-de-procedencia-de-datos)
17. [Verificación y pruebas](#17-verificación-y-pruebas)
18. [Limitaciones y supuestos](#18-limitaciones-y-supuestos)
19. [Reglas de ingeniería del proyecto](#19-reglas-de-ingeniería-del-proyecto)

---

## 1. Descripción general

EcoRuta responde a una pregunta central: **¿cuáles son las rutas óptimas entre un origen
y un destino cuando el costo y el tiempo son objetivos en conflicto?** En lugar de
devolver un único camino, entrega el **conjunto de rutas no dominadas** (frente de
Pareto): no existe otra alternativa que sea simultáneamente más barata *y* más rápida.

A diferencia de una malla teórica, el sistema **enruta sobre calles reales**:

- **Geometría real** de las rutas: OSRM y Valhalla devuelven las polilíneas que siguen
  la red vial de OpenStreetMap (miles de puntos por ruta).
- **Modelo físico de consumo** (no rendimiento estático km/l): resistencia aerodinámica,
  rodadura, gravedad por pendiente e inercia, evaluado con el núcleo en Rust.
- **Peaje estimado** a partir del tramo rodado a velocidad de autopista (OSRM) o del
  atributo de peaje del proveedor (Valhalla).
- **Ajuste temporal por congestión** según hora de salida y tipo de día.
- **Incertidumbre como perfiles**: ruta normal vs. modo **robusto (P90)**.

---

## 2. Arquitectura

```
┌──────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React 19 + Vite)                     │
│  Navbar · RoutePlannerPage · MapViewer (maplibre + deck.gl) ·          │
│  TripConfigCard · WeatherWindow · ComparisonSection · ChartsSection   │
└───────────────────────────────┬──────────────────────────────────────┘
                                │  HTTP /api/v1  (proxy Vite → backend)
┌───────────────────────────────▼──────────────────────────────────────┐
│                    BACKEND (FastAPI + Pydantic v2)                    │
│  /routes/optimize · /routes/optimize-multistop · /weather ·          │
│  /vehicles/profiles · /admin/sync-data                                │
│  Services: RealRoutingService · RouteEconomyService · FuelPriceService│
│            ParetoPreferenceSelector · MultiStopVRPOptimizer           │
└───────┬───────────────────────┬──────────────────┬───────────────────┘
        │ HTTPS                 │ PyO3 (ecoruta_core)│ asyncpg / redis
┌───────▼──────────────┐ ┌──────▼────────┐ ┌────────▼──────────────────┐
│  OSRM público        │ │ rust_core     │ │ PostgreSQL 16 + PostGIS   │
│  Valhalla público    │ │ (modelo       │ │  · perfiles vehiculares   │
│  (OpenStreetMap)     │ │  físico)      │ │  · estaciones CNE         │
│                      │ │               │ │  · zonas de contexto      │
└──────────────────────┘ └───────────────┘ └───────────────────────────┘
                                  ▲
                                  │ Redis (caché + CONAGUA/clima SESNSP)
```

---

## 3. Stack tecnológico

| Capa                | Tecnología |
|---------------------|------------|
| Enrutamiento real   | OSRM público (`router.project-osrm.org`) + Valhalla público |
| Núcleo físico       | Rust 2021, `PyO3` 0.30, `maturin` |
| Backend             | Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (`AsyncSession`), `asyncpg`, `httpx`, Redis (`redis.asyncio`) |
| Base de datos       | PostgreSQL 16 + PostGIS 3.4 (+ pgRouting disponible) |
| Frontend            | React 19, TypeScript estricto, Vite, `maplibre-gl`, `@deck.gl/react`, `@deck.gl/layers`, `recharts`, TailwindCSS |

---

## 4. Estructura del repositorio

```
ahorro_rutas/
├── backend/
│   ├── app/
│   │   ├── api/routes.py                 # Endpoints REST
│   │   ├── connectors/                   # CNE, CONAGUA (clima/cierres), SESNSP
│   │   ├── schemas/routes.py             # Contratos Pydantic v2
│   │   ├── services/
│   │   │   ├── real_routing.py           # OSRM + Valhalla (geometría real)
│   │   │   ├── route_economy.py          # consumo físico, peaje y congestión
│   │   │   ├── pareto_selector.py        # selección de recomendaciones
│   │   │   └── multi_stop_vrp.py         # GTDVRPTW multiparada
│   │   ├── config.py · db.py · main.py
│   ├── requirements.txt
│   └── Dockerfile                        # Multi-stage con imagen maturin (sin apt)
├── database/
│   ├── init_db.sql                       # Esquema PostGIS
│   └── seeds/010_vehicle_profiles.sql    # 5 perfiles vehiculares
├── frontend/
│   └── src/
│       ├── components/                   # Navbar, MapViewer, TripConfigCard, Field,
│       │                                 # WeatherWindow, ComparisonSection,
│       │                                 # ChartsSection, DataAuditBadge
│       ├── pages/ContentPages.tsx        # Páginas de documentación/contexto
│       ├── RoutePlannerPage.tsx · App.tsx
│       ├── palette.ts · api.ts · types.ts · cities.ts
│       └── ...
├── rust_core/                            # Núcleo físico + bindings PyO3
├── simulation/                           # Conversión OSM→SUMO y validación
├── scripts/                              # ETL y utilidades
├── docker-compose.yml · .env.example · README.md
└── documentacion.md
```

---

## 5. Requisitos previos

- **Docker Desktop** con Compose (backend + PostGIS + Redis).
- **Node.js 20+** y **npm** (frontend).
- **Conexión a Internet** (OSRM/Valhalla públicos, clima Open-Meteo/SMN).
- Rust 1.99+ con `maturin` solo si se compila el núcleo fuera de Docker.

> **Nota (Windows):** sin *linker* de MSVC, compile y pruebe el núcleo Rust **dentro de
> Docker**. No use `apt-get` en los Dockerfiles: la imagen oficial de `maturin` resuelve
> el build de la extensión.

---

## 6. Configuración (.env)

| Variable | Descripción | Valor típico |
|----------|-------------|--------------|
| `POSTGRES_*` | Credenciales PostGIS | `ecoruta_user/…/ecoruta_db` |
| `API_PORT` | Puerto **host** del backend | `8010` (8000 suele estar ocupado) |
| `CORS_ORIGINS` | Orígenes permitidos | `["http://localhost:5173","http://127.0.0.1:5173"]` |
| `REDIS_URL` | URL de Redis | `redis://redis:6379/0` |
| `VITE_API_TARGET` | Destino del proxy de Vite | `http://localhost:8010` |
| `AIR_DENSITY_DEFAULT` | Densidad del aire (kg/m³) | `1.05` |
| `CACHE_TTL_SECONDS` | TTL de caché de optimización | `900` |

Las URLs de OSRM/Valhalla usan por defecto los servidores públicos
(`OSRM_PUBLIC_BASE`, `VALHALLA_PUBLIC_BASE` en `services/real_routing.py`).

---

## 7. Puesta en marcha

```powershell
# 1) Infraestructura
docker compose up -d postgres redis

# 2) Perfiles vehiculares (subcarpeta → carga manual)
docker cp "database/seeds/010_vehicle_profiles.sql" ecoruta_postgis:/tmp/010_vehicle_profiles.sql
docker exec ecoruta_postgis psql -U ecoruta_user -d ecoruta_db -v ON_ERROR_STOP=1 -f /tmp/010_vehicle_profiles.sql

# 3) Backend
docker compose --profile full up -d --build backend
curl http://localhost:8010/health

# 4) Frontend
cd frontend; npm install; npm run dev    # http://localhost:5173
```

---

## 8. Motor de rutas reales (OSRM + Valhalla)

`RealRoutingService` (`backend/app/services/real_routing.py`) obtiene geometrías reales
que **siguen las calles**:

- **OSRM** — mejor ruta + alternativas (`alternatives=true`), con `overview=full`,
  `geometries=geojson` y `annotations=distance,speed`. Las anotaciones permiten medir el
  **tramo rodado a velocidad de autopista** (≥ 80 km/h), usado para estimar el peaje.
- **Valhalla** — variantes por preferencia de costos que introducen los compromisos
  reales costo↔tiempo:
  - `valhalla_rapida` (mínima duración, puede usar peaje),
  - `valhalla_evitar_peajes` (`use_tolls: 0`),
  - `valhalla_evitar_autopistas` (`use_highways: 0`) → ruta libre, sin peaje, más lenta,
  - `valhalla_mas_corta` (`shortest: true`).
- Las polilíneas de Valhalla (precisión 1e-6) se decodifican con
  `decode_polyline6`.
- Si un proveedor falla, el sistema continúa con el otro; si ambos fallan, responde
  `502`.

Cada candidata se convierte en una `RealRoute` (distancia, duración base, geometría y
atributos de peaje) que alimenta el motor de costos.

---

## 9. Modelo de costos: combustible, peaje y congestión

`RouteEconomyService` (`route_economy.py`) evalúa cada ruta real:

1. **Combustible (modelo físico, núcleo Rust):**
   ```python
   ecoruta_core.compute_energy_units(distance_m, slope_rad=0, duration_s,
                                     congestion_accel=0, rain_mmh=0, vehicle, air_density)
   ```
   Devuelve **litros** (ICE) o **kWh** (EV). El costo es `unidades × precio_unitario`.
2. **Precio de la energía** (`FuelPriceService`): toma la **estación CNE más cercana**
   en PostGIS (KNN `<->`); si no hay dato, usa un **respaldo explícito**
   (`fallback_estimate`).
3. **Peaje estimado** (`TOLL_RATE_MXN_PER_KM`: 1.10 autos / 2.40 camión):
   - OSRM → se aplica al tramo medido a ≥ 80 km/h (proxy de autopista).
   - Valhalla → se aplica a toda la ruta si `summary.has_toll == true`; si no, 0.
   > ⚠️ Es una **estimación indicativa**, no la tarifa oficial de la RNC.
4. **Ajuste temporal por congestión** (`congestion_factor`):
   | Escenario | Factor |
   |-----------|--------|
   | Fin de semana | ×1.00 |
   | Entre semana, hora pico (7–9, 17–19) | ×1.30 |
   | Entre semana, fuera de pico | ×1.08 |
   | Modo robusto (P90) | ×1.15 adicional |

   `total_time_s = duración_base_OSRM/Valhalla × factor`.

---

## 10. Frente de Pareto y recomendaciones

`filter_non_dominated` descarta las soluciones dominadas (mayor costo **y** mayor
tiempo) y `ParetoPreferenceSelector` produce:

- **`cheapest`** — mínimo costo.
- **`fastest`** — mínimo tiempo.
- **`recommended_knee`** — punto de codo (mejor compromiso costo/tiempo).
- **`recommended_user`** — minimiza $C + \lambda T$ según tu disposición a pagar.

Ejemplo real (CDMX → Puebla, sedan, 08:00):

| Alternativa | Distancia | Tiempo (con congestión) | Costo | Peaje |
|-------------|-----------|--------------------------|-------|-------|
| Ruta libre (Valhalla, sin autopistas) | 133.5 km | 358.6 min | 99.2 MXN | 0.0 |
| Rápida (OSRM, con autopista) | 131.6 km | 157.8 min | 135.9 MXN | 25.4 |

---

## 11. Núcleo físico en Rust

Expuesto a Python vía **PyO3** (`import ecoruta_core`):

```python
ecoruta_core.VehicleParams(...)          # parámetros físicos del vehículo
ecoruta_core.compute_energy_units(length_m, slope_rad, travel_time_s,
                                  congestion_accel_ms2, rain_intensity_mmh,
                                  vehicle, air_density) -> float
ecoruta_core.regularize_fifo(...)        # Δτ/Δt ≥ -0.95
ecoruta_core.interpolate_fifo(...)       # tiempo de viaje a la hora de llegada
ecoruta_core.solve_td_mols(...)          # TD-MOLS (label setting multiobjetivo)
```

Ecuación longitudinal unificada:

```text
F = ½·ρ·Cd·A·v² + Crr·m·g·cos α + m·g·sin α + m·a
E = F·v·Δt ; unidades = E / densidad_energética · κ_vehículo
```

El motor **TD-MOLS** y la regularización **FIFO** siguen disponibles para operar sobre
un grafo propio (pgRouting) cuando se cargue la RNC; en el modo actual, el núcleo se usa
para el **modelo físico de consumo** sobre las geometrías reales.

---

## 12. Base de datos (PostgreSQL/PostGIS)

| Tabla | Uso actual |
|-------|------------|
| `vehicle_profiles` | 5 perfiles físicos usados por el modelo |
| `fuel_stations_cne` | Precios de combustible por estación (KNN) |
| `hazard_zones` | Avisos contextuales municipales/riesgo hídrico |
| `road_nodes`, `road_edges`, `edge_hourly_speeds` | Esquema del grafo propio (pgRouting); **no** requerido para el enrutamiento real actual |

El contexto se evalúa cruzando la **geometría real** de la ruta con `hazard_zones`
(`ST_Intersects`), sin micro-puntuaciones por calle.

---

## 13. API REST

Prefijo `/api/v1`. Toda respuesta incluye `data_provenance_audit`.

### `POST /api/v1/routes/optimize`
```json
{
  "origin_lat": 19.4326, "origin_lon": -99.1332,
  "dest_lat": 19.0414, "dest_lon": -98.2063,
  "departure_hour": 8, "day_type": "weekday",
  "vehicle_code": "sedan_compacto", "cargo_mass_kg": 150,
  "ac_enabled": true, "willingness_to_pay_mxn_per_min": 2.5,
  "use_robust_p90": false
}
```
Devuelve `optimization_result` (frente + recomendaciones), el bloque **`comparison`**
(ver §15) y la auditoría. Cada ruta incluye `coordinates` (geometría real),
`distance_km`, `baseline_duration_minutes`, `network_source` (`osrm`/`valhalla`),
`route_profile`, `toll_is_estimate` y `context_notices`.

> **Errores:** `502` si OSRM/Valhalla no responden; `404` si no hay frente factible.

### `POST /api/v1/routes/optimize-multistop`
Ruteo multiparada con ventanas de tiempo. Construye la matriz de costos/tiempos reales
por tramo y optimiza la secuencia (`ordered_waypoints`).

### `GET /api/v1/weather?lat=…&lon=…`
Clima actual (Open-Meteo/SMN); `fallback_estimate` si la fuente falla.

### `GET /api/v1/vehicles/profiles`
5 perfiles: `sedan_compacto`, `suv_mediana`, `pickup_diesel`, `truck_5_ejes`,
`ev_compacto`.

### `POST /api/v1/admin/sync-data`
Sincroniza conectores oficiales (CNE y cierres CONAGUA), auditado.

---

## 14. Frontend

SPA con navegación por estado (sin router).

- **`Navbar`** — Rutas · Documentación · Contexto · Antecedentes · Información general.
- **`RoutePlannerPage`** — pantalla principal.
- **`TripConfigCard`** — formulario **colapsable y guiado** (Ruta → Vehículo →
  Condiciones → Preferencias), con **tooltips** por campo vía `Field`. Al calcular se
  colapsa y muestra un resumen con botón **Editar**.
- **`MapViewer`** — mapa *maplibre-gl* (OpenFreeMap Liberty) + capas *deck.gl*; dibuja las
  **rutas reales** (la alternativa activa en trazo grueso y el resto atenuadas).
- **`WeatherWindow`** — tarjeta flotante sobre el mapa (abrir/cerrar).
- **`ComparisonSection`** — tabla EcoRuta vs. OSRM vs. Valhalla + botón
  **Ver en Google Maps** (ver §15).
- **`ChartsSection`** — debajo del mapa: tarjetas-resumen y gráficas *recharts* con
  **paleta de colores viva y consistente** (`palette.ts`): barras de costo, barras de
  tiempo y **dispersión del frente de Pareto** (cada punto es una ruta real). Al calcular,
  la vista hace *scroll* a esta sección.
- Paleta: preferencia `#2563eb`, equilibrada `#16a34a`, más barata `#7c3aed`, más rápida
  `#dc2626`, alternativas adicionales con colores rotativos.

---

## 15. Comparativa con Google Maps, OSRM y Valhalla

La respuesta incluye el bloque `comparison`:

| Motor | Distancia | Tiempo | Costo | Aporta |
|-------|-----------|--------|-------|--------|
| **EcoRuta (recomendada)** | real | con congestión | físico + peaje | Optimización multiobjetivo |
| **OSRM** (más rápida) | real | base | — | Geometría + duración |
| **Valhalla** (más rápida) | real | base | — | Geometría + duración |

Además se ofrece un **enlace “Abrir en Google Maps”** con el mismo origen/destino
(`https://www.google.com/maps/dir/?api=1&…&travelmode=driving`), sin API key.

---

## 16. Auditoría de procedencia de datos

| Dato | Fuente | Nota |
|------|--------|------|
| Red vial | OpenStreetMap (OSRM + Valhalla) | red real |
| Combustible | CNE (o respaldo explícito) | precio unitario |
| Peaje | Estimación por perfil de velocidad/peaje | **no** tarifa RNC |
| Clima | Open-Meteo / SMN | punto |
| Seguridad | SESNSP | **municipal, solo contexto** |
| Riesgo hídrico | CONAGUA (Atlas Nacional) | polígono |

Regla: si se usa un valor estimado se marca explícitamente
(`toll_is_estimate`, `status: "fallback_estimate"`). Nunca *mocks* silenciosos.

---

## 17. Verificación y pruebas

```powershell
# Núcleo Rust (Docker)
docker run --rm -v "${PWD}\rust_core:/app" -w /app rust:1.99 `
  cargo test --release --no-default-features

# Frontend (tipado estricto)
cd frontend; npm run build      # tsc --noEmit && vite build

# Humo del backend
curl http://localhost:8010/health
curl "http://localhost:8010/api/v1/vehicles/profiles"
curl -X POST http://localhost:8010/api/v1/routes/optimize -H "Content-Type: application/json" -d "{...}"
```

Verificado: núcleo Rust 6/6; `optimize` con rutas reales (miles de puntos por ruta),
frente de Pareto de 2–3 alternativas, `comparison`, `optimize-multistop`, `weather` y
`vehicles/profiles`.

---

## 18. Limitaciones y supuestos

- Depende de **servidores públicos** de OSRM/Valhalla (límites de uso/latencia); el
  diseño permite apuntar a instancias **autoalojadas**.
- **Peaje estimado**, no tarifa oficial (falta cargar la RNC).
- **Pendiente media = 0** (sin DEM cargado); la lluvia no se inyecta aún al modelo físico
  por ruta (el clima se muestra informativo).
- Solo **dos objetivos primarios** (costo y tiempo). La incertidumbre se modela con el
  **modo robusto (P90)**.
- Los conectores CNE/SAKBÉ/CONAGUA dependen de sus endpoints/tokens oficiales.

---

## 19. Reglas de ingeniería del proyecto

1. **Solo 2 objetivos primarios**: `[costo_mxn, tiempo_s]`.
2. **Nunca rendimiento estático**: el consumo usa el modelo físico (`compute_energy_units`).
3. **FIFO obligatorio** si se opera sobre una serie temporal de grafo propio.
4. **Extraer subgrafo** antes de buscar si se usa el grafo propio (evitar el grafo nacional).
5. **Riesgo delictivo solo municipal** (SESNSP): nunca puntuaciones por calle.
6. **Auditoría obligatoria** de procedencia en cada respuesta JSON.

---

_EcoRuta — documento técnico. Red vial real vía OSRM + Valhalla (OpenStreetMap)._
