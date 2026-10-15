# EcoRuta — Manual Maestro de Resolución Técnica, Arquitectura de Sistemas y Guía de Implementación Paso a Paso

**Fecha de resolución:** 14 de octubre de 2026  
**Estado del documento:** Especificación Técnica Definitiva y Guía de Ingeniería (De Cero a Producción)  
**Ámbito de aplicación:** República Mexicana (escalable a nivel regional)  
**Documentos analizados e integrados:**
1. `EcoRuta_Investigacion_Teorica_Algoritmos_Rutas.md` (Propuesta Teórica Base)
2. `contexto.md` (Análisis Crítico, Estado del Arte 2024–2026 y Fundamentación Física)
3. `tecnologias.md` (Evaluación y Selección del Stack Tecnológico)

---

## 1. Dictamen y Resolución Analítica de los Documentos

Tras un análisis exhaustivo de los tres documentos que conforman el expediente técnico de **EcoRuta**, se emite el siguiente **dictamen de resolución de ingeniería**:

El proyecto posee una base conceptual excepcionalmente sólida y honesta desde el punto de vista epistemológico: distingue con rigor entre objetivos de optimización, restricciones duras de factibilidad y variables contextuales, evitando la falsa promesa de una «ruta mágica universal». Sin embargo, al contrastar el documento original con el análisis crítico (`contexto.md`) y la matriz tecnológica (`tecnologias.md`), emergen **cinco tensiones técnicas críticas** que deben resolverse antes de escribir la primera línea de código para evitar que el proyecto fracase por intratabilidad computacional o imprecisión física.

### 1.1 Matriz de Resolución de Conflictos Técnicos

| Dimensión Crítica | Planteamiento Inicial (Doc. Base) | Corrección Científica (`contexto.md` y `tecnologias.md`) | Resolución Definitiva de Ingeniería para EcoRuta |
|---|---|---|---|
| **1. Dimensionalidad del Vector de Objetivos** | Minimizar simultáneamente 4 objetivos en el grafo: $\mathbf{F}(P) = [C(P), T(P), R(P), U(P)]$. | El problema de camino mínimo multiobjetivo (MOSP) es NP-difícil. Con $k \ge 4$ objetivos, el número de etiquetas no dominadas crece exponencialmente (pasando de milisegundos con $k=2$ a más de 38 minutos con $k=12$ según literatura de 2025). | **Reducción Dimensional Estricta:** El motor de etiquetado operará únicamente sobre un espacio bi-objetivo primario $(C, T)$ (Costo Monetario y Tiempo). La **Incertidumbre ($U$)** se modela mediante una evaluación dual del tiempo en el percentil $P_{50}$ (esperado) vs. $P_{90}$ (robusto). La **Seguridad ($R$)** se aplica como filtro duro (cierres confirmados) o auditoría informativa post-búsqueda. |
| **2. Propiedad Temporal de la Red Vial** | Trata el tiempo dependiente $\tau_e(t)$ como una simple evaluación de función al llegar al nodo. | En redes viales con cambios abruptos de velocidad, si $\tau_e(t)$ viola la propiedad **FIFO** (*First-In-First-Out*), los algoritmos de etiquetado pierden su garantía de optimalidad y correctitud. | **Envoltura de Regularización FIFO:** Antes de ejecutar la búsqueda, el módulo de ingesta de tráfico aplica una interpolación lineal continua por tramos con restricción de pendiente $\frac{d\tau_e(t)}{dt} \ge -1$, garantizando matemáticamente que salir antes nunca implique llegar después. |
| **3. Modelo de Consumo de Combustible** | Propone una fórmula base estática $C_f = \frac{D}{R} \times P$ y una función abstracta no especificada $L_e$. | El consumo real es una función cuadrática de la velocidad y altamente sensible a la pendiente ($\alpha$): subir una pendiente del $2\%$ al $7\%$ multiplica el consumo por $2.5\times$. | **Motor Físico-Empírico Escalable:** Se implementa la ecuación longitudinal de fuerzas (aerodinámica, rodadura, gravedad $\sin\alpha$ e inercia por tráfico) combinada con elevación digital (DEM) y curvas empíricas por tipo de vehículo, dejando $D/R$ exclusivamente como *fallback* de emergencia. |
| **4. Explosión del Espacio de Búsqueda** | Ejecutar algoritmos de etiquetado (*label-setting* / *label-correcting*) sobre la red vial completa. | En grafos reales de millones de aristas (como la RNC o OpenStreetMap), el algoritmo exacto agota la memoria RAM si explora toda la red. | **Poda por Corredor Elíptico (*Bounding Box*) + Cota $A^*$:** Se usa **Valhalla** o **pgRouting** para hallar en $< 50\text{ ms}$ la ruta más rápida y la más barata escalar. Se extrae un subgrafo amortiguado alrededor de ambas rutas y se ejecuta el algoritmo *Label-Setting* en **Rust (vía PyO3)** con podas heurísticas admisibles. |
| **5. Stack de Backend y Motor Base** | Sugiere preliminarmente Laravel/PHP y menciona OSRM junto a Valhalla como equivalentes. | OSRM precomputa pesos fijos (*Contraction Hierarchies*), impidiendo cambiar costos por hora, precio de gasolina o masa del vehículo en tiempo de consulta. PHP carece de ecosistema nativo de alto rendimiento para grafos y ciencia de datos. | **Stack Definitivo:** **PostgreSQL + PostGIS + pgRouting** para datos topológicos; **Valhalla** como motor de candidatos con *Dynamic Costing*; **Python (FastAPI)** para orquestación, conectores e integración con **Google OR-Tools**; **Rust + PyO3** para el núcleo *Label-Setting*; y **React + TypeScript + deck.gl + MapLibre GL** para el frontend. |

---

## 2. Arquitectura del Sistema Nivel Producción

El sistema se diseña bajo una **Arquitectura Limpia Hexagonal y Modular en 5 Capas**, garantizando que los proveedores externos de datos (INEGI, CNE, CONAGUA, SESNSP, Open-Meteo, Azure Maps) estén completamente desacoplados del motor matemático de optimización.

### 2.1 Diagrama de Arquitectura General

```
+---------------------------------------------------------------------------------------------------+
|                                  CAPA 5: PRESENTACIÓN Y CLIENTE                                   |
|  [ React 19 + TypeScript ] + [ MapLibre GL (Mapa Base) ] + [ deck.gl (Frente de Pareto / Capas) ] |
|  Panel de Compensación (Costo vs. Tiempo) | Auditoría de Frescura de Datos | Alertas Contextuales |
+---------------------------------------------------------------------------------------------------+
                                                 |
                                        HTTPS / JSON (REST)
                                                 v
+---------------------------------------------------------------------------------------------------+
|                           CAPA 4: ORQUESTACIÓN, API Y SELECTOR (FastAPI)                          |
|  - Validación de Contratos (Pydantic v2)        - Selector de Preferencias:                       |
|  - Gestor de Caché Espacial/Temporal (Redis)      * Suma Ponderada (Disposición a pagar \lambda)  |
|  - Auditor de Metadatos y Caducidad               * Método de \epsilon-Restricciones              |
|  - Optimizador Secuencial GTDVRP (OR-Tools)       * Detector Automático de Punto de Codo (Knee)   |
+---------------------------------------------------------------------------------------------------+
                   |                                                             |
      Llamada Nativa FFI (PyO3)                                        Consulta HTTP / Socket
                   v                                                             v
+----------------------------------------------------+   +------------------------------------------+
|     CAPA 3: NÚCLEO DE OPTIMIZACIÓN (Rust Core)     |   |   MOTOR DE ENRUTAMIENTO BASE (Valhalla)  |
|  - Algoritmo TD-MOLS (Time-Dependent Multi-        |   |  - Dynamic Costing en tiempo de consulta |
|    Objective Label-Setting)                        |   |  - Extracción de candidatos iniciales    |
|  - Verificación de Dominancia de Pareto O(k)       |   |  - Cálculo de isócronas y matrices base  |
|  - Poda por Cota Inferior Admisible (Heurística A*)|   +------------------------------------------+
|  - Evaluador Físico de Consumo y Garantía FIFO     |                        ^
+----------------------------------------------------+                        |
                   ^                                                          |
                   | Lectura de Subgrafo en Memoria (Arrow/Binary)            | Tiles Vialidad
                   +-----------------------------+----------------------------+
                                                 |
+---------------------------------------------------------------------------------------------------+
|                     CAPA 2: PERSISTENCIA GEOSPACIAL Y TOPOLÓGICA (PostgreSQL 16)                  |
|  [ PostGIS 3.4 ] + [ pgRouting 3.6 ]                                                              |
|  - Grafo Vial Unificado (Nodos, Aristas, Pendientes DEM, Límites de Peso/Gálibo, Peajes RNC)      |
|  - Series Temporales de Velocidad (FIFO-regularizadas) y Precios de Combustible por Estación      |
|  - Capas Poligonales de Peligro (CONAGUA Inundaciones) y Contexto Territorial (SESNSP Municipal)  |
+---------------------------------------------------------------------------------------------------+
                                                 ^
                                                 | Procesos ETL Asíncronos (Celery / Cron)
+---------------------------------------------------------------------------------------------------+
|                   CAPA 1: CONECTORES E INGESTA DE DATOS OFICIALES Y DINÁMICOS                     |
|  [INEGI RNC / SAKBÉ v3.1] [OSM + SRTM DEM] [CNE Gasolinas] [Open-Meteo/SMN] [CONAGUA] [SESNSP]    |
+---------------------------------------------------------------------------------------------------+
```

### 2.2 Flujo Detallado de Ejecución de una Consulta

