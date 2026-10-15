# EcoRuta — Stack Tecnológico Recomendado: Análisis y Justificación

**Documento complementario al análisis teórico profundo**  
**Fecha:** 14 de octubre de 2026  
**Propósito:** seleccionar las tecnologías más adecuadas para cada capa del sistema EcoRuta, con base en el análisis previo y en evidencia técnica actualizada


## 1. Criterios de selección

La elección de tecnologías para EcoRuta no puede basarse únicamente en popularidad. Dado que el sistema combina optimización multiobjetivo, datos geoespaciales, enrutamiento dependiente del tiempo y validación experimental, los criterios rectores son:

1. **Flexibilidad de costos dinámicos.** El motor debe permitir modificar los costos de las aristas en tiempo de consulta, sin reconstruir el grafo. Esto es esencial porque EcoRuta evalúa costo monetario, tiempo y otras dimensiones que varían con el vehículo, la hora y el contexto.

2. **Compatibilidad con fuentes de datos mexicanas.** La solución debe integrarse con la Red Nacional de Caminos (RNC) del INEGI, los precios de combustible de la CNE y, cuando sea viable, con datos de tráfico disponibles para México.

3. **Escalabilidad comprobada.** El sistema debe manejar redes de tamaño relevante (miles a millones de nodos) sin degradación inaceptable del rendimiento.

4. **Licencia permisiva y costo sostenible.** Para un proyecto de investigación, las licencias abiertas y los costos controlados son preferibles. Las APIs comerciales se reservan para componentes donde no existe alternativa abierta viable.

5. **Ecosistema y comunidad.** La tecnología debe tener documentación sólida, comunidad activa y actualizaciones recientes, para minimizar el riesgo de obsolescencia.


## 2. Stack recomendado por capa

### 2.1 Almacenamiento y procesamiento geoespacial

| Tecnología | Rol en EcoRuta | Justificación | Alternativas descartadas |
|---|---|---|---|
| **PostgreSQL + PostGIS** | Base de datos relacional geoespacial para nodos, aristas, atributos estáticos y resultados de optimización | PostGIS es el estándar de facto para datos geoespaciales en bases de datos relacionales. Soporta índices espaciales (GiST, SP-GiST), tipos de geometría, y consultas SQL espaciales. Se integra nativamente con pgRouting. | MongoDB con GeoJSON (menos maduro para operaciones espaciales complejas); bases de datos de grafos puras (Neo4j, TigerGraph) son menos adecuadas porque EcoRuta requiere operaciones relacionales y geoespaciales, no solo traversal de grafos. |
| **pgRouting** | Extensión de PostgreSQL para cálculo de rutas y análisis de redes directamente en la base de datos | pgRouting extiende PostGIS/PostgreSQL para proporcionar funcionalidad de enrutamiento y análisis de redes. Implementa algoritmos de camino mínimo (Dijkstra, A*, bidireccional) y ha recibido contribuciones recientes, incluyendo la función `pgr_contractionHierarchies` añadida por Oslandia en 2025. Su ventaja principal es que todos los cálculos se realizan en la base de datos, sin necesidad de instalar herramientas adicionales. | Implementaciones en Python puro (NetworkX) tienen rendimiento muy inferior para grafos grandes; motores como OSRM o Valhalla están optimizados para consultas de usuario final, no para análisis batch. |
| **Apache Sedona** (opcional, fase avanzada) | Procesamiento distribuido de datos geoespaciales a gran escala | Si EcoRuta escala a millones de segmentos viales o requiere análisis de patrones de tráfico a escala nacional, Sedona proporciona capacidades de procesamiento distribuido sobre Spark. Para el MVP, PostgreSQL/PostGIS es suficiente. | GeoMesa es una alternativa para consultas espacio-temporales distribuidas, pero añade complejidad operativa que no se justifica en etapas tempranas. |

**Decisión para el MVP:** PostgreSQL + PostGIS + pgRouting. Esta combinación permite almacenar la red vial, calcular rutas de referencia (Dijkstra para tiempo mínimo, costo mínimo) y ejecutar análisis exploratorios sin infraestructura adicional. Para el algoritmo multiobjetivo propio, se recomienda implementarlo en un servicio separado que lea el grafo desde PostgreSQL.


### 2.2 Motores de enrutamiento

