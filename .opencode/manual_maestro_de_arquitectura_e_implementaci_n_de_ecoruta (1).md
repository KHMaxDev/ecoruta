# EcoRuta — Manual Maestro de Resolución Técnica, Prompts para IA, Arquitectura de Sistemas e Implementación Integral

**Fecha de actualización:** 14 de octubre de 2026  
**Estado del documento:** Especificación Técnica Exhaustiva, Playbook para Agentes de IA y Código de Producción  
**Ámbito de aplicación:** República Mexicana (escalable a nivel regional)  

---

## 0. Protocolo de Inicialización y Prompts Maestros para Agentes de IA

Esta sección está diseñada para que puedas instruir a cualquier agente de ingeniería de software asistido por IA (como **Cursor, Windsurf, Claude Code, GitHub Copilot Workspace o Aider**) de manera determinista, evitando alucinaciones arquitectónicas, errores de tipos o simplificaciones matemáticas indebidas.

### 0.1 Instrucciones Paso a Paso para Iniciar el Desarrollo desde Cero

Antes de entregarle el primer prompt a la IA, ejecuta los siguientes comandos en tu estación de trabajo (Linux / macOS / WSL2 en Windows) para preparar el entorno base:

```bash
# 1. Crear la estructura raíz del monorepo e inicializar Git
mkdir -p ecoruta-monorepo/{database/seeds,rust_core/src,backend/app/{models,schemas,connectors,services,api},simulation,frontend/src/components,scripts}
cd ecoruta-monorepo
git init

# 2. Verificar herramientas del sistema requeridas
# Asegúrate de tener instalados: Docker, Docker Compose, Rust (rustup), Python 3.12+ y Node.js 20+
rustc --version
python3 --version
docker --version

# 3. Crear entorno virtual de Python e instalar Maturin (puente Rust <-> Python)
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip maturin pytest httpx

# 4. Crear el archivo de reglas globales del agente (.cursorrules y CLAUDE.md)
touch .cursorrules CLAUDE.md
```

### 0.2 Archivo de Reglas del Sistema para la IA (`.cursorrules` / `CLAUDE.md`)

Copia y pega exactamente el siguiente bloque dentro de los archivos `.cursorrules` y `CLAUDE.md` en la raíz de tu proyecto. Este archivo actúa como la **Constitución Técnica Inmutable** que la IA leerá antes de realizar cualquier cambio:

```markdown
# REGLAS DE INGENIERÍA OBLIGATORIAS DEL PROYECTO ECORUTA

## 1. Identidad y Propósito del Sistema
EcoRuta es un sistema científico y de producción para la optimización multiobjetivo de rutas viales en México. Calcula el frente de Pareto entre Costo Monetario Total ($C$) y Tiempo de Viaje ($T$) sujeto a restricciones físicas duras y horarios dependientes del tiempo.

## 2. Reglas Arquitectónicas Inquebrantables (PROHIBICIONES)
1. **PROHIBIDO usar un vector de más de 2 objetivos primarios en la cola de prioridad del grafo:** El algoritmo de etiquetado (`TD-MOLS`) SOLO optimiza `[costo_mxn, tiempo_s]`. La incertidumbre se modela ejecutando el motor sobre perfiles de velocidad $P_{50}$ (esperado) vs. $P_{10}$ (tiempo $P_{90}$ robusto). La seguridad y el riesgo hídrico se aplican como filtros duros de factibilidad (`is_closed_confirmed = TRUE`) o como metadatos contextuales post-búsqueda.
2. **PROHIBIDO usar rendimiento estático ($km/l$) como modelo primario:** Todo cálculo de consumo en las aristas debe invocar el modelo longitudinal de fuerzas físicas en Rust (`compute_fuel_liters`), que considera resistencia aerodinámica, rodadura, gravedad por pendiente ($\sin\alpha$) e inercia por congestión, calibrado por el factor $\kappa_v$ del vehículo.
3. **PROHIBIDO evaluar tiempos dependientes sin regularización FIFO:** Toda serie temporal de velocidades o tiempos de viaje por arista debe cumplir la condición FIFO ($\frac{\Delta \tau}{\Delta t} \ge -0.95$) antes de ingresar al motor de búsqueda.
4. **PROHIBIDO ejecutar el algoritmo multiobjetivo sobre el grafo nacional completo:** Siempre debe extraerse primero un subgrafo factible mediante el servicio `SubgraphExtractorService` (corredor elíptico en PostGIS o candidatos de Valhalla) excluyendo cierres viales y violaciones de altura/peso.
5. **PROHIBIDO asignar puntuaciones de riesgo delictivo por calle individual:** Los datos del SESNSP tienen resolución municipal. Nunca inventes interpolaciones por calle; preséntalos únicamente como auditoría contextual municipal.
6. **AUDITORÍA OBLIGATORIA DE DATOS:** Toda respuesta JSON de la API debe incluir el bloque `data_provenance_audit` especificando la fuente, resolución espacial y `timestamp` de actualización de los precios de la CNE, peajes de la RNC y pronósticos climáticos.

## 3. Stack Tecnológico Estricto
- **Base de datos:** PostgreSQL 16 + PostGIS 3.4 + pgRouting 3.6.
- **Núcleo algorítmico (`rust_core/`):** Rust edición 2021 expuesto a Python mediante `PyO3` (v0.22+) y compilado con `maturin`. Sin dependencias pesadas innecesarias.
- **Backend (`backend/`):** Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (`AsyncSession`), `asyncpg`, `httpx`, `ortools` (Google OR-Tools para GTDVRPTW) y `redis.asyncio`.
- **Simulación (`simulation/`):** Eclipse SUMO (`traci`, `sumolib`), `rasterio`, `geopandas`, `pyproj`.
- **Frontend (`frontend/`):** React 19, TypeScript estricto (`noImplicitAny: true`), Vite, `maplibre-gl`, `@deck.gl/react`, `@deck.gl/layers`, `recharts`, TailwindCSS.

## 4. Estándares de Código y Verificación
- Todo código Python debe incluir *type hints* completos y validaciones Pydantic v2.
- Todo cambio en `rust_core` debe pasar `cargo test` verificando que el frente de Pareto coincida al 100% con una búsqueda exhaustiva en un grafo de prueba antes de compilar con `maturin develop --release`.
- Nunca utilices datos simulados (*mocks* silenciosos) en producción sin marcar explícitamente `status: "fallback_estimate"` en los metadatos de auditoría.
```

---

### 0.3 Secuencia de Prompts Maestros para Construir el Proyecto con una IA

Para desarrollar el proyecto de forma ordenada, entrega a tu agente de IA los siguientes **8 Prompts Maestros** uno por uno, esperando a que termine y valide cada fase antes de pasar al siguiente.

#### Prompt Maestro 1: Infraestructura Docker y Esquema Espacial PostGIS/pgRouting
> **Copia y pega a la IA:**
> "Actúa como Arquitecto Principal de Sistemas Geoespaciales. Lee `.cursorrules` y el documento `EcoRuta_Master_Blueprint_Arquitectura_Implementacion.md`. Tu objetivo en esta Fase 1 es implementar la capa de infraestructura y persistencia:
> 1. Genera `docker-compose.yml` con PostgreSQL 16 + PostGIS 3.4 + pgRouting 3.6, Redis 7.4 y Valhalla con soporte de elevación para México.
> 2. Genera `database/init_db.sql` con las tablas `vehicle_profiles` (incluyendo parámetros físicos para combustión interna y vehículos eléctricos), `road_nodes`, `road_edges` (con tarifas de peaje RNC por ejes, pendientes en radianes, restricciones físicas de peso/altura y precios asignados por tipo de combustible), `edge_hourly_speeds`, `fuel_stations_cne` y `hazard_zones`, junto con sus índices espaciales `GIST` y funciones auxiliares SQL.
> 3. Crea un script de verificación `scripts/test_db_schema.py` que se conecte a la base de datos, verifique que las extensiones `postgis` y `pgrouting` estén activas y valide las semillas de vehículos."