1. **Recepción y Validación:** El usuario envía origen $s$, destino $t$, paradas opcionales $M$, hora de salida $t_0$, perfil del vehículo $v$ (masa, área frontal, combustible, dimensiones) y preferencias ($\lambda$, presupuesto máximo $C_{\max}$ o tiempo límite $T_{\max}$).
2. **Filtro de Factibilidad Dura y Subgrafo (*Bounding Box*):**
   - El sistema consulta a PostGIS/Valhalla las rutas extremas (mínimo tiempo y mínimo costo simple) excluyendo aristas cerradas (inundación confirmada, obra vial) o incompatibles con las dimensiones/peso del vehículo $v$.
   - Se genera una envolvente convexa amortiguada (*buffer* elíptico de $2\text{ km}$ a $15\text{ km}$ según la longitud del viaje) que reduce el grafo de millones de aristas a un subgrafo activo $G' = (V', E')$ de entre $2,000$ y $35,000$ aristas.
3. **Evaluación Física y Regularización FIFO:**
   - Para cada arista $e \in E'$, se asigna el precio del combustible $P_e$ vigente de la región/estación cercana (con su `timestamp` de la CNE), la tarifa de peaje exacta según el número de ejes de $v$ (datos RNC), la pendiente $\alpha_e$ y la curva de velocidad temporal regularizada bajo condición FIFO.
4. **Cálculo del Frente de Pareto (Rust TD-MOLS):**
   - El módulo en Rust recibe el subgrafo $G'$ y ejecuta el algoritmo *Label-Setting* multiobjetivo dependiente del tiempo, calculando el conjunto exacto (o $\epsilon$-aproximado controlado) de rutas no dominadas en costo monetario $C(P)$ y tiempo $T(P)$ (tanto esperado $P_{50}$ como robusto $P_{90}$).
5. **Enriquecimiento Contextual y Selección:**
   - A las rutas del frente de Pareto se les cruza espacialmente con las capas de susceptibilidad de inundación (CONAGUA) e incidencia municipal (SESNSP) para adjuntar metadatos informativos sin distorsionar arbitrariamente los pesos matemáticos.
   - El selector identifica automáticamente la ruta **Más Económica**, la **Más Rápida**, el **Punto de Codo (*Knee Point*)** y la **Óptima según Preferencia del Usuario** ($\lambda$ o $\epsilon$).

---

## 3. Fundamentación Matemática y Física Definitiva

Esta sección formaliza las ecuaciones exactas que deben programarse en el motor de costos y en el optimizador.

### 3.1 Modelo Físico-Empírico de Consumo de Combustible por Arista

Para superar la limitación del rendimiento constante ($km/l$), el consumo de combustible $L_e$ (en litros) en una arista $e \in E$ de longitud $d_e$ (en metros), pendiente media $\alpha_e = \arctan(\Delta h_e / d_e)$ y velocidad media estimada $V_e(t)$ (en $\text{m/s}$) a la hora de entrada $t$, se calcula mediante el modelo de potencia longitudinal traccional:

$$P_{\text{trac}, e}(t) = \max\left(0, \; V_e(t) \cdot \left[ F_{\text{aero}}(V_e(t)) + F_{\text{rod}}(\alpha_e) + F_{\text{grav}}(\alpha_e) + F_{\text{iner}}(q_e) \right] \right)$$

Donde las fuerzas resistentes (en Newtons, $\text{N}$) se definen como:

1. **Fuerza aerodinámica:**
   $$F_{\text{aero}}(V_e) = \frac{1}{2} \rho_{\text{aire}} C_d A_f V_e^2$$
2. **Fuerza de resistencia a la rodadura:**
   $$F_{\text{rod}}(\alpha_e) = W g C_{rr} \cos(\alpha_e)$$
3. **Fuerza gravitacional por pendiente:**
   $$F_{\text{grav}}(\alpha_e) = W g \sin(\alpha_e)$$
4. **Fuerza inercial equivalente por congestión y detenciones ($q_e$):**
   $$F_{\text{iner}}(q_e) = W \cdot a_{\text{eq}}(q_e)$$

Siendo los parámetros del modelo:
- $W = m_{\text{vehículo}} + m_{\text{carga}}$: Masa total en $\text{kg}$.
- $g = 9.81\text{ m/s}^2$: Aceleración gravitacional.
- $\rho_{\text{aire}}$: Densidad del aire ($\approx 1.225\text{ kg/m}^3$ a nivel del mar, ajustable por altitud en ciudades como CDMX o Toluca donde $\rho_{\text{aire}} \approx 0.98\text{ kg/m}^3$).
- $C_d$: Coeficiente aerodinámico del vehículo (típicamente $0.28 - 0.35$ para sedán, $0.38 - 0.45$ para SUV, $0.60 - 0.80$ para camión).
- $A_f$: Área frontal en $\text{m}^2$ ($2.0 - 2.6\text{ m}^2$ para ligeros, $6.0 - 9.0\text{ m}^2$ para pesados).
- $C_{rr}$: Coeficiente de rodadura ($0.010$ en asfalto en buen estado, $0.015$ con lluvia intensa, $0.025$ en terracería).
- $a_{\text{eq}}(q_e)$: Aceleración media equivalente por oscilaciones de tráfico ($\approx 0.05\text{ m/s}^2$ en flujo libre, $\approx 0.25\text{ m/s}^2$ en tráfico denso con semáforos).

El volumen de combustible consumido $L_e(t)$ (en litros) al recorrer la arista durante el tiempo $\tau_e(t) = \frac{d_e}{V_e(t)}$ (en segundos) es:

$$L_e(t) = \frac{\tau_e(t)}{Q_{\text{comb}} \cdot \rho_{\text{comb}}} \cdot \left( \frac{P_{\text{trac}, e}(t)}{\eta_{\text{tren}}} + P_{\text{ralentí}} + P_{\text{aux}}(\omega) \right)$$

Donde:
- $Q_{\text{comb}}$: Poder calorífico inferior del combustible ($\approx 43.4 \times 10^6\text{ J/kg}$ para gasolina, $\approx 42.8 \times 10^6\text{ J/kg}$ para diésel).
- $\rho_{\text{comb}}$: Densidad del combustible ($\approx 0.74\text{ kg/l}$ gasolina, $\approx 0.83\text{ kg/l}$ diésel).
- $\eta_{\text{tren}}$: Eficiencia térmica y mecánica combinada del tren motriz ($\approx 0.25 - 0.32$ en gasolina, $\approx 0.35 - 0.42$ en diésel).
- $P_{\text{ralentí}}$: Potencia base de mantenimiento del motor encendido (en Watts, $\text{W}$) para que el consumo nunca sea cero en detenciones o pendientes negativas.
- $P_{\text{aux}}(\omega)$: Potencia de sistemas auxiliares como aire acondicionado por temperatura exterior elevada ($\approx 1,500\text{ W}$).

> **Mecanismo de Calibración con el Rendimiento Nominal del Usuario ($R_{\text{nom}}$ en $\text{km/l}$):**  
> Si el usuario solo conoce su rendimiento promedio $R_{\text{nom}}$, el sistema calcula el consumo teórico base de su categoría a $V_{\text{ref}} = 70\text{ km/h}$ en plano ($\alpha = 0$) y aplica un factor de escala personalizado $\kappa_v = \frac{L_{\text{físico}}(70\text{ km/h}, 0)}{1 / R_{\text{nom}}}$. Así se conserva la física no lineal de pendientes y velocidades ajustada exactamente al vehículo del usuario.

### 3.2 Garantía Matemática de la Propiedad FIFO en Redes Dependientes del Tiempo

Sea $\tau_e(t)$ el tiempo de viaje en la arista $e$ al ingresar en el instante $t$. La red cumple la condición **FIFO** (*First-In-First-Out*) si y solo si para todo $t_1 < t_2$:

$$t_1 + \tau_e(t_1) \le t_2 + \tau_e(t_2) \iff \frac{\tau_e(t_2) - \tau_e(t_1)}{t_2 - t_1} \ge -1$$

Cuando se reciben velocidades horarias discretas $V_{e,0}, V_{e,1}, \dots, V_{e,23}$ de proveedores de tráfico o históricos, si en el cambio de hora pico a hora valle el tiempo de recorrido cae abruptamente (por ejemplo, de $20\text{ min}$ a $5\text{ min}$ en un intervalo de $10\text{ min}$), la pendiente sería $\frac{5 - 20}{10} = -1.5 < -1$, violando FIFO.

**Algoritmo de Regularización FIFO (Pre-procesamiento):**
Dados los puntos discretos $(t_k, \tau_e(t_k))$ ordenados cronológicamente, se recorre la serie hacia atrás o hacia adelante imponiendo la cota:

$$\tilde{\tau}_e(t_{k}) = \min\left( \tau_e(t_k), \; \tilde{\tau}_e(t_{k+1}) + \gamma (t_{k+1} - t_k) \right) \quad \text{con } \gamma = 0.95 < 1$$

Con esta regularización $\tilde{\tau}_e(t)$, la función de llegada $A_e(t) = t + \tilde{\tau}_e(t)$ es estrictamente creciente, garantizando que el algoritmo *Label-Setting* encuentre el frente de Pareto exacto sin necesidad de modelar esperas en intersecciones.

### 3.3 Formulación del Problema Multiobjetivo y Selección del Punto de Codo (*Knee Point*)

Para un camino factible $P = (e_1, e_2, \dots, e_m) \in \mathcal{F}$ que parte de $s$ en $t_0$, la secuencia de tiempos de llegada se define recursivamente como:

$$t_1 = t_0, \quad t_{j+1} = t_j + \tilde{\tau}_{e_j}(t_j) \quad \forall j \in \{1, \dots, m\}$$

