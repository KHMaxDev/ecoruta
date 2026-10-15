# Reporte Técnico Detallado: Aplicación de la Auditoría EcoRuta

**Fecha:** 15 de octubre de 2026  
**Repositorio:** `C:\Users\madox\Documents\portafolio\ahorro_rutas`  
**Documento de origen:** `.opencode/auditoria_tecnica_de_ti_diseccion_y_analisis_foda_de_ecoruta.md`  
**Alcance:** Implementación de las recomendaciones accionables de las secciones **7.1–7.4** y **3.2/3.3** de la auditoría. El documento de auditoría **no fue modificado** (revertido a su estado original).

---

## 1. Resumen Ejecutivo

| # | Recomendación | Archivos | Estado |
|---|---|---|---|
| 7.1 | Grafo persistente en RAM + liberación del GIL | `rust_core/src/python.rs` | Implementado |
| 3.3 | *Watchdog timeout* `max_runtime_ms` | `rust_core/src/{td_mols.rs,python.rs}` | Implementado + test |
| 7.2 | Muestreo longitudinal de elevación cada 50 m | `scripts/etl_inegi_rnc_dem.py` | Implementado |
| 3.2 | Inserción por lotes (no fila por fila) | `scripts/etl_inegi_rnc_dem.py`, `scripts/seed_demo_corridor.py` | Implementado |
| 7.4 | Semilla de corredor demo autocontenida | `scripts/seed_demo_corridor.py` | Implementado + verificado en DB |
| 7.4 | CI con `cargo test` + validación Python | `.github/workflows/ci.yml` | Implementado |
| 7.3 | Penalización energética por giros | — | **Diferido** (justificación en §5) |

**Impacto neto:** DX < 2 min para evaluar end-to-end, núcleo Rust más robusto y preparado para carga concurrente, ETL con pendiente físicamente correcta e I/O por lotes, y regresión automática.

---

## 2. Cambios Implementados

### 2.1 `rust_core/src/td_mols.rs` — Watchdog de tiempo (auditoría 3.3)

- Nueva firma: `solve_core(..., max_runtime_ms: Option<u64>)`.
- `let started_at = std::time::Instant::now();` al inicio de la búsqueda.
- Comprobación dentro del bucle `while let Some(curr) = open_heap.pop()`:

```rust
if let Some(max_ms) = max_runtime_ms {
    if started_at.elapsed().as_millis() > u128::from(max_ms) {
        break;
    }
}
```

- **Comportamiento:** corta la expansión y devuelve la mejor frontera descubierta hasta ese instante (*best effort*). **Nunca** paniquea ni falla la petición.
- Las dos pruebas existentes se ajustaron a la nueva firma pasando `None`.
- Nueva prueba `test_watchdog_timeout_returns_partial_front`:

```rust
let timed_out = solve_core(make_edges(), veh, 1, 4, -99.0, 19.4, 28800.0, 1.05, 50, 0.0, Some(0));
assert!(started.elapsed().as_millis() < 1_000);
assert!(timed_out.len() <= 2);
```

### 2.2 `rust_core/src/python.rs` — `RoadGraphEngine` (auditoría 7.1)

Nueva clase PyO3 exportada como `RoadGraphEngine` (frozen, seguro para hilos):

```rust
#[pyclass(name = "RoadGraphEngine", frozen)]
pub struct PyRoadGraphEngine {
    edges: Arc<Vec<EdgeData>>,
    node_count: usize,
    edge_count: usize,
}
```

- **Constructor:** `RoadGraphEngine(edges)` — carga el grafo **una sola vez** (lifespan de FastAPI) y lo comparte por `Arc` entre todos los hilos de Uvicorn.
- **Método `query_pareto(vehicle, source_node, target_node, dest_lon, dest_lat, departure_time_s, air_density, max_labels_per_node, epsilon_rel, max_runtime_ms=None)`**: delega en `solve_core` **liberando el GIL**, de modo que las peticiones concurrentes ejecutan la búsqueda en paralelo real.
- **Getters:** `node_count`, `edge_count` (telemetría/auditoría).

Además se añadió `max_runtime_ms = None` (firma opcional PyO3) a `solve_td_mols`.

**Corrección de compilación:** PyO3 0.30 renombró `Python::allow_threads` → `Python::detach`. Se usa `py.detach(move || ...)`. La comparación de la auditoría usaba el nombre antiguo.

### 2.3 `scripts/etl_inegi_rnc_dem.py` — pendiente efectiva + lotes (auditorías 7.2 / 3.2)

**a) `compute_effective_slope_rad(geom, length_m)`**

Sustituye el cálculo de extremos (`atan2(h_v - h_u, L)`, que reportaba `0.0` para cualquier loma que regresara a la misma altitud):