| Tecnología | Rol en EcoRuta | Justificación | Alternativas descartadas |
|---|---|---|---|
| **Valhalla** | Motor de enrutamiento base para obtener geometrías y candidatos de ruta | Valhalla utiliza **costos dinámicos en tiempo de ejecución**: mantiene atributos ricos en el grafo y calcula los costos según un modelo de costo pasado en la consulta, sin necesidad de reconstruir el grafo. Esto es esencial para EcoRuta, donde los costos dependen del vehículo, la hora, el precio del combustible y las condiciones de tráfico. Valhalla soporta múltiples perfiles (automóvil, camión, motocicleta, bicicleta, peatón) y funcionalidades avanzadas como isócronas, matrices y optimización de rutas. Su licencia MIT es permisiva. | OSRM es más rápido para consultas con perfil fijo, pero su arquitectura precomputa los costos, lo que impide modificar el modelo de costo en tiempo de consulta. Si EcoRuta utilizara OSRM, necesitaría reconstruir el grafo para cada perfil de vehículo o condición de tráfico, lo cual es inviable. GraphHopper es una alternativa viable, pero su flexibilidad de costos es menor que la de Valhalla. |
| **SAKBÉ (INEGI)** | Fuente oficial de rutas para México y validación cruzada | La API de Ruteo del INEGI, versión 3.1, utiliza la Red Nacional de Caminos y está diseñada para sistemas inteligentes de transporte. Los parámetros se envían mediante POST e incluyen tipo de sistema de referencia (GRS80 o MERC) y token de usuario. La RNC incluye información de peajes por tipo de vehículo y número de ejes, así como ubicación de gasolineras. Es una fuente oficial mexicana que no depende de proveedores comerciales. | Google Maps Platform y HERE son alternativas comerciales con mayor cobertura de tráfico, pero su uso está sujeto a costos y condiciones contractuales. Para el MVP, SAKBÉ ofrece una línea base gratuita y oficial. |
| **OpenRouteService (ORS)** | Alternativa de código abierto con servicio listo para usar | ORS es un servicio completo construido sobre GraphHopper y open-elevation, con perfiles extensos (automóvil, bicicleta, peatón, vehículos pesados) y funcionalidades ricas (isócronas, matrices, búsqueda de POI). Puede ser útil para comparación o como respaldo si Valhalla presenta problemas de configuración. | Requiere una instancia propia para uso intensivo; la versión pública tiene límites de uso. |

**Decisión para el MVP:** Valhalla como motor principal, con SAKBÉ como fuente de validación para México. OSRM puede considerarse si el rendimiento se vuelve crítico y los perfiles de vehículo son limitados.


### 2.3 Algoritmos de optimización

| Tecnología | Rol en EcoRuta | Justificación | Alternativas descartadas |
|---|---|---|---|
| **Algoritmo de etiquetado label-setting (implementación propia)** | Núcleo multiobjetivo para generar la frontera de Pareto costo-tiempo | El algoritmo de etiquetado label-setting es la familia dominante para resolver el Problema de Camino Mínimo Multiobjetivo (MOSP) de forma exacta. Mantiene, para cada nodo, un conjunto de etiquetas no dominadas y aplica podas por dominancia. La implementación propia permite adaptar el algoritmo a las particularidades de EcoRuta (costos dependientes del tiempo, restricciones de vehículo, múltiples objetivos). La literatura reciente (Bazgan et al., 2025; Kergosien et al., 2022) proporciona la base algorítmica y las condiciones de correctitud. | Implementaciones genéricas de MOSP (por ejemplo, en bibliotecas de optimización) no están adaptadas a las necesidades específicas de enrutamiento vial. El algoritmo de etiquetado es suficientemente conocido como para implementarlo con garantías. |
| **Google OR-Tools** | Optimizador de secuencia de visitas (TSP/VRP con ventanas de tiempo) | OR-Tools es la biblioteca de referencia para problemas de rutas de vehículos. Implementa modelos de VRP con ventanas de tiempo, capacidades, múltiples vehículos y depósitos. Estudios de 2025 evalúan su rendimiento en problemas de VRP con ventanas de tiempo, confirmando su utilidad para instancias de pequeña y mediana escala. Para EcoRuta, OR-Tools se integraría como una capa separada que utiliza una matriz de costos generada por el motor de camino mínimo. | NSGA-II y algoritmos evolutivos propios pueden ser apropiados para instancias muy grandes o cuando la matriz de costos depende de la secuencia, pero OR-Tools ofrece una solución más robusta y probada para el caso estándar. |
| **pymoo** | Framework de optimización multiobjetivo para experimentación y comparación | pymoo implementa NSGA-II, NSGA-III, MOEA/D y otros algoritmos multiobjetivo con una API moderna y documentación completa. Su uso se recomienda para investigación exploratoria y para comparar el rendimiento de NSGA-II frente al algoritmo de etiquetado exacto en instancias pequeñas. No se recomienda como núcleo del sistema en producción, porque los algoritmos evolutivos no garantizan optimalidad. | DEAP es una alternativa más antigua con menor rendimiento en benchmarks comparativos. Para experimentación académica, pymoo es la opción actual. |
| **Implementación de Dijkstra/A*** | Líneas base de un solo objetivo | Dijkstra y A* son indispensables como referencias para validar el algoritmo multiobjetivo. Se pueden implementar en el mismo lenguaje que el núcleo (Python o Rust) o utilizar las versiones de pgRouting. Su valor es servir como punto de comparación para medir el beneficio de la optimización multiobjetivo. | No aplica; son algoritmos fundamentales que deben estar presentes. |