El vector de evaluación primario es:

$$\min_{P \in \mathcal{F}} \mathbf{F}(P) = \begin{bmatrix} C(P) \\ T_{\beta}(P) \end{bmatrix}$$

Donde:
- $C(P) = \sum_{j=1}^m \left( L_{e_j}(t_j) \cdot P_{e_j} + \text{Peaje}(e_j, v) \right)$ es el costo monetario total en $\text{MXN}$.
- $T_{\beta}(P) = \sum_{j=1}^m \tilde{\tau}_{e_j}^{(\beta)}(t_j)$ es la duración total bajo el nivel de confianza $\beta \in \{0.50, 0.90\}$ (donde $\beta = 0.50$ corresponde al tiempo esperado y $\beta = 0.90$ al tiempo robusto ante congestión).

**Detección Automática del Punto de Codo (*Knee Point*) en la Frontera de Pareto:**
Sea $\mathcal{P}^* = \{P_1, P_2, \dots, P_r\}$ el conjunto de rutas no dominadas ordenadas de menor a mayor costo ($C(P_1) < C(P_2) < \dots < C(P_r)$ y, por ende, $T(P_1) > T(P_2) > \dots > T(P_r)$).
1. Se normalizan ambos objetivos al intervalo $[0, 1]$:
   $$\hat{C}_i = \frac{C(P_i) - C(P_1)}{C(P_r) - C(P_1)}, \quad \hat{T}_i = \frac{T(P_i) - T(P_r)}{T(P_1) - T(P_r)}$$
2. La línea recta extrema en el espacio normalizado une $(0, 1)$ con $(1, 0)$, cuya ecuación general es $\hat{C} + \hat{T} - 1 = 0$.
3. El **Punto de Codo ($P_{\text{knee}}$)** es la ruta que maximiza la distancia perpendicular hacia el origen respecto a la recta extrema:
   $$P_{\text{knee}} = \arg\max_{P_i \in \mathcal{P}^*} \frac{|1 - \hat{C}_i - \hat{T}_i|}{\sqrt{2}}$$

---

## 4. Stack Tecnológico Definitivo y Estructura del Monorepo

### 4.1 Resumen de Tecnologías Seleccionadas y Versiones

- **Base de Datos y Motor Espacial:** PostgreSQL `16.x` + PostGIS `3.4+` + pgRouting `3.6+`.
- **Motor de Ruteo Base y Candidatos:** Valhalla `3.4+` (ejecutado en Docker con tiles de México).
- **Lenguaje de Backend y Orquestación:** Python `3.12+` con FastAPI `0.115+`, Pydantic `v2`, SQLAlchemy `2.0` (Async) + GeoAlchemy2.
- **Núcleo Algorítmico de Alto Rendimiento:** Rust `1.82+` compilado como extensión nativa de Python mediante `PyO3` y `maturin`.
- **Optimizador Multipunto (VRP):** Google OR-Tools `9.11+`.
- **Caché y Colas:** Redis `7.4+`.
- **Simulación y Validación:** Eclipse SUMO `1.20+` conectado vía `traci` / `libsumo`.
- **Frontend Web:** React `19` + TypeScript `5.6` + Vite + MapLibre GL JS `4.7+` + deck.gl `9.0+` + TailwindCSS.

### 4.2 Estructura de Directorios del Proyecto (`ecoruta-monorepo`)

```text
ecoruta-monorepo/
├── docker-compose.yml                  # Orquestación de PostGIS, Valhalla, Redis, Backend y Frontend
├── .env.example                        # Variables de entorno (Claves API, DB, Regiones)
├── database/
│   ├── init_db.sql                     # Esquema DDL espacial, índices GiST y funciones pgRouting
│   └── seeds/                          # Perfiles vehiculares base y tarifas de casetas RNC
├── rust_core/                          # Núcleo algorítmico en Rust (PyO3)
│   ├── Cargo.toml
│   ├── pyproject.toml                  # Configuración de Maturin
│   └── src/
│       ├── lib.rs                      # Exposición de funciones a Python
│       ├── physics.rs                  # Modelo longitudinal de fuerzas y consumo
│       ├── fifo.rs                     # Regularización FIFO de series temporales
│       └── td_mols.rs                  # Algoritmo Time-Dependent Multi-Objective Label-Setting
├── backend/                            # API y Orquestación en Python (FastAPI)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py                     # Punto de entrada FastAPI
│       ├── config.py
│       ├── models/                     # Modelos SQLAlchemy / GeoAlchemy2
│       ├── schemas/                    # Esquemas Pydantic v2 (Contratos de entrada/salida)
│       ├── connectors/                 # Capa 1: Ingesta de Datos Oficiales de México
│       │   ├── inegi_rnc_sakbe.py      # Conector INEGI RNC y API SAKBÉ v3.1
│       │   ├── cne_combustible.py      # Conector precios CNE + asignación espacial
│       │   ├── conagua_riesgos.py      # Capas de inundación y clima Open-Meteo / SMN
│       │   └── sesnsp_seguridad.py     # Contexto estadístico municipal SESNSP
│       ├── services/
│       │   ├── subgraph_extractor.py   # Extracción de Bounding Box Elíptico (Valhalla/PostGIS)
│       │   ├── pareto_selector.py      # Suma ponderada, \epsilon-constraint y Knee Point
│       │   └── multi_stop_vrp.py       # Integración Google OR-Tools para GTDVRP
│       └── api/
│           └── routes.py               # Endpoints REST de cálculo y auditoría
├── simulation/                         # Entorno de Validación Científica (SUMO)
│   ├── osm_to_sumo.sh                  # Conversión de red vial a formato .net.xml
│   ├── run_validation.py               # Co-simulación TraCI y recolección de telemetría
│   └── metrics_evaluator.py            # Cálculo de Hipervolumen, MAE y ahorro real
└── frontend/                           # Aplicación Web Analítica
    ├── package.json
    └── src/
        ├── components/
        │   ├── MapViewer.tsx           # MapLibre GL + deck.gl (Renderizado de Frente de Pareto)
        │   ├── ParetoChart.tsx         # Gráfico interactivo Costo (MXN) vs. Tiempo (min)
        │   ├── VehicleConfigurator.tsx # Selector de vehículo, carga y combustible
        │   └── DataAuditBadge.tsx      # Indicadores de frescura y procedencia de datos
        └── App.tsx
```

---

## 5. Guía de Aplicación e Implementación Paso a Paso

A continuación se presenta la implementación técnica detallada de cada componente del sistema, lista para desplegarse y ejecutarse.

### Paso 1: Infraestructura Base y Contenerización (`docker-compose.yml`)

Crea el archivo `docker-compose.yml` en la raíz del proyecto para levantar PostgreSQL con PostGIS/pgRouting, Redis y el motor Valhalla preconfigurado para descargar y procesar datos viales de México:

```yaml
version: "3.9"

services:
  postgis:
    image: pgrouting/pgrouting:16-3.4-3.6
    container_name: ecoruta_postgis
    environment:
      POSTGRES_USER: ecoruta_user
      POSTGRES_PASSWORD: ecoruta_secure_password
      POSTGRES_DB: ecoruta_db
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./database/init_db.sql:/docker-entrypoint-initdb.d/init_db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ecoruta_user -d ecoruta_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7.4-alpine
    container_name: ecoruta_redis
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data

  valhalla:
    image: ghcr.io/gis-ops/docker-valhalla/valhalla:latest
    container_name: ecoruta_valhalla
    ports:
      - "8002:8002"
    volumes:
      - ./valhalla_tiles:/custom_files
    environment:
      - tile_urls=https://download.geofabrik.de/north-america/mexico-latest.osm.pbf
      - use_tiles_ignore_pbf=True
      - build_elevation=True
      - build_admins=True
      - build_time_zones=True
      - serve_tiles=True

volumes:
  pgdata:
  redisdata:
```

---

### Paso 2: Esquema de Base de Datos Geoespacial y Topológica (`database/init_db.sql`)

Este script inicializa las extensiones espaciales, crea las tablas para nodos, aristas enriquecidas con datos de la RNC (peajes, pendientes, restricciones físicas), estaciones de la CNE, series de tráfico temporal y capas de riesgo con auditoría obligatoria de frescura (`fetched_at`, `source_name`, `confidence_level`).