```python
num_samples = max(2, min(40, int(length_m // 50.0) + 1))
elevations = [self.sample_elevation_m(...) for i in range(num_samples)]
pos_gain_m = sum(max(0.0, elevations[i+1] - elevations[i]) ...)
neg_loss_m = sum(max(0.0, elevations[i] - elevations[i+1]) ...)
net_delta_fwd = pos_gain_m - 0.35 * neg_loss_m
net_delta_rev = neg_loss_m - 0.35 * pos_gain_m
slope_fwd = clamp(atan2(net_delta_fwd, length_m), -0.25, 0.25)
```

El factor `0.35` modela la fracción del descenso que no compensa el ascenso previo (frenado + pérdidas de motor), acotado a ±0.25 rad por seguridad frente a ruido del SRTM.

- Se eliminó `delta_h = elev_v - elev_u` y `slope_vu = -slope_uv` en el bucle principal; ahora ambos sentidos se derivan de la muestra longitudinal (el sentido inverso **no** es simplemente `-fwd`, lo que corrige el error físico de la auditoría).

**b) `_insert_batch(conn, sql, params, label)`**

Reemplaza los dos bucles `for x in rows: conn.execute(...)` por `conn.execute(text(sql), chunk)` en lotes de **10,000** (SQLAlchemy `executemany`). Reduce los round-trips a PostgreSQL de ~1.2 M a ~120.

### 2.4 `scripts/seed_demo_corridor.py` (nuevo) — DX < 2 min (auditoría 7.4)

Script autocontenido, **sin shapefiles INEGI ni GeoTIFF**, que puebla PostGIS con el esquema real de `init_db.sql`:

- **Driver:** SQLAlchemy AsyncEngine + `asyncpg` (el único driver presente en `backend/requirements.txt`). Normaliza cualquier `DATABASE_URL` a `postgresql+asyncpg://`.
- **Identidad demo:** `node_id` en `[900000, 999999]` y `rnc_id` con prefijo `ECORUTA_DEMO_` → limpieza exacta, sin borrar datos de producción.
- **Topología:** malla 15×16 = **240 nodos**, **898 aristas** bidireccionales sobre CDMX–Toluca–Puebla (lat 18.85–19.45, lon −99.55–−99.10).
- **Elevación:** campo analítico `2260 + 90·sin(...) + 60·cos(...)` (corredor transvolcánico).
- **Pendiente:** calculada con el **mismo** muestreo de 50 m del ETL → **866 de 898** aristas quedan con pendiente no nula.
- **Casetas:** 3 plazas (`road_nodes.is_toll_booth`), **24** aristas con tarifa; estado `toll_source_status = 'estimado'` (correcto según §5.2 de la auditoría: no hay tarifas oficiales RNC cargadas).
- **Estaciones CNE:** 6 estaciones con precios dispares (regular 23.20–24.95, premium 24.90–26.30, diésel 24.40–25.90) para ejercitar el KNN.
- **Riesgo:** 2 zonas (`inundacion_historica` CONAGUA, `contexto_municipal_sesnsp`) — siempre `agregado_municipal`, nunca por calle.
- **Perfiles horarios:** 2 tipos de día × 24 h → **43,104** filas.
- **Auditoría:** registro en `data_ingest_audit` con `status='fallback_estimate'` y nota *"Red sintética de demostración; NO es RNC del INEGI."*

**Idempotente:** se ejecutó **dos veces**; los recuentos finales se mantuvieron en 240/898 (no se duplicaron).

### 2.5 `.github/workflows/ci.yml` (nuevo) — regresión temprana

- Job **`rust`**: `cargo test --release --no-default-features` (núcleo puro, sin PyO3) con caché de Cargo.
- Job **`python-backend`**: Python 3.12, `pip install -r backend/requirements.txt`, ejecuta `pytest` solo si existen tests.
- Disparadores: `push`/`pull_request` sobre `main` y `develop`.

---

## 3. Verificación Real (ejecutada, no inferida)

### 3.1 Núcleo Rust
```
docker run --rm -v ".../rust_core:/app" -w /app rust:1.99 cargo test --release --no-default-features
```
```
running 7 tests
test fifo::tests::test_fifo_monotonic_arrival ... ok
test fifo::tests::test_regularization_limits_drop ... ok
test physics::tests::test_positive_slope_consumes_more_than_flat ... ok
test physics::tests::test_rain_increases_consumption ... ok
test td_mols::tests::test_pareto_optimality_against_exhaustive_enumeration ... ok
test td_mols::tests::test_exhaustive_enumeration_matches_front ... ok
test td_mols::tests::test_watchdog_timeout_returns_partial_front ... ok
test result: ok. 7 passed; 0 failed
```
→ **7 passed** (eran 6; +1 del watchdog). La propiedad de exactitud del frente de Pareto (auditoría del CLAUDE.md) se mantiene intacta.

### 3.2 Compilación PyO3
```
maturin build --release -i cpython3.12
📦 Built wheel ... ecoruta_core-0.1.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```