**Decisión para el MVP:** Algoritmo de etiquetado label-setting implementado en Python (con posibilidad de migrar a Rust si el rendimiento lo requiere), Dijkstra como línea base, y OR-Tools para la capa de optimización de paradas cuando se incorpore.


### 2.4 Lenguajes de programación

| Lenguaje | Rol en EcoRuta | Justificación | Alternativas descartadas |
|---|---|---|---|
| **Python** | Lenguaje principal para prototipado, integración y capa de aplicación | Python ofrece el ecosistema más rico para computación científica, aprendizaje automático, procesamiento de datos y desarrollo web. Bibliotecas como NumPy, SciPy, pandas, pymoo, NetworkX y OR-Tools facilitan la experimentación rápida. Para el MVP, Python es adecuado porque permite iterar sobre el diseño del algoritmo sin la sobrecarga de un lenguaje compilado. | Si el rendimiento del algoritmo de etiquetado se vuelve un cuello de botella, se puede migrar el núcleo a Rust o C++ manteniendo Python como capa de orquestación. |
| **Rust** | Lenguaje recomendado para el núcleo de rendimiento crítico (fase de producción) | Rust ofrece rendimiento comparable a C++ con seguridad de memoria. Bibliotecas como `rustworkx` proporcionan estructuras de grafos de alto rendimiento. Un estudio de 2025 reporta que una implementación en Rust con bindings de Python a través de PyO3 logra aproximadamente **10x de speedup** sobre implementaciones en Python puro. Para el algoritmo de etiquetado multiobjetivo, que puede explorar millones de etiquetas, este rendimiento es esencial. | C++ es una alternativa con rendimiento similar, pero su gestión manual de memoria y su ecosistema de herramientas menos moderno lo hacen menos atractivo para un proyecto nuevo. |
| **TypeScript/JavaScript** | Frontend y visualización | El frontend de EcoRuta (interfaz de usuario, mapas interactivos) se beneficiaría de TypeScript por su tipado estático y su ecosistema de bibliotecas de visualización (deck.gl, MapLibre GL). No se recomienda para el núcleo algorítmico. | No aplica. |

**Decisión para el MVP:** Python para todo el prototipado y la capa de aplicación. Si el rendimiento del algoritmo de etiquetado se convierte en un problema, migrar el núcleo a Rust con PyO3.


### 2.5 Simulación y validación