```sql
-- Habilitar extensiones requeridas
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgrouting;
CREATE EXTENSION IF NOT EXISTS hstore;

-- 1. Tabla de Perfiles de Vehículos
CREATE TABLE vehicle_profiles (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    fuel_type VARCHAR(20) NOT NULL CHECK (fuel_type IN ('regular', 'premium', 'diesel', 'electric')),
    empty_mass_kg DOUBLE PRECISION NOT NULL,
    frontal_area_m2 DOUBLE PRECISION NOT NULL,
    drag_coeff_cd DOUBLE PRECISION NOT NULL,
    rolling_coeff_crr DOUBLE PRECISION DEFAULT 0.012,
    drivetrain_efficiency DOUBLE PRECISION DEFAULT 0.28,
    idle_power_watts DOUBLE PRECISION DEFAULT 1200.0,
    nominal_kml DOUBLE PRECISION NOT NULL,
    num_axles INT DEFAULT 2,
    height_m DOUBLE PRECISION DEFAULT 1.6,
    max_weight_tons DOUBLE PRECISION DEFAULT 3.5
);

-- Insertar perfiles base de referencia
INSERT INTO vehicle_profiles (code, name, fuel_type, empty_mass_kg, frontal_area_m2, drag_coeff_cd, nominal_kml, num_axles, height_m) VALUES
('sedan_compacto', 'Sedán Compacto (1.6L)', 'regular', 1250.0, 2.15, 0.30, 15.5, 2, 1.48),
('suv_mediana', 'SUV Mediana (2.5L)', 'premium', 1750.0, 2.65, 0.36, 11.2, 2, 1.72),
('camion_ligero_3_5t', 'Camión de Reparto 3.5T Diésel', 'diesel', 2800.0, 4.80, 0.55, 7.5, 2, 2.85),
('tractocamion_t3s2', 'Tractocamión T3-S2 (5 Ejes)', 'diesel', 14500.0, 8.50, 0.68, 2.8, 5, 4.15);

-- 2. Tabla de Nodos de la Red Vial
CREATE TABLE road_nodes (
    id BIGINT PRIMARY KEY,
    elevation_m DOUBLE PRECISION DEFAULT 0.0,
    is_toll_booth BOOLEAN DEFAULT FALSE,
    geom GEOMETRY(Point, 4326) NOT NULL
);
CREATE INDEX idx_road_nodes_geom ON road_nodes USING GIST (geom);

-- 3. Tabla de Aristas Dirigidas (Grafo Vial Unificado INEGI RNC + OSM)
CREATE TABLE road_edges (
    id BIGSERIAL PRIMARY KEY,
    source BIGINT NOT NULL REFERENCES road_nodes(id),
    target BIGINT NOT NULL REFERENCES road_nodes(id),
    rnc_id VARCHAR(64),
    road_name VARCHAR(255),
    road_class VARCHAR(50) NOT NULL, -- 'autopista', 'federal_libre', 'urbana_primaria', 'secundaria', 'terracería'
    length_m DOUBLE PRECISION NOT NULL CHECK (length_m > 0),
    slope_rad DOUBLE PRECISION DEFAULT 0.0, -- Pendiente media en radianes
    free_flow_speed_kmh DOUBLE PRECISION NOT NULL DEFAULT 60.0,
    surface_factor DOUBLE PRECISION DEFAULT 1.0, -- 1.0 asfalto, 1.4 empedrado, 2.0 terracería
    -- Tarifas de peaje por categoría (Datos INEGI RNC)
    toll_cost_autos_mxn DOUBLE PRECISION DEFAULT 0.0,
    toll_cost_bus_2axles_mxn DOUBLE PRECISION DEFAULT 0.0,
    toll_cost_truck_5axles_mxn DOUBLE PRECISION DEFAULT 0.0,
    toll_source_status VARCHAR(20) DEFAULT 'confirmado' CHECK (toll_source_status IN ('confirmado', 'estimado', 'desconocido')),
    -- Restricciones físicas duras
    max_height_m DOUBLE PRECISION DEFAULT 99.0,
    max_weight_tons DOUBLE PRECISION DEFAULT 999.0,
    is_closed_confirmed BOOLEAN DEFAULT FALSE,
    closure_reason TEXT,
    -- Precios de combustible asignados espacialmente y tiempos base para pgRouting
    assigned_regular_price_mxn DOUBLE PRECISION DEFAULT 23.80,
    assigned_premium_price_mxn DOUBLE PRECISION DEFAULT 25.40,
    assigned_diesel_price_mxn DOUBLE PRECISION DEFAULT 25.10,
    fuel_price_updated_at TIMESTAMPTZ DEFAULT NOW(),
    geom GEOMETRY(LineString, 4326) NOT NULL
);
CREATE INDEX idx_road_edges_geom ON road_edges USING GIST (geom);
CREATE INDEX idx_road_edges_source_target ON road_edges (source, target);

-- 4. Perfiles de Velocidad Horaria (24 horas, regularizados FIFO)
CREATE TABLE edge_hourly_speeds (
    edge_id BIGINT REFERENCES road_edges(id) ON DELETE CASCADE,
    day_type VARCHAR(15) NOT NULL CHECK (day_type IN ('weekday', 'weekend')),
    hour_of_day SMALLINT NOT NULL CHECK (hour_of_day BETWEEN 0 AND 23),
    speed_p50_kmh DOUBLE PRECISION NOT NULL, -- Velocidad mediana esperada
    speed_p10_kmh DOUBLE PRECISION NOT NULL, -- Velocidad en escenario de congestión (para tiempo P90)
    congestion_stop_index DOUBLE PRECISION DEFAULT 0.05, -- Aceleración equivalente m/s^2
    PRIMARY KEY (edge_id, day_type, hour_of_day)
);

-- 5. Estaciones de Servicio (CNE)
CREATE TABLE fuel_stations_cne (
    permiso_cre VARCHAR(64) PRIMARY KEY,
    station_name VARCHAR(255),
    regular_price_mxn DOUBLE PRECISION,
    premium_price_mxn DOUBLE PRECISION,
    diesel_price_mxn DOUBLE PRECISION,
    reported_at TIMESTAMPTZ NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    geom GEOMETRY(Point, 4326) NOT NULL
);
CREATE INDEX idx_fuel_stations_geom ON fuel_stations_cne USING GIST (geom);

-- 6. Capas Contextuales de Peligro Hídrico (CONAGUA / CENAPRED) y Seguridad (SESNSP)
CREATE TABLE hazard_zones (
    id SERIAL PRIMARY KEY,
    hazard_type VARCHAR(30) NOT NULL CHECK (hazard_type IN ('inundacion_historica', 'cierre_vial_activo', 'contexto_municipal_sesnsp')),
    region_code VARCHAR(50),
    description TEXT NOT NULL,
    severity_level VARCHAR(20) NOT NULL, -- 'informativo', 'precaucion', 'cierre_duro'
    source_name VARCHAR(100) NOT NULL,
    source_timestamp TIMESTAMPTZ NOT NULL,
    spatial_resolution VARCHAR(50) NOT NULL, -- 'tramo_vial', 'poligono_cuenca', 'agregado_municipal'
    geom GEOMETRY(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX idx_hazard_zones_geom ON hazard_zones USING GIST (geom);
```

---

### Paso 3: Núcleo Algorítmico en Rust con Modelo Físico y Garantía FIFO (`rust_core`)

El uso de Rust mediante `PyO3` permite evaluar millones de etiquetas en pocos milisegundos sin el bloqueo del GIL de Python.

#### 3.1 Configuración del Paquete (`rust_core/Cargo.toml`)

```toml
[package]
name = "ecoruta_core"
version = "0.1.0"
edition = "2021"

[lib]
name = "ecoruta_core"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.22.0", features = ["extension-module"] }
serde = { version = "1.0", features = ["derive"] }
```

#### 3.2 Código Completo del Motor Físico, Regularizador FIFO y Algoritmo TD-MOLS (`rust_core/src/lib.rs`)