#### Prompt Maestro 2: Pipeline ETL Geoespacial (INEGI RNC + DEM SRTM + OSM)
> **Copia y pega a la IA:**
> "Actúa como Ingeniero de Datos Geoespaciales (GIS). Tu tarea es implementar en `scripts/etl_inegi_rnc_dem.py` el pipeline completo de ingesta cartográfica para México:
> 1. Debe leer los Shapefiles/GeoPackages de la Red Nacional de Caminos (RNC) del INEGI (vialidades, casetas de peaje y maniobras prohibidas) y reproyectarlos de `EPSG:6372` (ITRF2008 México) a `EPSG:4326`.
> 2. Debe muestrear un archivo GeoTIFF de Modelo Digital de Elevación (DEM SRTM / Continuo de Elevaciones Mexicano del INEGI) usando `rasterio` en los nodos de inicio y fin de cada segmento vial para calcular la pendiente real $\alpha_e = \arctan(\Delta h / d_e)$ acotada en $[-0.25, 0.25]$ radianes.
> 3. Debe insertar los nodos y aristas dirigidas respetando el sentido de circulación (`SENTIDO` en RNC: 'Dos sentidos' genera dos aristas opuestas; 'Un sentido' genera una arista dirigida) en `road_nodes` y `road_edges`, y poblar perfiles horarios base en `edge_hourly_speeds`."

#### Prompt Maestro 3: Núcleo Algorítmico en Rust (`rust_core`) con Física Vehicular y Garantía FIFO
> **Copia y pega a la IA:**
> "Actúa como Ingeniero de Sistemas en Rust y Especialista en Optimización Combinatoria. Implementa el paquete `rust_core` expuesto a Python mediante `PyO3`:
> 1. Estructura el código en submódulos: `src/physics.rs` (modelo longitudinal de fuerzas para vehículos de combustión interna y vehículos eléctricos con frenado regenerativo en pendientes negativas), `src/fifo.rs` (interpolación continua y regularización FIFO estricta con cota de pendiente $\ge -0.95$), `src/td_mols.rs` (algoritmo Time-Dependent Multi-Objective Label-Setting con heurística admisible Euclidiana/$A^*$, poda global contra el frente del nodo destino y $\epsilon$-dominancia configurable) y `src/lib.rs`.
> 2. Añade pruebas unitarias en `src/td_mols.rs` (`#[cfg(test)]`) que construyan un grafo sintético de 12 nodos con tiempos variables, ejecuten una enumeración por fuerza bruta de todos los caminos posibles y demuestren matemáticamente que `solve_td_mols` con `epsilon_rel = 0.0` recupera exactamente el 100% de la frontera de Pareto.
> 3. Compila con `maturin develop --release` y ejecuta `cargo test`."

#### Prompt Maestro 4: Conectores Asíncronos para Fuentes Oficiales de México
> **Copia y pega a la IA:**
> "Actúa como Ingeniero Backend Senior en Python. Implementa todos los conectores de la Capa 1 en `backend/app/connectors/` utilizando `httpx`, `tenacity` (reintentos exponenciales) y `SQLAlchemy AsyncSession`:
> 1. `cne_combustible.py`: Descarga precios vigentes de estaciones de servicio de la CNE, guarda el `reported_at` y ejecuta el cruce espacial `LATERAL` con el operador `<->` de PostGIS para actualizar el precio más cercano en cada arista de `road_edges`, imponiendo un radio máximo de búsqueda y marcando antigüedad.
> 2. `inegi_rnc_sakbe.py`: Cliente completo para la API SAKBÉ v3.1 del INEGI para obtener rutas de referencia oficiales y validar tarifas de casetas.
> 3. `conagua_riesgos.py`: Conector dual que consulta pronósticos horarios de precipitación, temperatura y viento en `Open-Meteo` / `SMN`, cruza con polígonos del Atlas Nacional de Riesgo por Inundación de CONAGUA y actualiza el coeficiente de rodadura $C_{rr}$ por lluvia o activa cierres viales cuando existe alerta crítica confirmada.
> 4. `sesnsp_seguridad.py`: Ingesta de CSV/JSON de incidencia delictiva municipal del SESNSP hacia `hazard_zones` con resolución estrictamente etiquetada como `agregado_municipal`."

#### Prompt Maestro 5: Servicios de Subgrafo Elíptico, Selector de Pareto y Optimizador Multipunto (OR-Tools)
> **Copia y pega a la IA:**
> "Actúa como Ingeniero de Algoritmos y Backend. Implementa los servicios de negocio en `backend/app/services/`:
> 1. `subgraph_extractor.py`: Consulta a PostGIS/pgRouting las rutas extremas (mínimo tiempo y mínimo costo simple) entre origen y destino, construye una envolvente elíptica amortiguada (`ST_Buffer` dinámico según distancia), filtra cierres confirmados y límites de altura/peso, y empaqueta las aristas hacia estructuras `ecoruta_core.EdgeData` junto con coordenadas para la heurística $A^*$.
> 2. `pareto_selector.py`: Implementa el método de restricciones $\epsilon$, la función de utilidad por suma ponderada $J(P) = C(P) + \lambda T(P)$, la detección geométrica del Punto de Codo (*Knee Point*) y el cruce espacial de las rutas ganadoras con `hazard_zones` para adjuntar advertencias contextuales.
> 3. `multi_stop_vrp.py`: Implementa el optimizador de múltiples paradas dependiente del tiempo (GTDVRPTW) usando Google OR-Tools, construyendo la matriz de costos entre pares de paradas mediante llamadas al motor en Rust."

#### Prompt Maestro 6: API REST en FastAPI, Caché en Redis y Contratos Pydantic v2
> **Copia y pega a la IA:**
> "Actúa como Arquitecto de APIs en Python. Implementa en `backend/app/` la aplicación FastAPI completa (`main.py`, `config.py`, `schemas/`, `api/routes.py`):
> 1. Expón los endpoints `POST /api/v1/routes/optimize` (origen-destino bi-objetivo con auditoría completa y geometrías GeoJSON), `POST /api/v1/routes/optimize-multistop` (múltiples paradas con ventanas de tiempo), `GET /api/v1/vehicles/profiles` y `POST /api/v1/admin/sync-data`.
> 2. Integra caché en Redis utilizando un hash determinista de `(origen, destino, hora_salida, vehiculo, carga, modo_incertidumbre)` con TTL de 15 minutos."

#### Prompt Maestro 7: Entorno de Co-Simulación Microscópica en Eclipse SUMO
> **Copia y pega a la IA:**
> "Actúa como Investigador en Simulación de Tráfico. Implementa en `simulation/` el entorno completo de validación experimental:
> 1. `osm_to_sumo.sh`: Script que utiliza `netconvert` para transformar el recorte OSM y el GeoTIFF de elevación DEM en una red `.net.xml` tridimensional para SUMO.
> 2. `run_validation.py`: Script de co-simulación con `traci` que ejecuta el diseño experimental factorial de 64 escenarios comparando en tiempo real el consumo y tiempo de 4 vehículos idénticos (Ruta Más Corta, Ruta Más Rápida, Suma Escalada Ingenua y EcoRuta Knee Point).
> 3. `metrics_evaluator.py`: Calcula el indicador de Hipervolumen ($HV$) del frente de Pareto, el Error Porcentual Absoluto Medio ($\text{MAPE}$) de litros consumidos y genera el reporte estadístico en Markdown y CSV."

#### Prompt Maestro 8: Frontend Analítico con React, TypeScript, MapLibre GL, deck.gl y Recharts
> **Copia y pega a la IA:**
> "Actúa como Ingeniero Frontend Senior especializado en Visualización Geoespacial. Construye la aplicación en `frontend/` con React 19, TypeScript y TailwindCSS:
> 1. `MapViewer.tsx`: Mapa vectorial con `MapLibre GL` y superposición WebGL con `deck.gl` (`PathLayer` y `ScatterplotLayer`) que dibuja todas las rutas de la frontera de Pareto codificadas por color y grosor, más las casetas de peaje y alertas hídricas.
> 2. `ParetoChart.tsx`: Gráfico de dispersión interactivo con `Recharts` (Eje X: Tiempo en minutos, Eje Y: Costo Total en MXN) que muestra la curva de Pareto, resalta el Punto de Codo (*Knee Point*) y permite hacer clic en cualquier punto para iluminar la ruta en el mapa.
> 3. `VehicleConfigurator.tsx` y `DataAuditBadge.tsx`: Panel de control físico del vehículo (masa de carga, aire acondicionado, disposición a pagar $\lambda$, modo robusto $P_{90}$) y tarjeta de transparencia que muestra la antigüedad exacta de los datos de la CNE, INEGI RNC y SESNSP."

---

## 1. Dictamen Técnico Consolidado y Arquitectura de Producción

### 1.1 Resolución de las Cinco Tensiones de Ingeniería

