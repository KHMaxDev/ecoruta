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