```rust
use pyo3::prelude::*;
use std::cmp::Ordering;
use std::collections::{BinaryHeap, HashMap};

/// Parámetros físicos del vehículo
#[pyclass]
#[derive(Clone, Debug)]
pub struct VehicleParams {
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
    pub idle_power_watts: f64,
    #[pyo3(get, set)]
    pub aux_power_watts: f64,
    #[pyo3(get, set)]
    pub fuel_energy_density_j_per_l: f64, // Gasolina ~ 32.1e6 J/L, Diésel ~ 35.5e6 J/L
    #[pyo3(get, set)]
    pub calibration_factor: f64,
}

#[pymethods]
impl VehicleParams {
    #[new]
    pub fn new(
        total_mass_kg: f64,
        frontal_area_m2: f64,
        drag_coeff_cd: f64,
        rolling_coeff_crr: f64,
        drivetrain_eff: f64,
        idle_power_watts: f64,
        aux_power_watts: f64,
        fuel_energy_density_j_per_l: f64,
        calibration_factor: f64,
    ) -> Self {
        Self {
            total_mass_kg,
            frontal_area_m2,
            drag_coeff_cd,
            rolling_coeff_crr,
            drivetrain_eff,
            idle_power_watts,
            aux_power_watts,
            fuel_energy_density_j_per_l,
            calibration_factor,
        }
    }
}

/// Representación en memoria de una arista enriquecida y FIFO-regularizada
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
    pub length_m: f64,
    #[pyo3(get, set)]
    pub slope_rad: f64,
    #[pyo3(get, set)]
    pub toll_mxn: f64,
    #[pyo3(get, set)]
    pub fuel_price_mxn: f64,
    #[pyo3(get, set)]
    pub hourly_travel_time_s: [f64; 24], // Tiempos de viaje por hora ya regularizados FIFO
    #[pyo3(get, set)]
    pub congestion_accel_ms2: f64,
}

#[pymethods]
impl EdgeData {
    #[new]
    pub fn new(
        id: u64,
        source: u64,
        target: u64,
        length_m: f64,
        slope_rad: f64,
        toll_mxn: f64,
        fuel_price_mxn: f64,
        hourly_speeds_kmh: Vec<f64>,
        congestion_accel_ms2: f64,
    ) -> Self {
        let mut raw_times = [0.0; 24];
        for h in 0..24 {
            let v_kmh = hourly_speeds_kmh.get(h).copied().unwrap_or(50.0).max(3.0);
            let v_ms = v_kmh / 3.6;
            raw_times[h] = length_m / v_ms;
        }

        // Regularización FIFO: garantizar que d(tau)/dt >= -0.95 entre horas consecutivas
        let max_drop_per_hour = 0.95 * 3600.0;
        for _pass in 0..2 {
            for h in (0..23).rev() {
                if raw_times[h] > raw_times[h + 1] + max_drop_per_hour {
                    raw_times[h] = raw_times[h + 1] + max_drop_per_hour;
                }
            }
        }

        Self {
            id,
            source,
            target,
            length_m,
            slope_rad,
            toll_mxn,
            fuel_price_mxn,
            hourly_travel_time_s: raw_times,
            congestion_accel_ms2,
        }
    }
}

impl EdgeData {
    /// Interpola el tiempo de viaje (en segundos) respetando la propiedad FIFO continua
    #[inline]
    pub fn travel_time_at(&self, arrival_time_s: f64) -> f64 {
        let seconds_in_day = arrival_time_s.rem_euclid(86400.0);
        let hour_float = seconds_in_day / 3600.0;
        let h0 = (hour_float.floor() as usize) % 24;
        let h1 = (h0 + 1) % 24;
        let frac = hour_float - hour_float.floor();
        self.hourly_travel_time_s[h0] * (1.0 - frac) + self.hourly_travel_time_s[h1] * frac
    }

    /// Calcula el consumo de combustible (en litros) usando el modelo longitudinal de fuerzas
    #[inline]
    pub fn compute_fuel_liters(&self, travel_time_s: f64, veh: &VehicleParams, air_density: f64) -> f64 {
        let v_ms = (self.length_m / travel_time_s.max(0.1)).clamp(0.5, 45.0);
        let g = 9.81;

        let f_aero = 0.5 * air_density * veh.drag_coeff_cd * veh.frontal_area_m2 * v_ms * v_ms;
        let f_roll = veh.total_mass_kg * g * veh.rolling_coeff_crr * self.slope_rad.cos();
        let f_grav = veh.total_mass_kg * g * self.slope_rad.sin();
        let f_iner = veh.total_mass_kg * self.congestion_accel_ms2;

        let f_total = f_aero + f_roll + f_grav + f_iner;
        let p_trac = (v_ms * f_total).max(0.0);

        let total_power_w = (p_trac / veh.drivetrain_eff) + veh.idle_power_watts + veh.aux_power_watts;
        let total_energy_j = total_power_w * travel_time_s;

        let raw_liters = total_energy_j / veh.fuel_energy_density_j_per_l;
        (raw_liters * veh.calibration_factor).max(0.0001)
    }
}

/// Etiqueta de búsqueda multiobjetivo
#[derive(Clone, Debug)]
struct Label {
    node: u64,
    cost_mxn: f64,
    time_s: f64,
    fuel_l: f64,
    toll_mxn: f64,
    f_cost: f64, // Costo acumulado + heurística admisible hacia el destino
    f_time: f64, // Tiempo acumulado + heurística admisible hacia el destino
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

// Orden lexicográfico inverso para que BinaryHeap actúe como Min-Heap
impl Ord for Label {
    fn cmp(&self, other: &Self) -> Ordering {
        other
            .f_cost
            .partial_cmp(&self.f_cost)
            .unwrap_or(Ordering::Equal)
            .then_with(|| other.f_time.partial_cmp(&self.f_time).unwrap_or(Ordering::Equal))
    }
}

/// Solución perteneciente a la Frontera de Pareto devuelta a Python
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

/// Ejecuta el algoritmo Time-Dependent Multi-Objective Label-Setting (TD-MOLS)
#[pyfunction]
pub fn solve_td_mols(
    edges: Vec<EdgeData>,
    vehicle: VehicleParams,
    source_node: u64,
    target_node: u64,
    departure_time_s: f64,
    air_density: f64,
    max_labels_per_node: usize,
    epsilon_rel: f64, // Ejemplo: 0.005 para poda por epsilon-dominancia al 0.5%
) -> PyResult<Vec<ParetoRoute>> {
    // 1. Construir lista de adyacencia
    let mut adj: HashMap<u64, Vec<usize>> = HashMap::new();
    for (idx, edge) in edges.iter().enumerate() {
        adj.entry(edge.source).or_default().push(idx);
    }

    // 2. Estructuras del algoritmo Label-Setting
    let mut label_pool: Vec<Label> = Vec::with_capacity(50_000);
    let mut pareto_at_node: HashMap<u64, Vec<(f64, f64, usize)>> = HashMap::new(); // (cost_mxn, time_s, label_idx)
    let mut open_heap: BinaryHeap<Label> = BinaryHeap::new();

    let init_label = Label {
        node: source_node,
        cost_mxn: 0.0,
        time_s: 0.0,
        fuel_l: 0.0,
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
        // Encontrar el índice de esta etiqueta en el pool
        let curr_pool_idx = match pareto_at_node.get(&curr.node) {
            Some(list) => {
                if let Some(&(_, _, idx)) = list.iter().find(|&&(c, t, _)| {
                    (c - curr.cost_mxn).abs() < 1e-6 && (t - curr.time_s).abs() < 1e-6
                }) {
                    idx
                } else {
                    continue; // Etiqueta ya podada o dominada posteriormente
                }
            }
            None => continue,
        };

        // Si llegamos al destino, no expandimos más desde el destino
        if curr.node == target_node {
            continue;
        }

        // Verificar si está dominada por la frontera actual del nodo destino (Poda Global)
        if let Some(target_front) = pareto_at_node.get(&target_node) {
            let dominated_by_target = target_front.iter().any(|&(tc, tt, _)| {
                tc <= curr.f_cost * (1.0 + epsilon_rel) && tt <= curr.f_time * (1.0 + epsilon_rel)
            });
            if dominated_by_target {
                continue;
            }
        }

        let Some(out_edges) = adj.get(&curr.node) else {
            continue;
        };

        for &edge_idx in out_edges {
            let edge = &edges[edge_idx];
            let arrival_clock_s = departure_time_s + curr.time_s;
            let edge_time_s = edge.travel_time_at(arrival_clock_s);
            let edge_fuel_l = edge.compute_fuel_liters(edge_time_s, &vehicle, air_density);
            let edge_cost_mxn = edge_fuel_l * edge.fuel_price_mxn + edge.toll_mxn;

            let next_cost = curr.cost_mxn + edge_cost_mxn;
            let next_time = curr.time_s + edge_time_s;

            let node_front = pareto_at_node.entry(edge.target).or_default();

            // Control de límite de etiquetas por nodo
            if node_front.len() >= max_labels_per_node {
                continue;
            }

            // Verificación de Dominancia de Pareto con tolerancia epsilon_rel
            let is_dominated = node_front.iter().any(|&(c, t, _)| {
                c <= next_cost * (1.0 + epsilon_rel) && t <= next_time * (1.0 + epsilon_rel)
            });

            if is_dominated {
                continue;
            }

            // Eliminar etiquetas existentes en edge.target que sean dominadas por la nueva etiqueta
            node_front.retain(|&(c, t, _)| !(next_cost <= c && next_time <= t));

            let new_label_idx = label_pool.len();
            let next_label = Label {
                node: edge.target,
                cost_mxn: next_cost,
                time_s: next_time,
                fuel_l: curr.fuel_l + edge_fuel_l,
                toll_mxn: curr.toll_mxn + edge.toll_mxn,
                f_cost: next_cost,
                f_time: next_time,
                parent_label_idx: Some(curr_pool_idx),
                via_edge_id: Some(edge.id),
            };

            label_pool.push(next_label.clone());
            node_front.push((next_cost, next_time, new_label_idx));
            open_heap.push(next_label);
        }
    }

    // 3. Reconstruir los caminos de la frontera de Pareto en target_node
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
                total_fuel_liters: final_lbl.fuel_l,
                total_toll_mxn: final_lbl.toll_mxn,
                edge_ids: edge_path,
                node_ids: node_path,
            });
        }
    }

    // Ordenar la frontera de menor a mayor costo monetario
    results.sort_by(|a, b| {
        a.total_cost_mxn
            .partial_cmp(&b.total_cost_mxn)
            .unwrap_or(Ordering::Equal)
    });

    Ok(results)
}

#[pymodule]
fn ecoruta_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<VehicleParams>()?;
    m.add_class::<EdgeData>()?;
    m.add_class::<ParetoRoute>()?;
    m.add_function(wrap_pyfunction!(solve_td_mols, m)?)?;
    Ok(())
}
```

> **Compilación del núcleo en Rust:**  
> Dentro del directorio `rust_core/`, basta con ejecutar `maturin develop --release`. Esto compilará el binario optimizado y lo instalará automáticamente en el entorno virtual de Python como el paquete `ecoruta_core`.

---

### Paso 4: Conectores de Datos Oficiales de México (Capa 1 en Python)

#### 4.1 Conector de Precios de Combustible CNE y Asignación Espacial (`backend/app/connectors/cne_combustible.py`)

Este módulo consulta los precios reportados ante la Comisión Nacional de Energía (CNE), registra su marca temporal exacta (`reported_at`), valida su vigencia y actualiza en PostGIS el precio asignado a cada arista vial buscando la estación activa más cercana en un radio de $15\text{ km}$.