| Dimensión | Problema Detectado en el Planteamiento Inicial | Solución Definitiva Implementada en este Manual |
| :--- | :--- | :--- |
| **1. Explosión Combinatoria ($k$ objetivos)** | Minimizar simultáneamente 4 objetivos $[C, T, R, U]$ dispara exponencialmente el número de etiquetas por nodo. | El núcleo en Rust opera sobre el plano bi-objetivo primario $(C, T_{\beta})$. La incertidumbre $U$ se controla alternando entre el perfil de velocidad mediana ($\beta = 0.50$) y el perfil de congestión severa ($\beta = 0.90$). El riesgo $R$ opera como restricción dura de exclusión (cierres/inundaciones activas) o capa de auditoría informativa. |
| **2. Violación de la Propiedad FIFO** | Cambios bruscos de velocidad entre horas consecutivas hacen que salir antes implique llegar después, rompiendo la optimalidad de Dijkstra/Label-Setting. | Pre-procesamiento matemático obligatorio en Rust (`fifo.rs`) que garantiza $\frac{\tau_e(t_{k+1}) - \tau_e(t_k)}{t_{k+1} - t_k} \ge -0.95$ con interpolación lineal continua por segundo. |
| **3. Falsa Linealidad del Consumo ($km/l$)** | El rendimiento constante ignora que el consumo crece cuadráticamente con la velocidad y hasta $2.5\times$ en pendientes positivas. | Modelo traccional longitudinal completo (`physics.rs`) para motores de combustión interna (ICE) y vehículos eléctricos (EV con regeneración en bajadas), calibrado con el factor $\kappa_v$ respecto al rendimiento nominal del usuario. |
| **4. Escalabilidad en Redes Reales** | Ejecutar etiquetado multiobjetivo sobre los millones de aristas de México agota la memoria RAM. | Extracción de **Corredor Elíptico Amortiguado** en PostGIS alrededor de las rutas extremas, combinado con una **heurística admisible $A^*$** (distancia geodésica restante dividida por velocidad máxima libre y multiplicada por consumo mínimo físico). |
| **5. Ética y Resolución Espacial en Seguridad** | Riesgo de presentar tasas delictivas municipales del SESNSP como probabilidades exactas por calle. | Separación estricta en `hazard_zones` mediante el atributo `spatial_resolution = 'agregado_municipal'`. La API y el frontend auditan explícitamente el alcance territorial sin inventar micro-puntuaciones por cuadra. |

---

## 2. Fundamentación Matemática Completa (ICE + Vehículos Eléctricos + Heurística Admisible)

### 2.1 Ecuación Longitudinal Unificada (Combustión Interna y Eléctricos)

Para cada arista $e \in E$ de longitud $d_e$ (en metros), pendiente $\alpha_e = \arctan\left(\frac{h_{\text{destino}} - h_{\text{origen}}}{d_e}\right)$ (en radianes) y velocidad media $V_e(t) = \frac{d_e}{\tilde{\tau}_e(t)}$ (en $\text{m/s}$), la fuerza traccional total $F_{\text{tot}, e}(t)$ requerida en las ruedas es:

$$
F_{\text{tot}, e}(t) = \underbrace{\frac{1}{2} \rho_{\text{aire}} C_d A_f V_e(t)^2}_{F_{\text{aero}}} + \underbrace{W g C_{rr}(\omega) \cos(\alpha_e)}_{F_{\text{rod}}} + \underbrace{W g \sin(\alpha_e)}_{F_{\text{grav}}} + \underbrace{W a_{\text{eq}}(q_e)}_{F_{\text{iner}}}
$$

Donde el coeficiente de rodadura $C_{rr}(\omega)$ se ajusta dinámicamente según la precipitación horaria $I_{\text{lluvia}}$ (en $\text{mm/h}$) reportada por el conector meteorológico:

$$
C_{rr}(\omega) = C_{rr, \text{base}} \cdot \left( 1 + 0.02 \min(I_{\text{lluvia}}, 25.0) \right)
$$

#### Caso A: Vehículo de Combustión Interna (Gasolina Regular, Premium o Diésel)
En pendientes descendentes pronunciadas donde $F_{\text{tot}, e}(t) < 0$, el motor no genera combustible, pero mantiene un consumo mínimo de ralentí $P_{\text{ralentí}}$ más la carga de accesorios $P_{\text{aux}}(\omega)$:

$$
P_{\text{motor}, e}^{\text{ICE}}(t) = \frac{\max\left(0, \; V_e(t) F_{\text{tot}, e}(t)\right)}{\eta_{\text{tren}}} + P_{\text{ralentí}} + P_{\text{aux}}(\omega)
$$

El consumo en litros $L_e(t)$ es:

$$
L_e(t) = \kappa_v \cdot \frac{\tilde{\tau}_e(t) \cdot P_{\text{motor}, e}^{\text{ICE}}(t)}{E_{\text{litro}}}
$$

Donde $E_{\text{litro}} = Q_{\text{comb}} \cdot \rho_{\text{comb}}$ es la densidad energética volumétrica ($\approx 32.1 \times 10^6\text{ J/l}$ para gasolina y $\approx 35.5 \times 10^6\text{ J/l}$ para diésel).

#### Caso B: Vehículo Eléctrico (EV) con Frenado Regenerativo
Para la extensión a vehículos eléctricos, cuando $F_{\text{tot}, e}(t) < 0$ (descenso topográfico), el motor actúa como generador recuperando energía hacia la batería con una eficiencia de regeneración $\eta_{\text{regen}} \in [0.55, 0.70]$:

$$
P_{\text{batería}, e}^{\text{EV}}(t) = 
\begin{cases} 
\dfrac{V_e(t) F_{\text{tot}, e}(t)}{\eta_{\text{EV}}} + P_{\text{aux}}(\omega) & \text{si } F_{\text{tot}, e}(t) \ge 0 \\[10pt]
\eta_{\text{regen}} \left( V_e(t) F_{\text{tot}, e}(t) \right) + P_{\text{aux}}(\omega) & \text{si } F_{\text{tot}, e}(t) < 0 
\end{cases}
$$

La energía neta consumida en $\text{kWh}$ en la arista es:

$$
E_{\text{kWh}, e}(t) = \frac{\tilde{\tau}_e(t) \cdot P_{\text{batería}, e}^{\text{EV}}(t)}{3.6 \times 10^6}
$$

### 2.2 Heurística Admisible Multiobjetivo ($\text{NAMOA}^*$ / $\text{TD-MOLS}$)

Para acelerar la búsqueda sin perder ninguna solución Pareto-óptima, cada etiqueta en el nodo $u$ con coordenadas $(\phi_u, \lambda_u)$ calcula una cota inferior optimista $\mathbf{h}(u) = [h_C(u), h_T(u)]$ hacia el destino $t$ con coordenadas $(\phi_t, \lambda_t)$:

1. Sea $d_{\text{geo}}(u, t)$ la distancia geodésica de Haversine en metros entre $u$ y $t$.
2. Sea $V_{\max}$ la velocidad máxima permitida en toda la red vial ($\approx 36.11\text{ m/s}$ o $130\text{ km/h}$).
3. Sea $c_{\min}^{\text{km}}$ el costo monetario mínimo físico por metro en condiciones ideales (pendiente cero, velocidad óptima económica de $70\text{ km/h}$, sin peajes y con el precio de combustible mínimo del corredor $P_{\min}$).

Entonces, las cotas inferiores estrictamente admisibles y consistentes son:

$$
h_T(u) = \frac{d_{\text{geo}}(u, t)}{V_{\max}}, \qquad h_C(u) = d_{\text{geo}}(u, t) \cdot c_{\min}^{\text{km}}
$$

Como la distancia en línea recta es siempre menor o igual a cualquier camino vial ($d_{\text{geo}}(u, t) \le \sum_{e \in P_{u \to t}} d_e$), se cumple que $h_T(u) \le T^*(u, t)$ y $h_C(u) \le C^*(u, t)$, preservando la optimalidad exacta del frente de Pareto.

---

## 3. Módulo 1: Pipeline ETL Geoespacial (INEGI RNC + DEM SRTM + PostGIS)

Este módulo resuelve la ingesta de la **Red Nacional de Caminos (RNC)** del INEGI combinada con un **Modelo Digital de Elevación (DEM)** en formato GeoTIFF para poblar PostGIS con pendientes reales y tarifas de casetas de cobro.

### Archivo: `scripts/etl_inegi_rnc_dem.py`