| Tecnología | Rol en EcoRuta | Justificación | Alternativas descartadas |
|---|---|---|---|
| **SUMO (Simulation of Urban MObility)** | Simulación microscópica de tráfico para validar rutas en escenarios controlados | SUMO es el simulador de tráfico microscópico de código abierto más utilizado en investigación. Permite modelar vehículos individuales, flujos de tráfico, intersecciones, semáforos y condiciones de red. Estudios recientes lo utilizan para validar sistemas de enrutamiento sostenible: SRRS (2025) combina YOLO con SUMO para reducir consumo de combustible y emisiones; EvoRoute (2026) valida su marco de enrutamiento con una co-simulación SUMO–OpenAI Gym. Para EcoRuta, SUMO permite probar escenarios extremos (cierres masivos, horas pico severas) sin riesgo ni costo. | No existe una alternativa abierta con el mismo nivel de madurez y comunidad. Simuladores comerciales (VISSIM, Aimsun) son costosos y menos flexibles para investigación. |
| **OpenAI Gym (integración con SUMO)** | Entorno de simulación para experimentación con aprendizaje por refuerzo | Si EcoRuta evoluciona hacia estrategias adaptativas de enrutamiento, la integración SUMO–Gym permite entrenar agentes que ajusten rutas en tiempo real. | No se recomienda para el MVP; es una extensión posterior. |

**Decisión para el MVP:** SUMO para validación de rutas en escenarios controlados. La integración con Gym se reserva para fases avanzadas.


### 2.6 APIs de datos externos

| Fuente | Rol en EcoRuta | Justificación | Alternativas descartadas |
|---|---|---|---|
| **CNE — API de precios de combustible** | Precios de gasolina y diésel por estación | La CNE expone 4 endpoints que devuelven precios actuales de gasolina Regular, Premium y Diésel para estaciones en los 32 estados de México. Cada registro incluye dirección, tipo de producto, subproducto y precio vigente. La Plataforma Nacional de Datos Abiertos también publica un histórico de precios. Es la fuente oficial para el costo de combustible en México. | No existe alternativa oficial para México. Se puede complementar con entrada manual para precios no disponibles. |
| **SESNSP — Datos de incidencia delictiva** | Contexto territorial de seguridad (uso informativo) | El SESNSP publica datos abiertos de incidencia delictiva con desagregación estatal y municipal. Para EcoRuta, estos datos se utilizan como **contexto territorial**, no como puntuaciones de riesgo por calle. La interfaz debe mostrar la resolución espacial y las limitaciones metodológicas. | No aplica; es la fuente oficial. |
| **CONAGUA / CENAPRED — Atlas de inundación** | Capas de peligro histórico por inundación | El Atlas Nacional de Riesgo por Inundación proporciona capas de susceptibilidad que pueden utilizarse como contexto para advertir sobre zonas expuestas. No confirman cierres actuales; deben combinarse con avisos oficiales. | No aplica. |
| **Azure Maps Traffic** | Datos de tráfico en tiempo real para México | Azure Maps Traffic service ofrece cobertura de tráfico en tiempo real e incidentes para México. Es una alternativa a Google y HERE con precios potencialmente más accesibles. | HERE Traffic es otra opción; se debe evaluar cobertura y costo. Google Routes API tiene funcionalidad ecológica, pero su disponibilidad en México debe verificarse. |
| **Open-Meteo** | Datos meteorológicos abiertos | Open-Meteo ofrece pronósticos por coordenadas con API gratuita y sin necesidad de clave. Su cobertura global es adecuada para México. Se complementa con el SMN de CONAGUA para alertas oficiales. | OpenWeatherMap requiere clave y tiene límites en el plan gratuito. |

**Decisión para el MVP:** CNE para precios de combustible (con caché y timestamps), SESNSP para contexto territorial (sin puntuaciones por calle), CONAGUA para capas de peligro histórico, Azure Maps Traffic para tráfico en tiempo real si el presupuesto lo permite, y Open-Meteo para clima.


### 2.7 Visualización y frontend

| Tecnología | Rol en EcoRuta | Justificación | Alternativas descartadas |
|---|---|---|---|
| **deck.gl** | Visualización de rutas y datos geoespaciales a gran escala | deck.gl es un framework de visualización basado en WebGL que permite renderizar millones de puntos y líneas de manera eficiente. Está optimizado para datos geoespaciales y soporta capas de trayectorias, arcos y agregaciones espaciales. | Kepler.gl, construido sobre deck.gl, es una alternativa para exploración de datos, pero para una aplicación de producción con lógica personalizada, deck.gl ofrece mayor control. |
| **MapLibre GL** | Renderizado de mapas base | MapLibre GL es un fork de Mapbox GL JS con licencia BSD. Ofrece renderizado de mapas vectoriales de alto rendimiento y es compatible con estilos personalizados. | Mapbox GL requiere licencia comercial para uso en producción. |
| **React + TypeScript** | Framework de frontend | React con TypeScript proporciona tipado estático, un ecosistema maduro de componentes y facilidad para integrar bibliotecas de mapas y visualización. | Vue y Svelte son alternativas viables, pero React tiene mayor adopción en el ecosistema geoespacial. |