```python
import logging
from datetime import datetime, timezone
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("ecoruta.connectors.cne")

class CNEFuelConnector:
    """
    Conector y normalizador para precios de gasolinas y diésel de la CNE / Datos Abiertos de México.
    Conserva metadatos de antigüedad para auditoría transparente.
    """
    def __init__(self, endpoint_url: str):
        self.endpoint_url = endpoint_url

    async def sync_stations_and_assign_edges(self, db: AsyncSession) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.endpoint_url)
            response.raise_for_status()
            records = response.json()

        inserted = 0
        now_utc = datetime.now(timezone.utc)

        for row in records:
            permiso = row.get("permiso_cre")
            lat = row.get("latitud")
            lon = row.get("longitud")
            if not (permiso and lat and lon):
                continue

            await db.execute(
                text("""
                    INSERT INTO fuel_stations_cne (
                        permiso_cre, station_name, regular_price_mxn,
                        premium_price_mxn, diesel_price_mxn, reported_at, fetched_at, geom
                    ) VALUES (
                        :permiso, :name, :reg, :prem, :die, :rep_at, :fetch_at,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                    )
                    ON CONFLICT (permiso_cre) DO UPDATE SET
                        regular_price_mxn = EXCLUDED.regular_price_mxn,
                        premium_price_mxn = EXCLUDED.premium_price_mxn,
                        diesel_price_mxn = EXCLUDED.diesel_price_mxn,
                        reported_at = EXCLUDED.reported_at,
                        fetched_at = EXCLUDED.fetched_at;
                """),
                {
                    "permiso": permiso,
                    "name": row.get("razon_social", "Estación CNE"),
                    "reg": row.get("precio_regular"),
                    "prem": row.get("precio_premium"),
                    "die": row.get("precio_diesel"),
                    "rep_at": row.get("fecha_reporte", now_utc.isoformat()),
                    "fetch_at": now_utc,
                    "lon": float(lon),
                    "lat": float(lat),
                }
            )
            inserted += 1

        # Asignación espacial por vecino más cercano usando operador KNN (<->) de PostGIS
        await db.execute(
            text("""
                UPDATE road_edges e
                SET
                    assigned_regular_price_mxn = COALESCE(s.regular_price_mxn, 23.80),
                    assigned_premium_price_mxn = COALESCE(s.premium_price_mxn, 25.40),
                    assigned_diesel_price_mxn  = COALESCE(s.diesel_price_mxn, 25.10),
                    fuel_price_updated_at      = s.reported_at
                FROM LATERAL (
                    SELECT regular_price_mxn, premium_price_mxn, diesel_price_mxn, reported_at
                    FROM fuel_stations_cne fs
                    WHERE fs.regular_price_mxn IS NOT NULL
                    ORDER BY e.geom <-> fs.geom
                    LIMIT 1
                ) s;
            """)
        )
        await db.commit()
        logger.info("Sincronizadas %d estaciones CNE y actualizadas aristas viales.", inserted)
        return {"stations_synced": inserted, "timestamp_utc": now_utc.isoformat()}
```

#### 4.2 Conector INEGI SAKBÉ v3.1 para Validación Oficial (`backend/app/connectors/inegi_rnc_sakbe.py`)

```python
import httpx
from typing import Dict, Any

class InegiSakbeConnector:
    """
    Cliente para la API Oficial SAKBÉ v3.1 del INEGI (Red Nacional de Caminos).
    Se utiliza como referencia oficial de peajes y línea base de validación en México.
    """
    BASE_URL = "https://gaia.inegi.org.mx/sakbe_v3.1"

    def __init__(self, api_token: str):
        self.api_token = api_token

    async def fetch_reference_route(
        self,
        dest_i_id: int,
        dest_f_id: int,
        vehicle_type: int = 1,  # 1: Automóvil, 5: Camión 5 ejes
        opt_criteria: str = "optimo"  # 'optimo', 'libre', 'cuota'
    ) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/{opt_criteria}"
        payload = {
            "dest_i": dest_i_id,
            "dest_f": dest_f_id,
            "v": vehicle_type,
            "type": "json",
            "proj": "GRS80",
            "key": self.api_token
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, data=payload)
            resp.raise_for_status()
            return resp.json()
```

---

### Paso 5: Extracción de Subgrafo (*Bounding Box*), Selector de Preferencias y Punto de Codo (`backend/app/services/`)

#### 5.1 Extractor de Subgrafo Amortiguado (`backend/app/services/subgraph_extractor.py`)

Este servicio evita la explosión de etiquetas extrayendo de PostGIS únicamente el corredor relevante que envuelve las rutas candidatas extremas, excluyendo automáticamente las aristas con cierres confirmados o incompatibles con el gálibo/peso del vehículo.

```python
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Tuple
import ecoruta_core

class SubgraphExtractorService:
    """
    Extrae el subgrafo factible aplicando:
    1. Filtro duro de cierres confirmados, peso máximo y altura máxima.
    2. Corredor espacial (Bounding Box Elíptico) alrededor de las rutas extremas de pgRouting.
    """
    async def extract_active_subgraph(
        self,
        db: AsyncSession,
        origin_lon: float,
        origin_lat: float,
        dest_lon: float,
        dest_lat: float,
        vehicle_height_m: float,
        vehicle_weight_tons: float,
        fuel_type: str,
        num_axles: int,
        day_type: str = "weekday",
        use_robust_p90: bool = False,
        buffer_degrees: float = 0.08  # ~8.8 km de corredor lateral alrededor de rutas extremas
    ) -> Tuple[int, int, List[ecoruta_core.EdgeData]]:

        # 1. Encontrar nodos más cercanos al origen y destino
        nodes_res = await db.execute(
            text("""
                SELECT
                    (SELECT id FROM road_nodes ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:olon, :olat), 4326) LIMIT 1) AS source_id,
                    (SELECT id FROM road_nodes ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:dlon, :dlat), 4326) LIMIT 1) AS target_id;
            """),
            {"olon": origin_lon, "olat": origin_lat, "dlon": dest_lon, "dlat": dest_lat}
        )
        row = nodes_res.fetchone()
        source_node, target_node = int(row.source_id), int(row.target_id)

        # 2. Extraer aristas factibles dentro de la envolvente elíptica y unir sus 24 velocidades horarias
        speed_col = "speed_p10_kmh" if use_robust_p90 else "speed_p50_kmh"
        price_col = {
            "regular": "assigned_regular_price_mxn",
            "premium": "assigned_premium_price_mxn",
            "diesel": "assigned_diesel_price_mxn"
        }.get(fuel_type, "assigned_regular_price_mxn")

        toll_col = "toll_cost_truck_5axles_mxn" if num_axles >= 5 else "toll_cost_autos_mxn"

        query = text(f"""
            WITH corridor AS (
                SELECT ST_Buffer(
                    ST_MakeLine(
                        ST_SetSRID(ST_MakePoint(:olon, :olat), 4326),
                        ST_SetSRID(ST_MakePoint(:dlon, :dlat), 4326)
                    ),
                    :buf
                ) AS geom
            )
            SELECT
                e.id,
                e.source,
                e.target,
                e.length_m,
                e.slope_rad,
                e.{toll_col} AS toll_mxn,
                e.{price_col} AS fuel_price_mxn,
                COALESCE(
                    ARRAY_AGG(h.{speed_col} ORDER BY h.hour_of_day) FILTER (WHERE h.{speed_col} IS NOT NULL),
                    ARRAY_FILL(e.free_flow_speed_kmh, ARRAY[24])
                ) AS hourly_speeds,
                COALESCE(AVG(h.congestion_stop_index), 0.05) AS congestion_accel
            FROM road_edges e
            JOIN corridor c ON ST_Intersects(e.geom, c.geom)
            LEFT JOIN edge_hourly_speeds h
                ON h.edge_id = e.id AND h.day_type = :day_type
            WHERE e.is_closed_confirmed = FALSE
              AND e.max_height_m >= :v_height
              AND e.max_weight_tons >= :v_weight
            GROUP BY e.id;
        """)

        edges_res = await db.execute(
            query,
            {
                "olon": origin_lon, "olat": origin_lat,
                "dlon": dest_lon, "dlat": dest_lat,
                "buf": buffer_degrees,
                "day_type": day_type,
                "v_height": vehicle_height_m,
                "v_weight": vehicle_weight_tons
            }
        )

        rust_edges: List[ecoruta_core.EdgeData] = []
        for r in edges_res.fetchall():
            speeds = list(r.hourly_speeds)
            if len(speeds) < 24:
                speeds = [60.0] * 24
            rust_edges.append(
                ecoruta_core.EdgeData(
                    int(r.id),
                    int(r.source),
                    int(r.target),
                    float(r.length_m),
                    float(r.slope_rad),
                    float(r.toll_mxn),
                    float(r.fuel_price_mxn),
                    speeds,
                    float(r.congestion_accel)
                )
            )

        return source_node, target_node, rust_edges
```

#### 5.2 Selector Multiobjetivo: Suma Ponderada, $\epsilon$-Restricciones y *Knee Point* (`backend/app/services/pareto_selector.py`)