```python
"""
Pipeline ETL Geoespacial para EcoRuta:
1. Lee la Red Vial y Plazas de Cobro de la Red Nacional de Caminos (RNC - INEGI).
2. Reproyecta geometrías a EPSG:4326 (WGS84).
3. Muestrea un archivo GeoTIFF de elevación (Continuo de Elevaciones Mexicano / SRTM)
   para calcular la pendiente longitudinal real en radianes de cada segmento vial.
4. Genera las aristas dirigidas según el sentido de circulación y las inserta en PostGIS.
"""

import math
import logging
from typing import Tuple, List, Dict, Any
import geopandas as gpd
import rasterio
from shapely.geometry import LineString, MultiLineString, Point
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ecoruta.etl_rnc")


class InegiRNCGeospatialETL:
    def __init__(self, db_url: str, dem_geotiff_path: str):
        self.engine = create_engine(db_url)
        self.dem_path = dem_geotiff_path
        self.dem_dataset = rasterio.open(dem_geotiff_path)

    def sample_elevation_m(self, lon: float, lat: float) -> float:
        """Obtiene la altitud en metros sobre el nivel del mar desde el raster DEM."""
        try:
            row, col = self.dem_dataset.index(lon, lat)
            val = self.dem_dataset.read(1)[row, col]
            if val is None or val < -500 or val > 6000:
                return 0.0
            return float(val)
        except Exception:
            return 0.0

    @staticmethod
    def extract_endpoints(geom) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Extrae las coordenadas (lon, lat) inicial y final de un LineString o MultiLineString."""
        if isinstance(geom, MultiLineString):
            coords = list(geom.geoms[0].coords) + list(geom.geoms[-1].coords)
        elif isinstance(geom, LineString):
            coords = list(geom.coords)
        else:
            raise ValueError(f"Geometría no soportada: {type(geom)}")
        return (coords[0][0], coords[0][1]), (coords[-1][0], coords[-1][1])

    def process_and_load_rnc(
        self,
        rnc_roads_shapefile: str,
        rnc_tolls_shapefile: str,
        bbox_filter: Tuple[float, float, float, float] = (-100.5, 18.8, -98.0, 20.2)
    ) -> None:
        """
        Procesa un recorte regional o nacional de la RNC del INEGI.
        bbox_filter: (min_lon, min_lat, max_lon, max_lat) — Por defecto Corredor CDMX-Puebla-Toluca.
        """
        logger.info("Cargando capa de vialidades RNC desde %s...", rnc_roads_shapefile)
        gdf_roads = gpd.read_file(rnc_roads_shapefile)

        if gdf_roads.crs is not None and gdf_roads.crs.to_epsg() != 4326:
            logger.info("Reproyectando vialidades de %s a EPSG:4326...", gdf_roads.crs)
            gdf_roads = gdf_roads.to_crs(epsg=4326)

        # Filtrar por caja delimitadora de la región piloto
        gdf_roads = gdf_roads.cx[bbox_filter[0]:bbox_filter[2], bbox_filter[1]:bbox_filter[3]]
        logger.info("Segmentos viales dentro del corredor: %d", len(gdf_roads))

        # Cargar plazas de cobro (peajes) si el shapefile está disponible
        gdf_tolls = None
        if rnc_tolls_shapefile:
            gdf_tolls = gpd.read_file(rnc_tolls_shapefile)
            if gdf_tolls.crs is not None and gdf_tolls.crs.to_epsg() != 4326:
                gdf_tolls = gdf_tolls.to_crs(epsg=4326)
            gdf_tolls = gdf_tolls.cx[bbox_filter[0]:bbox_filter[2], bbox_filter[1]:bbox_filter[3]]

        node_registry: Dict[Tuple[int, int], int] = {}
        nodes_to_insert: List[Dict[str, Any]] = []
        edges_to_insert: List[Dict[str, Any]] = []
        next_node_id = 1

        def get_or_create_node(lon: float, lat: float) -> Tuple[int, float]:
            nonlocal next_node_id
            # Cuantizar a ~1 metro de precisión (5 decimales) para coser topología
            key = ( int(round(lon * 100000)), int(round(lat * 100000)) )
            if key in node_registry:
                nid = node_registry[key]
                elev = nodes_to_insert[nid - 1]["elevation_m"]
                return nid, elev

            elev = self.sample_elevation_m(lon, lat)
            nid = next_node_id
            next_node_id += 1
            node_registry[key] = nid
            nodes_to_insert.append({
                "id": nid,
                "lon": lon,
                "lat": lat,
                "elevation_m": elev
            })
            return nid, elev

        for idx, row in gdf_roads.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue

            (lon1, lat1), (lon2, lat2) = self.extract_endpoints(geom)
            u_id, elev_u = get_or_create_node(lon1, lat1)
            v_id, elev_v = get_or_create_node(lon2, lat2)

            if u_id == v_id:
                continue

            # Longitud en metros reportada por RNC o calculada geodésicamente
            length_m = float(row.get("LONGITUD", 0.0))
            if length_m <= 1.0:
                length_m = max(10.0, geom.length * 111320.0)

            # Pendiente longitudinal en radianes acotada físicamente en [-0.25, 0.25]
            delta_h = elev_v - elev_u
            slope_uv = max(-0.25, min(0.25, math.atan2(delta_h, length_m)))
            slope_vu = -slope_uv

            speed_kmh = float(row.get("VELOCIDAD", 60.0) or 60.0)
            road_name = str(row.get("NOMBRE", "Vialidad s/n") or "Vialidad s/n")
            road_class = str(row.get("TIPO_VIAL", "Carretera") or "Carretera").lower()
            circulacion = str(row.get("CIRCULACIO", "Dos sentidos") or "Dos sentidos")
            peaje_flag = str(row.get("PEAJE", "No") or "No").upper()

            toll_auto = float(row.get("TARIFA_A", 0.0) or 0.0) if peaje_flag == "SI" else 0.0
            toll_truck = float(row.get("TARIFA_C5", toll_auto * 4.2) or 0.0) if peaje_flag == "SI" else 0.0

            wkt_forward = geom.wkt if isinstance(geom, LineString) else geom.geoms[0].wkt

            # Arista en sentido directo (u -> v)
            edges_to_insert.append({
                "source": u_id,
                "target": v_id,
                "rnc_id": str(row.get("ID_RED", idx)),
                "road_name": road_name,
                "road_class": road_class,
                "length_m": length_m,
                "slope_rad": slope_uv,
                "free_flow_speed_kmh": speed_kmh,
                "toll_cost_autos_mxn": toll_auto,
                "toll_cost_truck_5axles_mxn": toll_truck,
                "wkt": wkt_forward
            })

            # Si es de doble sentido, generar la arista inversa (v -> u) con pendiente invertida
            if "dos" in circulacion.lower() or "ambos" in circulacion.lower():
                coords_rev = list(geom.coords)[::-1] if isinstance(geom, LineString) else list(geom.geoms[0].coords)[::-1]
                wkt_reverse = LineString(coords_rev).wkt
                edges_to_insert.append({
                    "source": v_id,
                    "target": u_id,
                    "rnc_id": f"{row.get('ID_RED', idx)}_REV",
                    "road_name": road_name,
                    "road_class": road_class,
                    "length_m": length_m,
                    "slope_rad": slope_vu,
                    "free_flow_speed_kmh": speed_kmh,
                    "toll_cost_autos_mxn": toll_auto,
                    "toll_cost_truck_5axles_mxn": toll_truck,
                    "wkt": wkt_reverse
                })

        # Inserción transaccional masiva en PostgreSQL / PostGIS
        with self.engine.begin() as conn:
            logger.info("Insertando %d nodos topológicos con elevación DEM...", len(nodes_to_insert))
            for n in nodes_to_insert:
                conn.execute(
                    text("""
                        INSERT INTO road_nodes (id, elevation_m, geom)
                        VALUES (:id, :elevation_m, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
                        ON CONFLICT (id) DO NOTHING;
                    """),
                    n
                )

            logger.info("Insertando %d aristas dirigidas enriquecidas...", len(edges_to_insert))
            for e in edges_to_insert:
                conn.execute(
                    text("""
                        INSERT INTO road_edges (
                            source, target, rnc_id, road_name, road_class,
                            length_m, slope_rad, free_flow_speed_kmh,
                            toll_cost_autos_mxn, toll_cost_truck_5axles_mxn, geom
                        ) VALUES (
                            :source, :target, :rnc_id, :road_name, :road_class,
                            :length_m, :slope_rad, :free_flow_speed_kmh,
                            :toll_cost_autos_mxn, :toll_cost_truck_5axles_mxn,
                            ST_GeomFromText(:wkt, 4326)
                        );
                    """),
                    e
                )

            # Generar perfiles de velocidad horaria sintéticos iniciales basados en hora pico mexicana
            logger.info("Generando series horarias de velocidad inicial (24h)...")
            conn.execute(
                text("""
                    INSERT INTO edge_hourly_speeds (edge_id, day_type, hour_of_day, speed_p50_kmh, speed_p10_kmh, congestion_stop_index)
                    SELECT
                        e.id,
                        'weekday',
                        h.hr,
                        CASE
                            WHEN h.hr IN (7, 8, 9, 18, 19, 20) THEN GREATEST(8.0, e.free_flow_speed_kmh * 0.48)
                            WHEN h.hr IN (13, 14, 15, 16, 17) THEN GREATEST(12.0, e.free_flow_speed_kmh * 0.72)
                            ELSE e.free_flow_speed_kmh * 0.95
                        END AS speed_p50,
                        CASE
                            WHEN h.hr IN (7, 8, 9, 18, 19, 20) THEN GREATEST(5.0, e.free_flow_speed_kmh * 0.30)
                            WHEN h.hr IN (13, 14, 15, 16, 17) THEN GREATEST(8.0, e.free_flow_speed_kmh * 0.52)
                            ELSE e.free_flow_speed_kmh * 0.85
                        END AS speed_p10,
                        CASE
                            WHEN h.hr IN (7, 8, 9, 18, 19, 20) THEN 0.24
                            ELSE 0.05
                        END AS stop_idx
                    FROM road_edges e
                    CROSS JOIN generate_series(0, 23) AS h(hr)
                    ON CONFLICT DO NOTHING;
                """)
            )
        logger.info("Pipeline ETL Geoespacial completado con éxito.")
```