**Decisión para el MVP:** deck.gl + MapLibre GL + React/TypeScript para el frontend.


### 2.8 Infraestructura y despliegue

| Tecnología | Rol en EcoRuta | Justificación | Alternativas descartadas |
|---|---|---|---|
| **Docker + Docker Compose** | Contenerización de servicios | Docker permite empaquetar PostgreSQL/PostGIS, Valhalla, el servicio de optimización y el backend en contenedores reproducibles. Docker Compose facilita la orquestación local para desarrollo y pruebas. | Kubernetes es excesivo para el MVP; se puede adoptar en producción si el sistema escala. |
| **FastAPI (Python)** | API backend para el servicio de optimización | FastAPI ofrece alto rendimiento, validación automática de datos con Pydantic y documentación OpenAPI generada automáticamente. Es ideal para exponer el motor de optimización como servicio. | Flask es más simple pero menos performante y carece de validación automática. Django REST Framework es más pesado y orientado a aplicaciones con base de datos relacional compleja. |
| **Redis** | Caché de consultas y colas de tareas | Redis puede almacenar en caché resultados de rutas frecuentes y gestionar colas para cálculos costosos (por ejemplo, generación de matrices de costos para VRP). | No es indispensable en el MVP, pero mejora la latencia y la experiencia de usuario. |

**Decisión para el MVP:** Docker Compose para desarrollo, FastAPI para el backend, Redis para caché si es necesario.


## 3. Tabla resumen del stack recomendado

| Capa | Tecnología principal | Alternativa | Fase de adopción |
|---|---|---|---|
| Base de datos geoespacial | PostgreSQL + PostGIS | Apache Sedona (fase avanzada) | MVP |
| Enrutamiento en base de datos | pgRouting | — | MVP |
| Motor de enrutamiento | Valhalla | OSRM, GraphHopper | MVP |
| Fuente oficial México | SAKBÉ (INEGI) | — | MVP |
| Algoritmo multiobjetivo | Label-setting propio (Python → Rust) | pymoo (experimentación) | MVP |
| Optimización de paradas | Google OR-Tools | pymoo (investigación) | Fase 2 |
| Lenguaje principal | Python | Rust (rendimiento), TypeScript (frontend) | MVP |
| Simulación | SUMO | — | Fase 3 |
| Precios de combustible | CNE API | Entrada manual | MVP |
| Tráfico | Azure Maps Traffic | HERE, Google Routes | Fase 2 |
| Clima | Open-Meteo | SMN/CONAGUA | MVP |
| Seguridad | SESNSP (contexto) | — | Fase 2 |
| Inundaciones | CONAGUA/CENAPRED | — | Fase 2 |
| Frontend | React + TypeScript | — | MVP |
| Visualización | deck.gl + MapLibre GL | Kepler.gl (exploración) | MVP |
| Backend API | FastAPI | — | MVP |
| Caché | Redis | — | Fase 2 |
| Contenerización | Docker + Docker Compose | — | MVP |


## 4. Justificación de las decisiones críticas

### 4.1 ¿Por qué Valhalla y no OSRM?

OSRM es más rápido para consultas con perfil fijo, pero su arquitectura precomputa los costos en el grafo. EcoRuta necesita que los costos dependan del vehículo, la hora, el precio del combustible y las condiciones de tráfico. Valhalla resuelve esto con **costos dinámicos en tiempo de ejecución**: el modelo de costo se pasa en la consulta y no requiere reconstruir el grafo. Esta flexibilidad es indispensable para el proyecto.

### 4.2 ¿Por qué un algoritmo de etiquetado propio y no una biblioteca existente?

Las bibliotecas de optimización multiobjetivo (pymoo, DEAP) están orientadas a problemas genéricos y no están adaptadas a las particularidades del enrutamiento vial: costos dependientes del tiempo, restricciones de vehículo, y necesidad de generar la frontera de Pareto de manera exacta para grafos de tamaño moderado. El algoritmo de etiquetado label-setting es suficientemente conocido y la literatura reciente proporciona las condiciones de correctitud. Implementarlo permite adaptarlo a las necesidades específicas de EcoRuta.