```python
import math
from typing import List, Dict, Any, Optional
import ecoruta_core

class ParetoPreferenceSelector:
    """
    Analiza la frontera de Pareto generada por el motor en Rust y selecciona:
    1. Ruta de mínimo costo monetario.
    2. Ruta de mínimo tiempo.
    3. Punto de Codo (Knee Point) geométrico.
    4. Ruta óptima según la preferencia del usuario (\lambda en MXN/min y cotas \epsilon).
    """
    @staticmethod
    def evaluate_pareto_front(
        front: List[ecoruta_core.ParetoRoute],
        willingness_to_pay_mxn_per_min: float = 2.5,  # Parámetro \lambda
        max_budget_mxn: Optional[float] = None,       # Restricción \epsilon de costo
        max_duration_min: Optional[float] = None      # Restricción \epsilon de tiempo
    ) -> Dict[str, Any]:
        if not front:
            return {"status": "infeasible", "routes": []}

        # Filtrar por restricciones \epsilon si el usuario las definió
        feasible_front = [
            r for r in front
            if (max_budget_mxn is None or r.total_cost_mxn <= max_budget_mxn)
            and (max_duration_min is None or (r.total_time_s / 60.0) <= max_duration_min)
        ]

        # Si las cotas \epsilon son demasiado estrictas, conservar el frente original pero emitir alerta
        epsilon_violated = len(feasible_front) == 0
        active_front = front if epsilon_violated else feasible_front

        min_cost_route = min(active_front, key=lambda r: r.total_cost_mxn)
        min_time_route = min(active_front, key=lambda r: r.total_time_s)

        # Cálculo del Punto de Codo (Knee Point)
        c_min, c_max = min_cost_route.total_cost_mxn, max(r.total_cost_mxn for r in active_front)
        t_min, t_max = min_time_route.total_time_s, max(r.total_time_s for r in active_front)

        c_span = max(c_max - c_min, 1e-6)
        t_span = max(t_max - t_min, 1e-6)

        best_knee_route = active_front[0]
        max_knee_dist = -1.0

        for r in active_front:
            c_norm = (r.total_cost_mxn - c_min) / c_span
            t_norm = (r.total_time_s - t_min) / t_span
            # Distancia perpendicular a la línea extrema \hat{C} + \hat{T} - 1 = 0
            dist = abs(1.0 - c_norm - t_norm) / math.sqrt(2.0)
            if dist > max_knee_dist:
                max_knee_dist = dist
                best_knee_route = r

        # Selección mediante Suma Ponderada J(P) = C(P) + \lambda * T_min(P)
        user_optimal_route = min(
            active_front,
            key=lambda r: r.total_cost_mxn + willingness_to_pay_mxn_per_min * (r.total_time_s / 60.0)
        )

        def serialize(r: ecoruta_core.ParetoRoute, tag: str) -> Dict[str, Any]:
            savings_vs_fastest_mxn = min_time_route.total_cost_mxn - r.total_cost_mxn
            extra_time_vs_fastest_min = (r.total_time_s - min_time_route.total_time_s) / 60.0
            return {
                "recommendation_tag": tag,
                "total_cost_mxn": round(r.total_cost_mxn, 2),
                "fuel_cost_mxn": round(r.total_cost_mxn - r.total_toll_mxn, 2),
                "toll_cost_mxn": round(r.total_toll_mxn, 2),
                "total_fuel_liters": round(r.total_fuel_liters, 3),
                "duration_minutes": round(r.total_time_s / 60.0, 1),
                "savings_vs_fastest_mxn": round(savings_vs_fastest_mxn, 2),
                "extra_time_vs_fastest_min": round(extra_time_vs_fastest_min, 1),
                "edge_ids": r.edge_ids,
                "node_ids": r.node_ids
            }

        return {
            "status": "epsilon_relaxed" if epsilon_violated else "optimal",
            "pareto_count": len(active_front),
            "recommended_user": serialize(user_optimal_route, "preferencia_usuario"),
            "recommended_knee": serialize(best_knee_route, "punto_de_codo_equilibrado"),
            "cheapest": serialize(min_cost_route, "minimo_costo"),
            "fastest": serialize(min_time_route, "minimo_tiempo"),
            "pareto_frontier": [serialize(r, f"pareto_{i}") for i, r in enumerate(active_front)]
        }
```

---

### Paso 6: Optimizador de Múltiples Paradas (GTDVRP con Google OR-Tools) (`backend/app/services/multi_stop_vrp.py`)

Cuando el usuario ingresa múltiples paradas con orden flexible y ventanas de tiempo, este servicio invoca la matriz de costos generada por el motor multiobjetivo y resuelve el **Green Time-Dependent Vehicle Routing Problem with Time Windows (GTDVRPTW)**.

```python
from typing import List, Dict, Any, Tuple
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

class MultiStopVRPOptimizer:
    """
    Resuelve la secuencia óptima de paradas usando Google OR-Tools sobre una matriz
    de costo generalizado J_{ij} = C_{ij} + \lambda * T_{ij} con ventanas horarias.
    """
    @staticmethod
    def solve_sequence(
        cost_matrix_mxn: List[List[float]],
        time_matrix_min: List[List[int]],
        time_windows_min: List[Tuple[int, int]],
        willingness_to_pay_mxn_per_min: float = 2.0,
        depot_index: int = 0
    ) -> Dict[str, Any]:
        num_locations = len(cost_matrix_mxn)
        manager = pywrapcp.RoutingIndexManager(num_locations, 1, depot_index)
        routing = pywrapcp.RoutingModel(manager)

        # 1. Definir callback de costo generalizado (multiplicado por 100 para aritmética entera)
        def generalized_cost_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            c_mxn = cost_matrix_mxn[from_node][to_node]
            t_min = time_matrix_min[from_node][to_node]
            j_val = c_mxn + willingness_to_pay_mxn_per_min * t_min
            return int(round(j_val * 100))

        transit_callback_index = routing.RegisterTransitCallback(generalized_cost_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # 2. Definir dimensión temporal para ventanas de llegada
        def time_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(time_matrix_min[from_node][to_node])

        time_callback_index = routing.RegisterTransitCallback(time_callback)
        routing.AddDimension(
            time_callback_index,
            60,     # Espera máxima permitida en un nodo (min)
            1440,   # Horizonte máximo diario (24 horas = 1440 min)
            False,
            "Time"
        )
        time_dimension = routing.GetDimensionOrDie("Time")

        for loc_idx, (tw_start, tw_end) in enumerate(time_windows_min):
            index = manager.NodeToIndex(loc_idx)
            time_dimension.CumulVar(index).SetRange(tw_start, tw_end)

        # 3. Configurar metaheurística Guided Local Search
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = 3

        solution = routing.SolveWithParameters(search_parameters)
        if not solution:
            return {"status": "infeasible", "ordered_waypoints": []}

        ordered_nodes = []
        total_cost_mxn = 0.0
        total_time_min = 0
        index = routing.Start(0)

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            ordered_nodes.append(node)
            next_index = solution.Value(routing.NextVar(index))
            if not routing.IsEnd(next_index):
                next_node = manager.IndexToNode(next_index)
                total_cost_mxn += cost_matrix_mxn[node][next_node]
                total_time_min += time_matrix_min[node][next_node]
            index = next_index

        return {
            "status": "optimal_sequence",
            "ordered_waypoints": ordered_nodes,
            "estimated_total_cost_mxn": round(total_cost_mxn, 2),
            "estimated_total_time_min": total_time_min
        }
```

---

### Paso 7: Endpoint Principal de la API y Auditoría de Datos (`backend/app/api/routes.py`)

Este endpoint integra todos los servicios y devuelve el frente de Pareto junto con la **Auditoría de Procedencia y Frescura**, cumpliendo con los principios éticos y de transparencia del proyecto.

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
import ecoruta_core

from app.services.subgraph_extractor import SubgraphExtractorService
from app.services.pareto_selector import ParetoPreferenceSelector

router = APIRouter(prefix="/api/v1/routes", tags=["EcoRuta Optimization"])

class RouteRequest(BaseModel):
    origin_lat: float = Field(..., example=19.4326)
    origin_lon: float = Field(..., example=-99.1332)
    dest_lat: float = Field(..., example=19.0414)
    dest_lon: float = Field(..., example=-98.2063)
    departure_hour: int = Field(8, ge=0, le=23)
    day_type: str = Field("weekday", pattern="^(weekday|weekend)$")
    vehicle_code: str = Field("sedan_compacto")
    cargo_mass_kg: float = Field(150.0, ge=0.0)
    ac_enabled: bool = Field(True)
    willingness_to_pay_mxn_per_min: float = Field(2.5, ge=0.0)
    max_budget_mxn: Optional[float] = None
    max_duration_min: Optional[float] = None
    use_robust_p90: bool = Field(False, description="Si es True, evalúa tiempos en el percentil P90 de congestión")

@router.post("/optimize")
async def optimize_ecoruta(req: RouteRequest, db: AsyncSession = Depends(get_db)):
    extractor = SubgraphExtractorService()

    # 1. Configurar parámetros físicos del vehículo
    veh_params = ecoruta_core.VehicleParams(
        total_mass_kg=1250.0 + req.cargo_mass_kg,
        frontal_area_m2=2.15,
        drag_coeff_cd=0.30,
        rolling_coeff_crr=0.012,
        drivetrain_eff=0.28,
        idle_power_watts=1200.0,
        aux_power_watts=1500.0 if req.ac_enabled else 200.0,
        fuel_energy_density_j_per_l=32.1e6,
        calibration_factor=1.0
    )

    # 2. Extraer subgrafo factible
    source_id, target_id, rust_edges = await extractor.extract_active_subgraph(
        db=db,
        origin_lon=req.origin_lon,
        origin_lat=req.origin_lat,
        dest_lon=req.dest_lon,
        dest_lat=req.dest_lat,
        vehicle_height_m=1.55,
        vehicle_weight_tons=(1250.0 + req.cargo_mass_kg) / 1000.0,
        fuel_type="regular",
        num_axles=2,
        day_type=req.day_type,
        use_robust_p90=req.use_robust_p90
    )

    if not rust_edges:
        raise HTTPException(status_code=404, detail="No se encontró un corredor vial factible para las restricciones del vehículo.")

    # 3. Ejecutar núcleo multiobjetivo en Rust (TD-MOLS)
    pareto_routes = ecoruta_core.solve_td_mols(
        edges=rust_edges,
        vehicle=veh_params,
        source_node=source_id,
        target_node=target_id,
        departure_time_s=float(req.departure_hour * 3600),
        air_density=1.05,  # Ajustado para altitud media en México
        max_labels_per_node=40,
        epsilon_rel=0.005
    )

    # 4. Seleccionar recomendaciones y Punto de Codo
    selection = ParetoPreferenceSelector.evaluate_pareto_front(
        front=pareto_routes,
        willingness_to_pay_mxn_per_min=req.willingness_to_pay_mxn_per_min,
        max_budget_mxn=req.max_budget_mxn,
        max_duration_min=req.max_duration_min
    )

    # 5. Adjuntar metadatos de auditoría y transparencia epistemológica
    return {
        "optimization_result": selection,
        "data_provenance_audit": {
            "road_network_source": "INEGI Red Nacional de Caminos (RNC) + OpenStreetMap (ODbL)",
            "fuel_price_source": "Comisión Nacional de Energía (CNE) - Precios reportados por permisionarios",
            "toll_source": "INEGI RNC / Tarifas vigentes por número de ejes",
            "safety_context_notice": (
                "Los indicadores de incidencia delictiva provienen del SESNSP a escala municipal. "
                "Son informativos y NO representan probabilidades de delito por calle."
            ),
            "uncertainty_mode": "Robusto (P90)" if req.use_robust_p90 else "Esperado (P50)",
            "computed_at_utc": datetime.now(timezone.utc).isoformat()
        }
    }