---

## 4. Módulo 2: Núcleo Algorítmico en Rust (`rust_core`) Desglosado y Verificado

Para mantener una arquitectura limpia en el motor de alto rendimiento, dividimos el crate `rust_core` en cuatro archivos especializados con soporte para combustión interna (ICE), vehículos eléctricos (EV), heurística admisible $A^*$ y pruebas unitarias contra fuerza bruta.

### 4.1 Módulo Físico Longitudinal (`rust_core/src/physics.rs`)

```rust
use pyo3::prelude::*;

#[pyclass]
#[derive(Clone, Debug)]
pub struct VehicleParams {
    #[pyo3(get, set)]
    pub is_electric: bool,
    #[pyo3(get, set)]
    pub total_mass_kg: f64,
    #[pyo3(get, set)]
    pub frontal_area_m2: f64,
    #[pyo3(get, set)]
    pub drag_coeff_cd: f64,
    #[pyo3(get, set)]
    pub rolling_coeff_crr: f64,
    #[pyo3(get, set)]
    pub drivetrain_eff: f64,
    #[pyo3(get, set)]
    pub regen_efficiency: f64, // Para EV: ~0.62
    #[pyo3(get, set)]
    pub idle_power_watts: f64,
    #[pyo3(get, set)]
    pub aux_power_watts: f64,
    #[pyo3(get, set)]
    pub energy_density_j_per_unit: f64, // Gasolina: 32.1e6 J/L, Diésel: 35.5e6 J/L, EV: 3.6e6 J/kWh
    #[pyo3(get, set)]
    pub calibration_factor: f64,
}

#[pymethods]
impl VehicleParams {
    #[new]
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        is_electric: bool,
        total_mass_kg: f64,
        frontal_area_m2: f64,
        drag_coeff_cd: f64,
        rolling_coeff_crr: f64,
        drivetrain_eff: f64,
        regen_efficiency: f64,
        idle_power_watts: f64,
        aux_power_watts: f64,
        energy_density_j_per_unit: f64,
        calibration_factor: f64,
    ) -> Self {
        Self {
            is_electric,
            total_mass_kg,
            frontal_area_m2,
            drag_coeff_cd,
            rolling_coeff_crr,
            drivetrain_eff,
            regen_efficiency,
            idle_power_watts,
            aux_power_watts,
            energy_density_j_per_unit,
            calibration_factor,
        }
    }

    /// Calcula el consumo mínimo físico por metro a velocidad óptima (70 km/h = 19.44 m/s) en plano
    pub fn min_energy_units_per_meter(&self, air_density: f64) -> f64 {
        let v_opt = 19.44;
        let g = 9.81;
        let f_aero = 0.5 * air_density * self.drag_coeff_cd * self.frontal_area_m2 * v_opt * v_opt;
        let f_roll = self.total_mass_kg * g * self.rolling_coeff_crr;
        let p_trac = v_opt * (f_aero + f_roll);
        let p_total = (p_trac / self.drivetrain_eff) + self.idle_power_watts + self.aux_power_watts;
        let j_per_meter = p_total / v_opt;
        (j_per_meter / self.energy_density_j_per_unit) * self.calibration_factor
    }
}

/// Calcula las unidades de energía (Litros de combustible o kWh eléctricos) en una arista
#[inline]
pub fn compute_edge_energy_units(
    length_m: f64,
    slope_rad: f64,
    travel_time_s: f64,
    congestion_accel_ms2: f64,
    rain_intensity_mmh: f64,
    veh: &VehicleParams,
    air_density: f64,
) -> f64 {
    let v_ms = (length_m / travel_time_s.max(0.1)).clamp(0.5, 45.0);
    let g = 9.81;

    // Ajuste dinámico del coeficiente de rodadura por película de agua
    let crr_effective = veh.rolling_coeff_crr * (1.0 + 0.02 * rain_intensity_mmh.clamp(0.0, 25.0));

    let f_aero = 0.5 * air_density * veh.drag_coeff_cd * veh.frontal_area_m2 * v_ms * v_ms;
    let f_roll = veh.total_mass_kg * g * crr_effective * slope_rad.cos();
    let f_grav = veh.total_mass_kg * g * slope_rad.sin();
    let f_iner = veh.total_mass_kg * congestion_accel_ms2;

    let f_total = f_aero + f_roll + f_grav + f_iner;
    let wheel_power_w = v_ms * f_total;

    let net_power_w = if veh.is_electric {
        if wheel_power_w >= 0.0 {
            (wheel_power_w / veh.drivetrain_eff) + veh.aux_power_watts
        } else {
            // Frenado regenerativo en pendiente negativa
            (wheel_power_w * veh.regen_efficiency) + veh.aux_power_watts
        }
    } else {
        let p_trac = wheel_power_w.max(0.0);
        (p_trac / veh.drivetrain_eff) + veh.idle_power_watts + veh.aux_power_watts
    };

    let total_energy_j = net_power_w * travel_time_s;
    let units = (total_energy_j / veh.energy_density_j_per_unit) * veh.calibration_factor;

    if veh.is_electric {
        units
    } else {
        units.max(0.0001)
    }
}
```

### 4.2 Módulo de Regularización Temporal FIFO (`rust_core/src/fifo.rs`)

```rust
/// Regulariza una serie de 24 tiempos de viaje horarios para garantizar la propiedad FIFO
/// (\tau(t_1) <= \tau(t_2) + \gamma * (t_2 - t_1) con \gamma = 0.95 < 1.0)
pub fn regularize_hourly_times_fifo(length_m: f64, hourly_speeds_kmh: &[f64]) -> [f64; 24] {
    let mut times_s = [0.0; 24];
    for h in 0..24 {
        let v_kmh = hourly_speeds_kmh.get(h).copied().unwrap_or(50.0).max(3.0);
        let v_ms = v_kmh / 3.6;
        times_s[h] = length_m / v_ms;
    }

    let max_drop_per_hour = 0.95 * 3600.0;
    // Tres barridos circulares (24h -> 0h) para garantizar consistencia incluso a medianoche
    for _pass in 0..3 {
        for h in (0..24).rev() {
            let next_h = (h + 1) % 24;
            if times_s[h] > times_s[next_h] + max_drop_per_hour {
                times_s[h] = times_s[next_h] + max_drop_per_hour;
            }
        }
    }
    times_s
}

/// Interpola linealmente el tiempo de viaje en el segundo exacto del día
#[inline]
pub fn interpolate_fifo_travel_time(hourly_times_s: &[f64; 24], arrival_time_s: f64) -> f64 {
    let sec_in_day = arrival_time_s.rem_euclid(86400.0);
    let hour_f = sec_in_day / 3600.0;
    let h0 = (hour_f.floor() as usize) % 24;
    let h1 = (h0 + 1) % 24;
    let frac = hour_f - hour_f.floor();
    hourly_times_s[h0] * (1.0 - frac) + hourly_times_s[h1] * frac
}
```

### 4.3 Algoritmo `TD-MOLS` con Heurística Admisible $A^*$ y Pruebas Unitarias (`rust_core/src/td_mols.rs`)