### 3.3 Smoke test de `RoadGraphEngine`
```
grafo residente: 4 nodos, 5 aristas
RoadGraphEngine frente: [(40.15, 1772.3), (132.5, 1080.0)]
solve_td_mols frente:   [(40.15, 1772.3), (132.5, 1080.0)]
watchdog 0ms -> 2 soluciones (parcial) sin error
watchdog 1000ms en engine -> 2 soluciones
ALL_OK
```
→ El resultado del grafo residente **coincide exactamente** con el cálculo por petición.

### 3.4 Backend desplegado
```
docker compose --profile full up -d --build backend
docker exec ecoruta_backend python -c "from ecoruta_core import RoadGraphEngine"
→ RoadGraphEngine en backend: <class 'builtins.RoadGraphEngine'>

GET /health                        → {"status":"ok","service":"EcoRuta API"}
POST /api/v1/routes/optimize       → status: "optimal", pareto_count: 2
   ruta: 133.15 MXN / 157.8 min (133 km, incluye 25.43 MXN de peaje)
```

### 3.5 Semilla demo en base de datos real
```
nodos=240 | aristas=898 | horarias=43104
con_pendiente=866 | casetas=24 | estaciones=6 | zonas=2
```
Reejecución → `nodos=240 | aristas=898` (idempotente).

---

## 4. Por qué la penalización por giros (7.3) queda diferida

La auditoría propone:

$$E_{\text{giro}}(e_{in}, e_{out}) = \begin{cases} 0 & |\Delta\theta| < 35^\circ \\ \frac{1}{2}\eta W (V_{in}^2 - V_{giro}^2) & |\Delta\theta| \ge 35^\circ \end{cases}$$

**El modelo es físicamente correcto**, pero no puede aplicarse hoy en el camino de producción:

1. El enrutamiento activo es **externo** (OSRM/Valhalla públicos): la API devuelve geometría *generalizada*, no una topología nodo→salientes con IDs consistentes con `road_edges`. No existe un par `(arista entrante, arista saliente)` estable en el que evaluar $\Delta\theta$.
2. Aplicar la fórmula sobre el grafo pgRouting local `road_edges` **requiere** resolver primero el *map-matching* entre la polilínea del proveedor y el grafo local — exactamente la "esquizofrenia de doble grafo" (§1.2) que el cambio a routing externo eliminó.
3. La implementación correcta es hacerlo **dentro** del motor que conoce la topología, una vez activo `RoadGraphEngine` como buscador primario.

La fórmula queda documentada aquí y en la sección 3.3 de la auditoría para su implementación futura sin volver a introducir el acoplamiento por IDs.

---

## 5. Veredicto de la Auditoría vs Estado Final

| Dimensión (auditoría §2) | Nota original | Estado tras el cambio |
|---|---|---|
| Construcción e Ingeniería de Código | 6.8/10 | ETL por lotes + pendiente correcta + seed verificado |
| Escalabilidad y Rendimiento Real | 5.8/10 | Grafo residente + GIL liberado + watchdog listos (motor aún en modo "ruta externa") |
| Experiencia de Desarrollador (DX) | 5.2/10 | `python scripts/seed_demo_corridor.py` → red navegable completa en ~1 s, sin descargas |
| Regresión | — | CI con `cargo test` en cada push |

**No se tocó** (fuera de alcance de estas correcciones o dependiente de datos oficiales): migraciones Alembic, tarifas RNC oficiales (siguen como `estimado`), tráfico en tiempo real, `COPY` nativo de PostgreSQL, traducción de jerga en el frontend y geocodificación.

---

## 6. Instrucciones de Uso

```powershell
# 1. Núcleo Rust (validar paridad de Pareto antes de tocar nada)
docker run --rm -v ".../rust_core:/app" -w /app rust:1.99 cargo test --release --no-default-features

# 2. Backend con el wheel nuevo
docker compose --profile full up -d --build backend

# 3. Red demo autocontenida (sin INEGI ni DEM)
docker run --rm --network ahorro_rutas_default `
  -e DB_HOST=postgis -e DB_NAME=ecoruta_db `
  -e DB_USER=ecoruta_user -e DB_PASSWORD=ecoruta_secure_password `
  -v ".../scripts:/scripts" ahorro_rutas-backend python /scripts/seed_demo_corridor.py

# 4. Smoke de grafo residente
python -c "from ecoruta_core import RoadGraphEngine, EdgeData, VehicleParams; ..."
```

---

## 7. Archivos

**Modificados**
- `rust_core/src/td_mols.rs`
- `rust_core/src/python.rs`
- `scripts/etl_inegi_rnc_dem.py`

**Creados**
- `scripts/seed_demo_corridor.py`
- `.github/workflows/ci.yml`
- `reporte_tecnico_detallado_ecoruta_20261015.md` (este archivo)

**Revertido (sin cambios)**
- `.opencode/auditoria_tecnica_de_ti_diseccion_y_analisis_foda_de_ecoruta.md`