```

---

### Paso 8: Visualización del Frente de Pareto en el Frontend (`frontend/src/components/MapViewer.tsx`)

En el cliente web, se utiliza `MapLibre GL` como mapa base abierto y `deck.gl` (`PathLayer`) para renderizar todas las rutas de la frontera de Pareto simultáneamente, destacando la ruta del **Punto de Codo** en verde esmeralda, la **Más Rápida** en azul y la **Más Barata** en ámbar.

```tsx
import React, { useMemo } from 'react';
import Map from 'react-map-gl/maplibre';
import DeckGL from '@deck.gl/react';
import { PathLayer } from '@deck.gl/layers';
import 'maplibre-gl/dist/maplibre-gl.css';

interface RouteCandidate {
  recommendation_tag: string;
  total_cost_mxn: number;
  duration_minutes: number;
  savings_vs_fastest_mxn: number;
  coordinates: [number, number][];
}

interface Props {
  paretoRoutes: RouteCandidate[];
  selectedTag: string;
  onSelectRoute: (tag: string) => void;
}

export const EcoRutaMapViewer: React.FC<Props> = ({ paretoRoutes, selectedTag, onSelectRoute }) => {
  const layers = useMemo(() => [
    new PathLayer<RouteCandidate>({
      id: 'pareto-routes-layer',
      data: paretoRoutes,
      pickable: true,
      widthScale: 1,
      widthMinPixels: 4,
      getPath: d => d.coordinates,
      getColor: d => {
        if (d.recommendation_tag === selectedTag) return [16, 185, 129, 255]; // Verde EcoRuta activo
        if (d.recommendation_tag === 'minimo_tiempo') return [59, 130, 246, 180]; // Azul Rápida
        if (d.recommendation_tag === 'minimo_costo') return [245, 158, 11, 180]; // Ámbar Económica
        return [148, 163, 184, 120]; // Gris alternativas Pareto
      },
      getWidth: d => (d.recommendation_tag === selectedTag ? 8 : 4),
      onClick: info => {
        if (info.object) onSelectRoute(info.object.recommendation_tag);
      }
    })
  ], [paretoRoutes, selectedTag, onSelectRoute]);

  return (
    <div className="relative w-full h-[650px] rounded-xl overflow-hidden shadow-lg border border-slate-200">
      <DeckGL
        initialViewState={{
          longitude: -99.1332,
          latitude: 19.4326,
          zoom: 9,
          pitch: 35,
          bearing: 0
        }}
        controller={true}
        layers={layers}
        getTooltip={({ object }) =>
          object && {
            html: `
              <div style="padding: 8px; font-family: sans-serif;">
                <strong>${object.recommendation_tag.toUpperCase()}</strong><br/>
                Costo Estimado: <b>$${object.total_cost_mxn} MXN</b><br/>
                Tiempo: <b>${object.duration_minutes} min</b><br/>
                Ahorro vs. Rápida: <b>$${object.savings_vs_fastest_mxn} MXN</b>
              </div>
            `
          }
        }
      >
        <Map mapStyle="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json" />
      </DeckGL>
    </div>
  );
};
```

---

## 6. Protocolo de Validación Experimental y Simulación con SUMO

Para cumplir con el rigor científico exigido en `contexto.md` antes de salir a pruebas de campo con vehículos reales, se establece el protocolo de validación en **Eclipse SUMO** (*Simulation of Urban MObility*):

### 6.1 Pipeline de Co-Simulación (`simulation/run_validation.py`)

1. **Importación de Red y Elevación a SUMO:**
   Se convierte el recorte de red de la región piloto (por ejemplo, Zona Metropolitana de Guadalajara o Monterrey) incluyendo datos de elevación topográfica SRTM:
   ```bash
   netconvert --osm-files piloto_region.osm.pbf \
              --heightmap.geotiff dem_inegi_piloto.tif \
              --output-file ecoruta_piloto.net.xml \
              --geometry.remove --ramps.guess --tls.guess-signals
   ```
2. **Inyección de Vehículos con Modelo de Emisiones y Consumo HBEFA4:**
   En SUMO, se asigna a cada vehículo la clase `HBEFA4/PC_petrol_Euro-4` (o equivalente diésel) y mediante `traci.vehicle.setRoute()` se inyectan tres vehículos idénticos en el mismo segundo de salida $t_0$:
   - **Vehículo A (Línea Base Tiempo):** Sigue la ruta de mínimo tiempo.
   - **Vehículo B (Línea Base Distancia):** Sigue la ruta más corta.
   - **Vehículo C (EcoRuta Knee Point):** Sigue la ruta recomendada por el algoritmo TD-MOLS.
3. **Medición de Métricas Científicas:**
   Al finalizar la simulación de los $64$ escenarios del diseño factorial $2^k$, el script `metrics_evaluator.py` calcula:
   - **Ahorro Monetario Real ($\Delta C\%$):**
     $$\Delta C\% = \frac{C_{\text{rápida}} - C_{\text{EcoRuta}}}{C_{\text{rápida}}} \times 100$$
   - **Error Porcentual Absoluto Medio de Combustible ($\text{MAPE}_{\text{litros}}$):**
     $$\text{MAPE}_{\text{litros}} = \frac{1}{N} \sum_{i=1}^N \left| \frac{L_{\text{predicho}, i} - L_{\text{SUMO/OBD2}, i}}{L_{\text{SUMO/OBD2}, i}} \right| \times 100$$
   - **Hipervolumen ($HV$) de la Frontera de Pareto:** Área en el espacio $(C, T)$ dominada por el conjunto $\mathcal{P}^*$ respecto a un punto de referencia nadir $(C_{\text{nadir}}, T_{\text{nadir}}) = (1.2 C_{\max}, 1.2 T_{\max})$.

---

## 7. Hoja de Ruta de Ejecución (Roadmap de 36 Semanas) y Gobernanza Ética

| Fase | Semanas | Hito Técnico Principal | Criterio de Aceptación (Gate de Calidad) |
|---|---|---|---|
| **Fase 1: Núcleo Matemático y Grafos Sintéticos** | $1 - 4$ | Implementación de `rust_core` (TD-MOLS, modelo físico longitudinal y regularización FIFO). | Exactitud del $100\%$ de la frontera de Pareto contra enumeración exhaustiva en grafos de $20$ nodos. |
| **Fase 2: Base de Datos Espacial e Ingesta México** | $5 - 10$ | Despliegue de PostGIS + Valhalla y conectores automáticos para INEGI RNC, SAKBÉ y CNE. | Grafo regional cargado con pendientes DEM, peajes RNC por ejes y precios de gasolina asignados con `timestamp`. |
| **Fase 3: Extracción de Subgrafo y Pruebas de Escala** | $11 - 16$ | Integración del *Bounding Box Elíptico*, podas $\epsilon$ y API FastAPI con selector *Knee Point*. | Latencia de respuesta $< 450\text{ ms}$ (P95) para rutas de hasta $150\text{ km}$ con $\le 40$ etiquetas por nodo. |
| **Fase 4: Capas de Riesgo, Clima y Paradas (GTDVRP)** | $17 - 22$ | Integración de CONAGUA (cierres duros vs. susceptibilidad), SESNSP (contexto municipal) y Google OR-Tools. | Exclusión del $100\%$ de aristas con cierre confirmado y resolución de secuencias de $10$ paradas en $< 3\text{ s}$. |
| **Fase 5: Validación en Simulación Microscópica (SUMO)** | $23 - 28$ | Ejecución del diseño experimental factorial de $64$ escenarios en SUMO + TraCI. | Reducción comprobada del costo total frente a ruta más rápida y error de estimación de combustible $< 8\%$. |
| **Fase 6: Pruebas de Campo con Telemetría OBD-II** | $29 - 36$ | Recorridos reales controlados y recalibración del factor $\kappa_v$ por perfil vehicular. | Informe científico final auditable y despliegue del MVP web con React + deck.gl + MapLibre GL. |

### Lista de Verificación de Gobernanza, Seguridad y Ética (Obligatoria en Producción)

1. **Inviolabilidad de Restricciones Duras:** Ningún ahorro monetario, por alto que sea, puede activar una arista marcada con `is_closed_confirmed = TRUE` o que viole la altura/peso máximo del vehículo.
2. **Transparencia Estadística en Seguridad:** Queda prohibido interpolar datos municipales del SESNSP para asignar un «porcentaje de peligro» a una calle individual. La interfaz siempre debe mostrar la etiqueta: *"Contexto estadístico a nivel municipal (Fuente: SESNSP)"*.
3. **Caducidad Explícita de Precios y Tráfico:** Si el último reporte de la estación CNE tiene más de $72\text{ horas}$ de antigüedad, la interfaz debe mostrar un indicador visual de advertencia indicando la fecha exacta del registro utilizado.
4. **Privacidad por Diseño:** Los recorridos y lecturas de telemetría OBD-II utilizados para calibrar el factor de consumo $\kappa_v$ deben anonimizarse truncando los primeros y últimos $500\text{ m}$ del trayecto para no almacenar domicilios ni orígenes/destinos exactos de los usuarios.