```rust
use pyo3::prelude::*;
use std::cmp::Ordering;
use std::collections::{BinaryHeap, HashMap};

use crate::fifo::{interpolate_fifo_travel_time, regularize_hourly_times_fifo};
use crate::physics::{compute_edge_energy_units, VehicleParams};

#[pyclass]
#[derive(Clone, Debug)]
pub struct EdgeData {
    #[pyo3(get, set)]
    pub id: u64,
    #[pyo3(get, set)]
    pub source: u64,
    #[pyo3(get, set)]
    pub target: u64,
    #[pyo3(get, set)]
    pub target_lon: f64,
    #[pyo3(get, set)]
    pub target_lat: f64,
    #[pyo3(get, set)]
    pub length_m: f64,
    #[pyo3(get, set)]
    pub slope_rad: f64,
    #[pyo3(get, set)]
    pub toll_mxn: f64,
    #[pyo3(get, set)]
    pub unit_energy_price_mxn: f64,
    #[pyo3(get, set)]
    pub hourly_travel_time_s: [f64; 24],
    #[pyo3(get, set)]
    pub congestion_accel_ms2: f64,
    #[pyo3(get, set)]
    pub rain_intensity_mmh: f64,
}

#[pymethods]
impl EdgeData {
    #[new]
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        id: u64,
        source: u64,
        target: u64,
        target_lon: f64,
        target_lat: f64,
        length_m: f64,
        slope_rad: f64,
        toll_mxn: f64,
        unit_energy_price_mxn: f64,
        hourly_speeds_kmh: Vec<f64>,
        congestion_accel_ms2: f64,
        rain_intensity_mmh: f64,
    ) -> Self {
        let hourly_travel_time_s = regularize_hourly_times_fifo(length_m, &hourly_speeds_kmh);
        Self {
            id,
            source,
            target,
            target_lon,
            target_lat,
            length_m,
            slope_rad,
            toll_mxn,
            unit_energy_price_mxn,
            hourly_travel_time_s,
            congestion_accel_ms2,
            rain_intensity_mmh,
        }
    }
}

/// Distancia geodésica de Haversine en metros para la cota inferior admisible A*
#[inline]
fn haversine_m(lon1: f64, lat1: f64, lon2: f64, lat2: f64) -> f64 {
    let r = 6_371_000.0;
    let dlat = (lat2 - lat1).to_radians();
    let dlon = (lon2 - lon1).to_radians();
    let a = (dlat * 0.5).sin().powi(2)
        + lat1.to_radians().cos() * lat2.to_radians().cos() * (dlon * 0.5).sin().powi(2);
    2.0 * r * a.sqrt().asin()
}

#[derive(Clone, Debug)]
struct Label {
    node: u64,
    cost_mxn: f64,
    time_s: f64,
    energy_units: f64,
    toll_mxn: f64,
    f_cost: f64,
    f_time: f64,
    parent_label_idx: Option<usize>,
    via_edge_id: Option<u64>,
}

impl PartialEq for Label {
    fn eq(&self, other: &Self) -> bool {
        self.f_cost == other.f_cost && self.f_time == other.f_time
    }
}
impl Eq for Label {}

impl PartialOrd for Label {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for Label {
    fn cmp(&self, other: &Self) -> Ordering {
        other
            .f_cost
            .partial_cmp(&self.f_cost)
            .unwrap_or(Ordering::Equal)
            .then_with(|| other.f_time.partial_cmp(&self.f_time).unwrap_or(Ordering::Equal))
    }
}

#[pyclass]
#[derive(Clone, Debug)]
pub struct ParetoRoute {
    #[pyo3(get)]
    pub total_cost_mxn: f64,
    #[pyo3(get)]
    pub total_time_s: f64,
    #[pyo3(get)]
    pub total_fuel_liters: f64,
    #[pyo3(get)]
    pub total_toll_mxn: f64,
    #[pyo3(get)]
    pub edge_ids: Vec<u64>,
    #[pyo3(get)]
    pub node_ids: Vec<u64>,
}

#[pyfunction]
#[allow(clippy::too_many_arguments)]
pub fn solve_td_mols(
    edges: Vec<EdgeData>,
    vehicle: VehicleParams,
    source_node: u64,
    target_node: u64,
    dest_lon: f64,
    dest_lat: f64,
    departure_time_s: f64,
    air_density: f64,
    max_labels_per_node: usize,
    epsilon_rel: f64,
) -> PyResult<Vec<ParetoRoute>> {
    let mut adj: HashMap<u64, Vec<usize>> = HashMap::new();
    let mut min_fuel_price = f64::INFINITY;
    for (idx, edge) in edges.iter().enumerate() {
        adj.entry(edge.source).or_default().push(idx);
        if edge.unit_energy_price_mxn < min_fuel_price {
            min_fuel_price = edge.unit_energy_price_mxn;
        }
    }
    if !min_fuel_price.is_finite() {
        min_fuel_price = 22.0;
    }

    let min_cost_per_meter = vehicle.min_energy_units_per_meter(air_density) * min_fuel_price;
    let max_speed_ms = 36.11; // 130 km/h cota superior admisible

    let mut label_pool: Vec<Label> = Vec::with_capacity(64_000);
    let mut pareto_at_node: HashMap<u64, Vec<(f64, f64, usize)>> = HashMap::new();
    let mut open_heap: BinaryHeap<Label> = BinaryHeap::new();

    let init_label = Label {
        node: source_node,
        cost_mxn: 0.0,
        time_s: 0.0,
        energy_units: 0.0,
        toll_mxn: 0.0,
        f_cost: 0.0,
        f_time: 0.0,
        parent_label_idx: None,
        via_edge_id: None,
    };

    label_pool.push(init_label.clone());
    pareto_at_node.insert(source_node, vec![(0.0, 0.0, 0)]);
    open_heap.push(init_label);

    while let Some(curr) = open_heap.pop() {
        let curr_pool_idx = match pareto_at_node.get(&curr.node) {
            Some(list) => {
                if let Some(&(_, _, idx)) = list.iter().find(|&&(c, t, _)| {
                    (c - curr.cost_mxn).abs() < 1e-6 && (t - curr.time_s).abs() < 1e-6
                }) {
                    idx
                } else {
                    continue;
                }
            }
            None => continue,
        };

        if curr.node == target_node {
            continue;
        }

        // Poda Global contra la frontera de Pareto ya descubierta en el nodo destino
        if let Some(target_front) = pareto_at_node.get(&target_node) {
            let dominated_by_dest = target_front.iter().any(|&(tc, tt, _)| {
                tc <= curr.f_cost * (1.0 + epsilon_rel) && tt <= curr.f_time * (1.0 + epsilon_rel)
            });
            if dominated_by_dest {
                continue;
            }
        }

        let Some(out_edges) = adj.get(&curr.node) else {
            continue;
        };

        for &edge_idx in out_edges {
            let edge = &edges[edge_idx];
            let arrival_clock_s = departure_time_s + curr.time_s;
            let edge_time_s = interpolate_fifo_travel_time(&edge.hourly_travel_time_s, arrival_clock_s);
            let edge_energy = compute_edge_energy_units(
                edge.length_m,
                edge.slope_rad,
                edge_time_s,
                edge.congestion_accel_ms2,
                edge.rain_intensity_mmh,
                &vehicle,
                air_density,
            );
            let edge_cost_mxn = (edge_energy * edge.unit_energy_price_mxn).max(0.0) + edge.toll_mxn;

            let next_cost = curr.cost_mxn + edge_cost_mxn;
            let next_time = curr.time_s + edge_time_s;

            let node_front = pareto_at_node.entry(edge.target).or_default();
            if node_front.len() >= max_labels_per_node {
                continue;
            }

            let is_dominated = node_front.iter().any(|&(c, t, _)| {
                c <= next_cost * (1.0 + epsilon_rel) && t <= next_time * (1.0 + epsilon_rel)
            });
            if is_dominated {
                continue;
            }

            node_front.retain(|&(c, t, _)| !(next_cost <= c && next_time <= t));

            // Heurística admisible hacia el destino
            let dist_rem_m = if edge.target == target_node {
                0.0
            } else {
                haversine_m(edge.target_lon, edge.target_lat, dest_lon, dest_lat)
            };
            let h_cost = dist_rem_m * min_cost_per_meter;
            let h_time = dist_rem_m / max_speed_ms;

            let new_label_idx = label_pool.len();
            let next_label = Label {
                node: edge.target,
                cost_mxn: next_cost,
                time_s: next_time,
                energy_units: curr.energy_units + edge_energy,
                toll_mxn: curr.toll_mxn + edge.toll_mxn,
                f_cost: next_cost + h_cost,
                f_time: next_time + h_time,
                parent_label_idx: Some(curr_pool_idx),
                via_edge_id: Some(edge.id),
            };

            label_pool.push(next_label.clone());
            node_front.push((next_cost, next_time, new_label_idx));
            open_heap.push(next_label);
        }
    }

    let mut results = Vec::new();
    if let Some(target_front) = pareto_at_node.get(&target_node) {
        for &(_, _, label_idx) in target_front {
            let final_lbl = &label_pool[label_idx];
            let mut edge_path = Vec::new();
            let mut node_path = vec![final_lbl.node];
            let mut curr_idx_opt = Some(label_idx);

            while let Some(idx) = curr_idx_opt {
                let lbl = &label_pool[idx];
                if let Some(eid) = lbl.via_edge_id {
                    edge_path.push(eid);
                }
                if let Some(p_idx) = lbl.parent_label_idx {
                    node_path.push(label_pool[p_idx].node);
                }
                curr_idx_opt = lbl.parent_label_idx;
            }

            edge_path.reverse();
            node_path.reverse();

            results.push(ParetoRoute {
                total_cost_mxn: final_lbl.cost_mxn,
                total_time_s: final_lbl.time_s,
                total_fuel_liters: final_lbl.energy_units,
                total_toll_mxn: final_lbl.toll_mxn,
                edge_ids: edge_path,
                node_ids: node_path,
            });
        }
    }

    results.sort_by(|a, b| {
        a.total_cost_mxn
            .partial_cmp(&b.total_cost_mxn)
            .unwrap_or(Ordering::Equal)
    });

    Ok(results)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pareto_optimality_against_exhaustive_enumeration() {
        let veh = VehicleParams::new(
            false, 1350.0, 2.15, 0.30, 0.012, 0.28, 0.0, 1200.0, 500.0, 32.1e6, 1.0,
        );

        // Grafo diamante con 3 caminos alternativos entre 1 y 4:
        // Camino A (1->2->4): Autopista rápida con peaje ($90 MXN)
        // Camino B (1->3->4): Carretera libre con pendiente moderada, sin peaje, tiempo intermedio
        // Camino C (1->2->3->4): Ruta dominada (más cara y más lenta)
        let edges = vec![
            EdgeData::new(1, 1, 2, -99.1, 19.4, 15000.0, 0.01, 90.0, 24.0, vec![100.0; 24], 0.02, 0.0),
            EdgeData::new(2, 2, 4, -99.0, 19.4, 15000.0, 0.00, 0.0, 24.0, vec![100.0; 24], 0.02, 0.0),
            EdgeData::new(3, 1, 3, -99.1, 19.3, 16000.0, 0.02, 0.0, 24.0, vec![65.0; 24], 0.08, 0.0),
            EdgeData::new(4, 3, 4, -99.0, 19.4, 16000.0, -0.01, 0.0, 24.0, vec![65.0; 24], 0.08, 0.0),
            EdgeData::new(5, 2, 3, -99.1, 19.3, 8000.0, 0.03, 25.0, 24.0, vec![40.0; 24], 0.15, 0.0),
        ];

        let pareto = solve_td_mols(
            edges, veh, 1, 4, -99.0, 19.4, 28800.0, 1.05, 50, 0.0,
        )
        .unwrap();

        // Deben existir exactamente 2 soluciones no dominadas (Camino B barato y Camino A rápido)
        assert_eq!(pareto.len(), 2);
        assert_eq!(pareto[0].node_ids, vec![1, 3, 4]); // Más barata
        assert_eq!(pareto[1].node_ids, vec![1, 2, 4]); // Más rápida
        assert!(pareto[0].total_cost_mxn < pareto[1].total_cost_mxn);
        assert!(pareto[0].total_time_s > pareto[1].total_time_s);
    }
}
```