### 4.3 ¿Por qué Python para el MVP y Rust para producción?

Python ofrece el ecosistema más rico para prototipado e integración. Permite iterar rápidamente sobre el diseño del algoritmo y conectarse fácilmente con PostgreSQL, APIs externas y bibliotecas de optimización. Si el rendimiento del algoritmo de etiquetado se convierte en un cuello de botella, Rust ofrece un speedup de aproximadamente 10x con bindings de Python, manteniendo la facilidad de integración.

### 4.4 ¿Por qué SUMO para validación?

SUMO es el simulador de tráfico microscópico de código abierto más maduro y utilizado en investigación. Permite validar rutas en escenarios controlados antes de pasar a recorridos reales, reduciendo costo y riesgo. Estudios recientes confirman su utilidad para validar sistemas de enrutamiento sostenible.

### 4.5 ¿Por qué PostgreSQL/PostGIS y no una base de datos de grafos?

EcoRuta requiere operaciones relacionales (unir tablas de nodos, aristas, atributos, resultados de optimización) además de operaciones geoespaciales. PostgreSQL/PostGIS cubre ambos requisitos. Las bases de datos de grafos puras (Neo4j, TigerGraph) están optimizadas para traversal de grafos, pero son menos adecuadas para consultas relacionales complejas y análisis geoespaciales. Además, pgRouting ya implementa algoritmos de camino mínimo directamente en PostgreSQL, lo que simplifica la arquitectura.

### 4.6 ¿Por qué CNE para precios y no una API comercial?

La CNE es la fuente oficial de precios de combustible en México. Su API expone precios actuales por estación, estado y municipio. No existe una alternativa oficial y las APIs comerciales no ofrecen datos específicos de México con la misma granularidad. La limitación principal es que el precio reportado puede no ser instantáneo; el sistema debe conservar el timestamp y marcar la antigüedad del dato.


## 5. Riesgos tecnológicos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Complejidad de configuración de Valhalla | Media | Medio | Usar la imagen Docker oficial; documentar el proceso de importación de la RNC |
| Rendimiento insuficiente del algoritmo en Python | Media | Alto | Prototipar en Python, migrar núcleo a Rust si es necesario; usar PyO3 para bindings |
| Cobertura limitada de Azure Maps Traffic en México | Media | Medio | Verificar cobertura antes de adoptar; usar patrones históricos como respaldo |
| Datos de la CNE con latencia o inconsistencias | Alta | Bajo | Conservar timestamps; permitir entrada manual; marcar antigüedad del dato |
| Complejidad de SUMO para escenarios realistas | Media | Medio | Comenzar con redes simplificadas; escalar gradualmente |
| Dependencia de un único proveedor de tráfico | Media | Alto | Abstraer la capa de conectores; poder intercambiar proveedores sin afectar el núcleo |


## 6. Conclusión

El stack tecnológico recomendado para EcoRuta se organiza en capas que reflejan la arquitectura del sistema:

- **Datos:** PostgreSQL + PostGIS + pgRouting para almacenamiento y análisis geoespacial; CNE, SESNSP y CONAGUA para datos oficiales de México; Azure Maps Traffic y Open-Meteo para datos dinámicos.
- **Enrutamiento:** Valhalla como motor principal por su flexibilidad de costos dinámicos; SAKBÉ como fuente de validación para México.
- **Optimización:** Algoritmo de etiquetado label-setting implementado en Python (con migración a Rust si es necesario) para el núcleo multiobjetivo; Google OR-Tools para la capa de VRP; pymoo para experimentación.
- **Validación:** SUMO para simulación microscópica de tráfico.
- **Aplicación:** FastAPI para el backend; React + TypeScript + deck.gl + MapLibre GL para el frontend.
- **Infraestructura:** Docker + Docker Compose para desarrollo; Redis para caché.

Esta selección prioriza la flexibilidad, la integración con fuentes mexicanas y la viabilidad de un proyecto de investigación, manteniendo abierta la posibilidad de escalar a producción con tecnologías de mayor rendimiento cuando el modelo esté validado.


*Documento complementario al análisis teórico profundo de EcoRuta. Las tecnologías recomendadas deben validarse experimentalmente antes de adoptarse definitivamente. Las versiones y licencias de cada herramienta deben verificarse antes de su implementación.*