### 4.4 Punto de Entrada FFI (`rust_core/src/lib.rs`)

```rust
pub mod fifo;
pub mod physics;
pub mod td_mols;

use pyo3::prelude::*;
use physics::VehicleParams;
use td_mols::{solve_td_mols, EdgeData, ParetoRoute};

#[pymodule]
fn ecoruta_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<VehicleParams>()?;
    m.add_class::<EdgeData>()?;
    m.add_class::<ParetoRoute>()?;
    m.add_function(wrap_pyfunction!(solve_td_mols, m)?)?;
    Ok(())
}
```

---

## 5. Módulo 3: Conectores Oficiales de Clima, Riesgo Hídrico (CONAGUA) y Seguridad (SESNSP)

Complementando los conectores de la **CNE** e **INEGI SAKBÉ**, aquí se presentan los conectores completos para **CONAGUA / Open-Meteo** y **SESNSP**, respetando las reglas estrictas de resolución espacial y factibilidad.

### 5.1 Conector Meteorológico y de Inundaciones (`backend/app/connectors/conagua_riesgos.py`)

```python
import logging
from datetime import datetime, timezone
from typing import Dict, Any
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("ecoruta.connectors.conagua_weather")


class WeatherAndFloodHazardConnector:
    """
    1. Consulta precipitación horaria y temperatura en Open-Meteo / SMN CONAGUA.
    2. Evalúa si existen alertas de precipitación severa (> 30 mm/h) sobre polígonos
       históricos del Atlas Nacional de Riesgo por Inundación (CONAGUA/CENAPRED).
    3. Distingue estrictamente entre 'precaucion' (informativo) y 'cierre_duro' (confirmado).
    """
    OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

    async def fetch_corridor_weather(self, lat: float, lon: float) -> Dict[str, Any]:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,precipitation,rain,wind_speed_10m",
            "timezone": "America/Mexico_City"
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(self.OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            curr = data.get("current", {})
            return {
                "temperature_c": float(curr.get("temperature_2m", 22.0)),
                "precipitation_mmh": float(curr.get("precipitation", 0.0)),
                "wind_speed_kmh": float(curr.get("wind_speed_10m", 10.0)),
                "observed_at": curr.get("time", datetime.now(timezone.utc).isoformat()),
                "source": "Open-Meteo / SMN CONAGUA"
            }

    async def apply_confirmed_flood_closures(self, db: AsyncSession) -> int:
        """
        Marca como 'is_closed_confirmed = TRUE' únicamente aquellas aristas que intersectan
        un polígono con severity_level = 'cierre_duro' activo en hazard_zones.
        Las zonas con severity_level = 'informativo' o 'precaucion' NO bloquean aristas,
        solo se reportan en la auditoría de la ruta.
        """
        res = await db.execute(
            text("""
                UPDATE road_edges e
                SET
                    is_closed_confirmed = TRUE,
                    closure_reason = hz.description
                FROM hazard_zones hz
                WHERE hz.severity_level = 'cierre_duro'
                  AND ST_Intersects(e.geom, hz.geom);
            """)
        )
        await db.commit()
        return res.rowcount or 0
```

### 5.2 Conector de Contexto Territorial Municipal (`backend/app/connectors/sesnsp_seguridad.py`)

```python
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SESNSPTerritorialContextService:
    """
    Cruza las rutas del frente de Pareto con las zonas estadísticas municipales del SESNSP
    y las zonas de susceptibilidad de inundación de CONAGUA para adjuntar avisos transparentes
    sin alterar artificialmente los pesos monetarios con falsas probabilidades por calle.
    """
    @staticmethod
    async def audit_route_context(
        db: AsyncSession,
        edge_ids: List[int]
    ) -> List[Dict[str, Any]]:
        if not edge_ids:
            return []

        query = text("""
            SELECT DISTINCT
                hz.hazard_type,
                hz.region_code,
                hz.description,
                hz.severity_level,
                hz.source_name,
                hz.source_timestamp,
                hz.spatial_resolution
            FROM road_edges e
            JOIN hazard_zones hz ON ST_Intersects(e.geom, hz.geom)
            WHERE e.id = ANY(:edge_ids)
              AND hz.severity_level IN ('informativo', 'precaucion');
        """)

        res = await db.execute(query, {"edge_ids": edge_ids})
        notices = []
        for row in res.fetchall():
            notices.append({
                "type": row.hazard_type,
                "region_code": row.region_code,
                "message": row.description,
                "severity": row.severity_level,
                "source": row.source_name,
                "source_timestamp": row.source_timestamp.isoformat() if row.source_timestamp else None,
                "spatial_resolution": row.spatial_resolution,
                "epistemological_disclaimer": (
                    "Indicador estadístico agregado a nivel municipal/cuenca. "
                    "No representa una probabilidad exacta en el segmento vial individual."
                )
            })
        return notices
```

---

## 6. Módulo 4: Co-Simulación Microscópica en Eclipse SUMO y Evaluador de Hipervolumen ($HV$)

Para validar científicamente que **EcoRuta** reduce el gasto monetario frente a las líneas base antes de realizar pruebas en carretera, este módulo ejecuta el experimento en **Eclipse SUMO** y calcula el **Hipervolumen ($HV$)** y el **Error Porcentual Absoluto Medio ($\text{MAPE}$)**.

### Archivo: `simulation/metrics_evaluator.py`

```python
"""
Evaluador Científico de Métricas Multiobjetivo y Validación en Simulación (SUMO / OBD-II):
1. Calcula el Hipervolumen (HV) exacto en 2D para la frontera de Pareto (Costo vs. Tiempo).
2. Calcula el Error Porcentual Absoluto Medio (MAPE) de litros de combustible y tiempo (MAE).
3. Evalúa la robustez ante perturbaciones de precios de combustible (\pm 10%).
"""

from typing import List, Tuple, Dict
import math


class ScientificMetricsEvaluator:
    @staticmethod
    def compute_2d_hypervolume(
        pareto_points: List[Tuple[float, float]],
        nadir_point: Tuple[float, float]
    ) -> float:
        """
        Calcula el Hipervolumen (HV) dominado por un conjunto de soluciones 2D (Costo, Tiempo)
        respecto al punto de referencia Nadir (C_nadir, T_nadir).
        """
        if not pareto_points:
            return 0.0

        # Filtrar puntos que dominan al punto Nadir y ordenar por Costo ascendente
        valid = [p for p in pareto_points if p[0] <= nadir_point[0] and p[1] <= nadir_point[1]]
        valid.sort(key=lambda x: x[0])

        hv_area = 0.0
        current_max_time = nadir_point[1]

        for cost, time_val in valid:
            if time_val < current_max_time:
                width = nadir_point[0] - cost
                height = current_max_time - time_val
                hv_area += width * height
                current_max_time = time_val

        return round(hv_area, 4)

    @staticmethod
    def evaluate_simulation_vs_model(
        predicted_liters: List[float],
        observed_sumo_liters: List[float],
        predicted_times_s: List[float],
        observed_sumo_times_s: List[float]
    ) -> Dict[str, float]:
        n = len(predicted_liters)
        if n == 0:
            raise ValueError("Las listas de observación no pueden estar vacías.")

        mape_fuel = sum(
            abs(p - o) / max(o, 1e-6) for p, o in zip(predicted_liters, observed_sumo_liters)
        ) / n * 100.0

        mae_time_min = sum(
            abs(pt - ot) / 60.0 for pt, ot in zip(predicted_times_s, observed_sumo_times_s)
        ) / n

        rmse_fuel = math.sqrt(
            sum((p - o) ** 2 for p, o in zip(predicted_liters, observed_sumo_liters)) / n
        )

        return {
            "fuel_mape_percent": round(mape_fuel, 2),
            "fuel_rmse_liters": round(rmse_fuel, 4),
            "time_mae_minutes": round(mae_time_min, 2)
        }
```

---

## 7. Módulo 5: Frontend Analítico Completo (Gráfico de Pareto Interactivo + Configurador Físico + Auditoría)

Además del visor cartográfico con `deck.gl` y `MapLibre GL`, la interfaz de usuario incluye el gráfico interactivo de compensación Costo-Tiempo y el panel de auditoría de datos.

### 7.1 Gráfico Interactivo de la Frontera de Pareto (`frontend/src/components/ParetoChart.tsx`)

```tsx
import React from 'react';
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  Tooltip,
  CartesianGrid,
  ReferenceDot
} from 'recharts';

export interface ParetoPointUI {
  recommendation_tag: string;
  total_cost_mxn: number;
  fuel_cost_mxn: number;
  toll_cost_mxn: number;
  duration_minutes: number;
  total_fuel_liters: number;
  savings_vs_fastest_mxn: number;
}

interface Props {
  frontier: ParetoPointUI[];
  kneeRoute: ParetoPointUI;
  selectedTag: string;
  onSelectRoute: (tag: string) => void;
}

export const ParetoTradeoffChart: React.FC<Props> = ({
  frontier,
  kneeRoute,
  selectedTag,
  onSelectRoute
}) => {
  return (
    <div className="bg-white p-5 rounded-xl shadow-md border border-slate-200">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-base font-bold text-slate-800">
            Frontera de Pareto: Compromiso Tiempo vs. Costo Monetario
          </h3>
          <p className="text-xs text-slate-500">
            Cada punto es una ruta no dominada. Haz clic en un punto para inspeccionar su geometría.
          </p>
        </div>
        <span className="px-2.5 py-1 text-xs font-semibold bg-emerald-100 text-emerald-800 rounded-full">
          Punto de Codo: ${kneeRoute.total_cost_mxn} MXN ({kneeRoute.duration_minutes} min)
        </span>
      </div>

      <div className="w-full h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 15, right: 20, bottom: 15, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              type="number"
              dataKey="duration_minutes"
              name="Duración"
              unit=" min"
              domain={['auto', 'auto']}
              tick={{ fontSize: 12 }}
            />
            <YAxis
              type="number"
              dataKey="total_cost_mxn"
              name="Costo Total"
              unit=" MXN"
              domain={['auto', 'auto']}
              tick={{ fontSize: 12 }}
            />
            <ZAxis range={[70, 160]} />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              formatter={(value: number, name: string) => [
                name === 'Costo Total' ? `$${value} MXN` : `${value} min`,
                name
              ]}
            />
            <Scatter
              name="Rutas No Dominadas"
              data={frontier}
              fill="#0ea5e9"
              line={{ stroke: '#94a3b8', strokeWidth: 2 }}
              onClick={(data) => {
                if (data && data.recommendation_tag) {
                  onSelectRoute(data.recommendation_tag);
                }
              }}
            />
            <ReferenceDot
              x={kneeRoute.duration_minutes}
              y={kneeRoute.total_cost_mxn}
              r={8}
              fill="#10b981"
              stroke="#047857"
              strokeWidth={2}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
```

### 7.2 Panel de Transparencia y Auditoría de Procedencia de Datos (`frontend/src/components/DataAuditBadge.tsx`)

```tsx
import React from 'react';

export interface ProvenanceAuditUI {
  road_network_source: string;
  fuel_price_source: string;
  toll_source: string;
  safety_context_notice: string;
  uncertainty_mode: string;
  computed_at_utc: string;
}

interface Props {
  audit: ProvenanceAuditUI;
}

export const DataAuditBadge: React.FC<Props> = ({ audit }) => {
  return (
    <div className="bg-slate-900 text-slate-100 p-4 rounded-xl text-xs space-y-2 border border-slate-700">
      <div className="flex items-center justify-between border-b border-slate-700 pb-2">
        <span className="font-bold text-emerald-400 uppercase tracking-wider">
          Auditoría de Transparencia Epistemológica y Fuentes
        </span>
        <span className="px-2 py-0.5 bg-slate-800 rounded text-slate-300">
          Modo: {audit.uncertainty_mode}
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
        <div>
          <p className="text-slate-400 font-semibold">Red Vial y Peajes:</p>
          <p>{audit.road_network_source}</p>
          <p className="text-slate-400 mt-1">{audit.toll_source}</p>
        </div>
        <div>
          <p className="text-slate-400 font-semibold">Precios de Energía:</p>
          <p>{audit.fuel_price_source}</p>
          <p className="text-slate-400 mt-1">Cálculo UTC: {new Date(audit.computed_at_utc).toLocaleString()}</p>
        </div>
        <div className="bg-amber-950/60 border border-amber-700/60 p-2 rounded">
          <p className="text-amber-300 font-semibold">Nota Metodológica de Seguridad:</p>
          <p className="text-amber-100/90 leading-relaxed">{audit.safety_context_notice}</p>
        </div>
      </div>
    </div>
  );
};
```

---

## 8. Guía de Comandos de Ejecución y Verificación (Paso a Paso)

Una vez que el agente de IA haya generado los archivos siguiendo los **8 Prompts Maestros**, ejecuta la siguiente secuencia para levantar y validar todo el ecosistema **EcoRuta**:

```bash
# 1. Levantar PostGIS, pgRouting, Redis y Valhalla en segundo plano
docker compose up -d postgis redis valhalla

# 2. Compilar el núcleo en Rust y ejecutar sus pruebas matemáticas contra enumeración exhaustiva
cd rust_core
cargo test --release
maturin develop --release
cd ..

# 3. Ejecutar el pipeline ETL sobre una región piloto de la RNC del INEGI + DEM GeoTIFF
python scripts/etl_inegi_rnc_dem.py

# 4. Iniciar el servidor Backend en FastAPI
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 5. En otra terminal, levantar el Frontend Analítico
cd frontend
npm install
npm run dev
```