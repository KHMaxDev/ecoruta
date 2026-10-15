# EcoRuta — Documento de Análisis Profundo, Fundamentación Teórica y Propuesta de Investigación Mejorada

**Tipo de documento:** análisis crítico, ampliación teórica y hoja de ruta de investigación  
**Fecha de análisis:** 14 de octubre de 2026  
**Documento base:** `EcoRuta_Investigacion_Teorica_Algoritmos_Rutas.md`  
**Estado:** marco teórico ampliado con literatura científica actualizada; sin implementación ni validación experimental  
**Ámbito:** México, con posibilidad de extensión regional


## Nota de lectura

Este documento no reemplaza al informe original de EcoRuta. Lo complementa, profundiza y, en varios puntos, lo corrige o matiza. Se han consultado fuentes científicas publicadas entre 2015 y 2025 para actualizar el estado del arte, reforzar la justificación matemática y proponer un diseño experimental más riguroso. Cada afirmación relevante está vinculada a la fuente correspondiente. Cuando el informe original hacía una afirmación que la evidencia actual matiza o contradice, se señala explícitamente.


## 1. Diagnóstico crítico del documento original

### 1.1 Fortalezas identificadas

El documento original presenta una estructura sólida y un enfoque profesional. Destacan los siguientes aciertos:

**Rigor conceptual.** La distinción entre objetivos, restricciones duras y variables contextuales está bien establecida. La insistencia en que los cierres confirmados no deben ser penalizaciones económicas intercambiables por ahorro es correcta desde la perspectiva de factibilidad.

**Transparencia epistemológica.** El documento reconoce repetidamente que no promete una ruta perfecta y que la calidad del resultado depende tanto del algoritmo como de la calidad de los datos. Esta humildad metodológica es infrecuente y valiosa.

**Arquitectura modular.** La separación en capas (datos, estimación de costos, optimización, selección, interfaz) es la decisión correcta para un sistema que debe evolucionar sin reescribirse por completo.

**Reconocimiento de la multidimensionalidad.** La propuesta de trabajar con frentes de Pareto en lugar de un único óptimo escalar es matemáticamente correcta para el problema planteado.

### 1.2 Limitaciones del análisis original

**Falta de profundidad en la fundamentación algorítmica.** El informe menciona algoritmos de etiquetado multiobjetivo pero no analiza su complejidad computacional, las condiciones bajo las cuales son viables, ni las técnicas específicas de poda y dominancia que determinan su rendimiento práctico. La literatura reciente muestra que el crecimiento del número de etiquetas puede hacer inviable el enfoque exacto cuando se superan ciertos umbrales de objetivos y densidad de red.

**Subestimación de la complejidad del enrutamiento dependiente del tiempo.** El documento trata el enrutamiento dependiente del tiempo como una "propiedad del modelo" pero no aborda las dificultades específicas que introduce: la propiedad FIFO (First-In-First-Out) de las funciones de tiempo, la necesidad de discretización, y las implicaciones para la correctitud de los algoritmos de etiquetado.

**Ausencia de revisión de literatura sobre el problema específico.** No se mencionan variantes como el *Green Time-Dependent Vehicle Routing Problem* (GTDVRP), que es exactamente la clase de problema que EcoRuta aborda cuando se incorporan múltiples paradas y costos variables en el tiempo.

**Modelo de consumo excesivamente simplificado.** Aunque el documento reconoce la necesidad de modelos más sofisticados, no presenta alternativas concretas. La literatura reciente ofrece modelos basados en fuerzas físicas que relacionan consumo con velocidad, pendiente, masa y resistencia aerodinámica de manera explícita.

**Falta de consideración de la validación con simulación.** El plan experimental carece de un componente de simulación de tráfico que permita validar las rutas propuestas antes de pruebas de campo. Existen marcos establecidos para esto, como la combinación de SUMO con algoritmos de optimización.

**Vaguedad en el tratamiento de la incertidumbre.** El documento menciona la incertidumbre como un objetivo \(U(P)\) pero no define cómo se calcularía ni cómo interactuaría con la búsqueda multiobjetivo. La literatura reciente ofrece enfoques robustos basados en optimización min-max y conciencia de riesgo.

### 1.3 Correcciones necesarias

| Afirmación del documento original | Corrección o matiz |
|---|---|
| "La suma ponderada no encuentra necesariamente todas las soluciones eficientes" | Correcto, pero el documento no menciona que existe un resultado teórico: para problemas convexos, la suma ponderada con pesos variados sí puede generar toda la frontera de Pareto. La cuestión es que el problema de rutas es discreto y no convexo. |
| "El etiquetado multiobjetivo puede ofrecer resultados exactos" | Cierto bajo supuestos de dominancia correcta y funciones de costo monótonas. En redes dependientes del tiempo no-FIFO, la correctitud requiere condiciones adicionales que el documento no menciona. |
| "A* convencional no produce por sí solo todas las soluciones de Pareto" | Correcto. Sin embargo, existen extensiones multiobjetivo de A* (NAMOA*, MOA*) que sí lo hacen, aunque con costos computacionales significativos. |
| "Los datos del SESNSP no equivalen a una probabilidad precisa por calle" | Correcto y bien señalado. Adicionalmente, debe considerarse que las tasas de denuncia varían sistemáticamente entre regiones, lo que introduce sesgo geográfico. |


## 2. Marco teórico ampliado

### 2.1 El problema de camino mínimo multiobjetivo: fundamentos formales

El problema que EcoRuta aborda en su núcleo es una variante del **Problema de Camino Mínimo Multiobjetivo (MOSP, por sus siglas en inglés)**. Formalmente:

Dado un grafo dirigido \(G=(V,E)\), un origen \(s\) y un destino \(t\), y una función vectorial de costo \(\mathbf{c}: E \to \mathbb{R}^k_{\geq 0}\) donde \(k\) es el número de objetivos, se busca el conjunto de caminos \(P\) de \(s\) a \(t\) que son **Pareto-óptimos**: ningún otro camino factible los domina en todos los objetivos simultáneamente.

La dominancia se define como: un camino \(P_1\) domina a \(P_2\) si \(\mathbf{c}(P_1) \leq \mathbf{c}(P_2)\) componente a componente, con desigualdad estricta en al menos una componente.

El conjunto de todas las soluciones no dominadas constituye la **frontera de Pareto**. Para problemas discretos como el enrutamiento en redes viales, esta frontera puede ser finita pero exponencialmente grande en el peor caso.

**Complejidad computacional.** El MOSP es NP-difícil cuando el número de objetivos \(k \geq 2\). Esto no significa que no pueda resolverse exactamente para instancias prácticas, sino que no existe un algoritmo de tiempo polinomial que garantice encontrar toda la frontera para cualquier grafo. Los algoritmos de etiquetado son pseudopolinomiales: su tiempo de ejecución depende del tamaño de la frontera de Pareto, que puede crecer exponencialmente con \(k\) y con el tamaño del grafo.

**Implicación para EcoRuta.** El diseño debe balancear la exhaustividad de la frontera con la viabilidad computacional. Para grafos de tamaño relevante (miles o millones de nodos), con más de tres o cuatro objetivos, el enfoque exacto puede volverse prohibitivo. Esto justifica la estrategia híbrida que se detalla más adelante.

### 2.2 Algoritmos de etiquetado multiobjetivo: estado del arte 2024–2025

Los algoritmos de etiquetado son la familia dominante para resolver el MOSP de forma exacta. Mantienen, para cada nodo, un conjunto de **etiquetas** —vectores de costo acumulado de caminos parciales— y aplican **podas por dominancia** para descartar etiquetas que no pueden conducir a una solución óptima.

**Clasificación fundamental:**

*Label-setting.* Las etiquetas se procesan en orden de prioridad (típicamente lexicográfico o por una función de mérito) y, una vez extraídas de la cola, se consideran definitivas para ese estado. La implementación más conocida es la **Multiobjective Dijkstra (MLS)** . El artículo de Bazgan, Kager, Thielen y Vanderpooten (2025) presenta un algoritmo general de etiquetado para el problema de camino mínimo multiobjetivo temporal, con análisis de tratabilidad que distingue entre redes FIFO y no-FIFO.

*Label-correcting.* Las etiquetas pueden actualizarse múltiples veces hasta que ninguna mejora sea posible. Kergosien et al. (2022) demostraron que un algoritmo label-correcting bien implementado puede manejar grafos con millones de nodos y aristas, pero ese resultado se obtuvo con dos objetivos y en instancias específicas de prueba【S4】.

**Avances recientes relevantes:**

Silva, Ramos y Barbosa (2025) publicaron el algoritmo **All-pairs Multi-objective Dynamic Shortest Path**, que combina un método de etiquetado correctivo con el algoritmo Optimistic Linear Support. Los resultados reportan ser más de 3.22 veces más rápido que las líneas base en la producción de soluciones de Pareto para problemas dinámicos.

El algoritmo **OPMOS** (Ordered Parallel Multi-Objective Shortest-Paths), presentado en la Conferencia Internacional de Supercomputación de 2025, propone una ejecución paralela y asíncrona para el MOSP, con verificaciones de dominancia que crecen con el número de objetivos. Los autores señalan que el tiempo de ejecución puede escalar de 3 milisegundos con 2 objetivos a más de 38 minutos con 12 objetivos en una misma instancia.

**Lección para EcoRuta.** El número de objetivos debe mantenerse bajo. Dos o tres objetivos son tratables en la mayoría de escenarios; cuatro ya introduce complejidad significativa; cinco o más requiere estrategias de reducción dimensional o enfoques aproximados.

### 2.3 Enrutamiento dependiente del tiempo: el problema de la no-FIFO

El enrutamiento dependiente del tiempo introduce una complicación que el documento original no aborda con suficiente profundidad: la **propiedad FIFO** (First-In-First-Out) de las funciones de tiempo de viaje.

Una función de tiempo \(\tau_e(t)\) es FIFO si para cualquier par de instantes de salida \(t_1 < t_2\), se cumple que \(t_1 + \tau_e(t_1) \leq t_2 + \tau_e(t_2)\). Es decir, salir antes nunca implica llegar después. Las redes viales reales suelen satisfacer esta propiedad, pero no siempre: los cambios de semáforo, los accidentes que se disipan, o las restricciones de acceso pueden violarla.

**Implicación algorítmica.** En redes no-FIFO, la correctitud de los algoritmos de etiquetado requiere condiciones adicionales. El artículo de Bazgan et al. (2025) analiza precisamente esta cuestión y distingue entre redes con tiempo discreto y continuo, señalando que la tratabilidad depende de si se permite esperar en los nodos.

**Lección para EcoRuta.** La implementación debe verificar empíricamente si las funciones de tiempo de viaje derivadas de los datos del proveedor satisfacen FIFO. Si no lo hacen, el algoritmo debe adaptarse o documentar la aproximación.

### 2.4 Modelos de consumo de combustible: más allá de km/l

El documento original reconoce que km/l es insuficiente pero no ofrece alternativas concretas. La literatura reciente proporciona modelos más rigurosos.

**Modelo basado en fuerzas.** El consumo instantáneo de combustible puede modelarse como una función de la potencia requerida para vencer la resistencia aerodinámica, la resistencia a la rodadura, la resistencia gravitacional (pendiente) y la inercia. La ecuación fundamental es:

\[
M_L = \frac{K A S^2}{21.15 \, Q_L \eta_1 \eta_2} V^2 + \frac{0.001 T_2 W V S}{Q_L \eta_1 \eta_2} V + \frac{0.001 T_1 W S + W V S \sin\alpha}{Q_L \eta_1 \eta_2}
\]

donde \(K\) es el coeficiente aerodinámico, \(A\) el área frontal, \(S\) la densidad del aire, \(V\) la velocidad, \(W\) el peso, \(T_1\) y \(T_2\) coeficientes de resistencia a la rodadura, y \(\alpha\) el ángulo de pendiente.

La conclusión clave de este modelo es que el consumo por 100 km es una **función cuadrática de la velocidad** para un vehículo, carretera y condiciones dadas. Esto significa que existe una velocidad óptima de consumo mínimo (típicamente entre 60 y 80 km/h para vehículos ligeros) y que tanto velocidades muy bajas como muy altas incrementan el consumo.

**Efecto de la pendiente.** Estudios de 2024 confirman que la pendiente es el factor más crítico en la variación del consumo. Un aumento de pendiente del 2% al 7% produce un incremento de consumo de aproximadamente 2.5 veces. Para un vehículo que sube y baja la misma pendiente, el consumo neto se aproxima al de un tramo plano, pero el consumo instantáneo en subida es significativamente mayor.

**Modelos con aprendizaje automático.** La literatura de 2025 está migrando hacia modelos de consumo basados en aprendizaje profundo. Un estudio reciente propone un modelo de consumo para vehículos eléctricos con un margen de error del 2.66% para el estado de carga (SoC) y 0.6 kWh para el consumo energético. Para vehículos de combustión, hay propuestas que combinan transformadores y optimización por políticas proximales (PPO) para la predicción de consumo y la planificación adaptativa de puntos de ruta.

**Lección para EcoRuta.** El modelo de consumo debe ser, como mínimo, una función de velocidad, pendiente y masa. Un enfoque escalonado —comenzar con una curva empírica por rangos de velocidad, luego incorporar pendiente, y finalmente calibración con datos reales— es el camino más realista.

### 2.5 El problema de rutas verde dependiente del tiempo (GTDVRP)

Cuando EcoRuta incorpora múltiples paradas cuyo orden puede variar, el problema se convierte en una instancia del **Green Time-Dependent Vehicle Routing Problem (GTDVRP)** . La revisión de 2024 sobre enfoques de solución para el Green VRP y sus variantes identifica que el 13.76% de los 458 artículos revisados abordan la variante dependiente del tiempo.

Un hallazgo cuantitativo relevante: la formulación dependiente del tiempo conduce a una disminución promedio del 11.71% en comparación con el enfoque independiente del tiempo en términos de emisiones. Esto cuantifica el beneficio de considerar la variación temporal.

**Técnicas de solución.** La literatura reciente combina NSGA-II con aprendizaje automático para mejorar la calidad y velocidad de las soluciones en el MOTDGVRP (Multi-Objective Time-Dependent Green VRP). El estudio de 2025 reporta que la integración de ML acelera el rendimiento computacional y mejora la calidad de las soluciones.

**Lección para EcoRuta.** Si el sistema va a manejar múltiples paradas con orden flexible, el GTDVRP es el marco teórico correcto, y NSGA-II mejorado con ML es una opción viable para instancias grandes.

### 2.6 Incertidumbre y robustez

El tratamiento de la incertidumbre en enrutamiento ha evolucionado hacia enfoques de **optimización robusta** y **conciencia de riesgo**. Un estudio de 2026 sobre enrutamiento marítimo propone un marco que integra optimización min-max de Pareto con un algoritmo consciente de la incertidumbre, logrando reducciones del 5% en consumo y 2% en duración.

La idea central es que, en lugar de optimizar para el valor esperado, se optimiza para el peor caso o para un percentil de riesgo (por ejemplo, el P90 de duración). Esto produce rutas menos sensibles a fluctuaciones imprevistas.

**Lección para EcoRuta.** La incertidumbre no debe tratarse como un objetivo independiente más, sino como una dimensión que modifica la evaluación de los objetivos principales. Una ruta puede ser evaluada por su costo esperado y por su costo en el peor caso (o P90), generando así un frente de Pareto robusto.

### 2.7 Validación mediante simulación

El documento original propone validación con recorridos reales, lo cual es correcto pero costoso y tardado. La literatura ofrece un paso intermedio: **simulación microscópica de tráfico**.

El marco propuesto por EvoRoute combina SUMO con un entorno de aprendizaje por refuerzo (OpenAI Gym) para validar estrategias de enrutamiento en condiciones de congestión realistas. Otro enfoque, menos sofisticado pero más accesible, consiste en generar escenarios sintéticos con patrones de tráfico conocidos y verificar que el algoritmo produce rutas consistentes con las expectativas.

**Lección para EcoRuta.** El plan experimental debe incluir una fase de validación en simulación antes de la validación con recorridos reales. Esto permite probar escenarios extremos (cierres masivos, inundaciones, horas pico severas) sin riesgo ni costo.


## 3. Análisis ampliado de las fuentes de datos

### 3.1 Red Nacional de Caminos (INEGI) y API SAKBÉ

El documento original menciona la RNC pero no la API SAKBÉ. La API de Ruteo del INEGI, versión 3.1, utiliza la Red Nacional de Caminos y está diseñada para sistemas inteligentes de transporte. La RNC se actualiza anualmente y se publica el 15 de diciembre; la base de datos de la API se actualiza con la versión más reciente en un plazo no mayor a una semana.

La API SAKBÉ expone endpoints para cálculo de rutas entre dos puntos, con parámetros como el tipo de sistema de referencia (GRS80 o MERC) y un token de usuario. La RNC incluye información de peajes por tipo de vehículo y número de ejes, así como la ubicación de gasolineras (7,476 registros) y casetas de cobro.

**Implicación para EcoRuta.** SAKBÉ es una fuente oficial mexicana que no requiere dependencia de proveedores comerciales para el cálculo de rutas base. Sin embargo, no ofrece estimaciones de tráfico en tiempo real ni modelos de consumo, por lo que debe combinarse con otras fuentes para los costos.

### 3.2 Precios de combustible (CNE)

La CNE ofrece datos de precios de gasolinas y diésel reportados por permisionarios. Existen endpoints de API que exponen precios de gasolina Regular, Premium y Diésel para estaciones en los 32 estados de México. La Plataforma Nacional de Datos Abiertos también publica un histórico de precios de gasolinas y diésel.

Los precios varían significativamente por región. A finales de 2025, Quintana Roo registraba el precio más alto de gasolina regular (24.81 MXN/L) y Tamaulipas el más bajo. El precio promedio nacional de gasolina regular se situaba en 23.38 MXN/L.

**Implicación para EcoRuta.** La integración con la API de la CNE es viable y debe realizarse con manejo de timestamps y caducidad de datos. La variación regional de precios justifica la inclusión del precio como variable espacial en el modelo.

### 3.3 Motores de enrutamiento: OSRM vs. Valhalla

Una decisión técnica crítica que el documento original no resuelve es la elección del motor de enrutamiento subyacente.

**OSRM** es extremadamente rápido para consultas con un perfil fijo, pero su arquitectura precomputa los costos en el grafo, lo que hace inflexible la modificación de costos en tiempo de consulta. Es adecuado si EcoRuta utiliza un perfil de vehículo único y costos estáticos.

**Valhalla** utiliza **costos dinámicos en tiempo de ejecución**: en lugar de precomputar los pesos, mantiene una rica atribución en el grafo y calcula los costos según un modelo de costo pasado en la consulta. Esto permite cambiar el modelo de costo sin reprocesar el grafo, lo cual es esencial para EcoRuta, donde los costos dependen del vehículo, la hora, el precio del combustible y las condiciones de tráfico.

**Recomendación.** Valhalla es el motor más adecuado para EcoRuta debido a su flexibilidad de costos dinámicos. OSRM puede considerarse como alternativa si el rendimiento es crítico y los costos pueden precomputarse por un número limitado de perfiles.

### 3.4 Tráfico y clima: fuentes y limitaciones

El documento original menciona proveedores comerciales (Google, HERE) y fuentes oficiales (SMN). Es necesario precisar las limitaciones de cada uno.

**Tráfico.** Google Routes API permite obtener información de tráfico por segmentos de polilínea, pero la disponibilidad y granularidad varían por región. HERE ofrece tráfico en vivo e histórico, con la capacidad de incorporar restricciones temporales en el enrutamiento【D9–D11】. Para un proyecto centrado en México, es crucial verificar la cobertura de estos proveedores fuera de las principales zonas metropolitanas.

**Clima.** El SMN de CONAGUA proporciona pronósticos oficiales, pero su resolución espacial y temporal puede ser insuficiente para modelar microclimas urbanos. La integración con APIs meteorológicas de terceros (OpenWeatherMap, Open-Meteo) es una alternativa, pero debe verificarse la cobertura y licencia.

**Datos de inundación.** El Atlas Nacional de Riesgo por Inundación de CONAGUA es una capa de peligro histórico, no un sistema de alerta en tiempo real. La distinción entre susceptibilidad histórica y cierre confirmado, que el documento original establece correctamente, debe reflejarse en la arquitectura de datos: las capas de peligro son contextuales, mientras que los avisos de cierre son operativos.

### 3.5 Seguridad: limitaciones fundamentales de los datos del SESNSP

El documento original advierte correctamente que los datos del SESNSP no equivalen a una probabilidad precisa por calle. Es necesario ir más allá: las tasas de incidencia delictiva están sujetas a **sesgos de denuncia** que varían sistemáticamente por región, nivel socioeconómico y tipo de delito. Un municipio con alta tasa de denuncia puede parecer más peligroso que otro con baja tasa, aunque la incidencia real sea similar.

Además, la desagregación municipal puede ocultar una enorme heterogeneidad intraurbana. Utilizar estos datos para asignar un "riesgo" a un segmento de calle específico es metodológicamente insostenible sin un modelo de desagregación espacial validado.

**Recomendación.** La seguridad debe modelarse como una **restricción blanda informativa** en el MVP: el sistema muestra información contextual sobre la zona (por ejemplo, "este municipio registra una tasa de incidencia superior al promedio estatal"), pero no excluye rutas automáticamente ni asigna puntuaciones numéricas de riesgo. Las restricciones duras por seguridad solo deben aplicarse cuando existan datos georreferenciados de alta calidad y una metodología documentada.


## 4. Arquitectura algorítmica mejorada

### 4.1 Principio de diseño: separación de capas de optimización

El error más común en sistemas de enrutamiento multiobjetivo es intentar resolver todos los componentes simultáneamente. EcoRuta debe adoptar una **arquitectura de optimización en capas**:

**Capa 1: Grafo y costos por arista.** La red vial se representa como un grafo dirigido con atributos estáticos (longitud, tipo de vía, pendiente) y dinámicos (velocidad estimada por hora, precio de combustible por zona, cierres).

**Capa 2: Motor de camino mínimo multiobjetivo.** Para origen-destino sin paradas, un algoritmo de etiquetado label-setting genera la frontera de Pareto costo-tiempo. Esta capa opera sobre el grafo completo o sobre un subgrafo extraído alrededor de la ruta más rápida y la más barata (técnica de *bounding box*).

**Capa 3: Optimizador de secuencia de visitas.** Cuando hay múltiples paradas con orden flexible, se resuelve un TSP/VRP sobre una matriz de costos entre puntos de interés. Esta matriz se calcula invocando la Capa 2 para cada par origen-destino relevante.

**Capa 4: Selector de preferencias.** La frontera de Pareto se filtra y ordena según restricciones del usuario (presupuesto máximo, hora límite) y preferencias (disposición a pagar por tiempo).

Esta separación permite que cada capa se implemente, pruebe y optimice independientemente.

### 4.2 Algoritmo núcleo: label-setting con poda agresiva

Para la Capa 2, se recomienda implementar un algoritmo **label-setting** con las siguientes características:

**Representación de etiquetas.** Cada etiqueta contiene: costo monetario acumulado, tiempo acumulado, nodo actual, y hora de llegada al nodo. Opcionalmente, puede incluir un indicador de riesgo territorial y una medida de incertidumbre.

**Orden de procesamiento.** Las etiquetas se extraen de una cola de prioridad ordenada lexicográficamente por el primer objetivo (costo), con desempate por el segundo (tiempo). Esto garantiza que se procesen primero las etiquetas más prometedoras.

**Verificación de dominancia.** Para cada nodo, se mantiene un conjunto de etiquetas no dominadas. Una nueva etiqueta \(l'\) se descarta si existe una etiqueta \(l\) en el nodo tal que \(l\) domina a \(l'\). Si \(l'\) no es dominada, se eliminan todas las etiquetas del nodo que \(l'\) domina, y se inserta \(l'\).

**Poda por cota inferior.** Se calcula una cota inferior optimista del costo restante desde cada nodo hasta el destino (por ejemplo, distancia euclidiana × costo mínimo por kilómetro). Si el costo acumulado más la cota inferior excede el costo de la peor solución en la frontera actual del destino, la etiqueta se descarta.

**Manejo del tiempo dependiente.** Si las funciones de tiempo de viaje son dependientes de la hora, la hora de llegada se recalcula en cada expansión. Si la red es FIFO, la correctitud se mantiene. Si no lo es, se debe documentar la aproximación o implementar espera en nodos.

### 4.3 Estrategias para controlar la explosión de etiquetas

La literatura reciente identifica la explosión del espacio de estados como el principal cuello de botella del MOSP. Las siguientes estrategias son esenciales:

**Reducción de dimensionalidad.** En lugar de mantener todos los objetivos simultáneamente, se puede resolver el problema para pares de objetivos (costo-tiempo, luego costo-riesgo) y combinar las fronteras resultantes. Esto es aproximado pero drásticamente más rápido.

**Bounding box.** Se calcula la ruta más rápida (Dijkstra sobre tiempo) y la más barata (Dijkstra sobre costo). Se construye un subgrafo con los nodos que están dentro de un radio razonable alrededor de ambas rutas. El algoritmo multiobjetivo opera solo sobre este subgrafo.

**Poda por no-dominancia aproximada.** Si el número de etiquetas por nodo excede un umbral, se pueden agrupar etiquetas cercanas y mantener solo representantes. Esto introduce aproximación pero controla el crecimiento.

**Paralelización.** El algoritmo OPMOS demuestra que la ejecución paralela puede acelerar significativamente el MOSP, aunque con la complejidad adicional de la sincronización y la gestión de duplicados.

### 4.4 Selección de preferencias: más allá de la suma ponderada

La suma ponderada \(J(P) = C(P) + \lambda T(P)\) es simple pero tiene limitaciones conocidas en problemas discretos. Se recomienda complementarla con:

**Método de restricciones ε.** El usuario especifica un presupuesto máximo de tiempo (o de costo) y se minimiza el otro objetivo. Esto genera una frontera de Pareto de manera más controlada que la suma ponderada.

**Punto de codo (knee point).** En muchas fronteras de Pareto, existe un punto donde la compensación entre objetivos cambia abruptamente. Este punto suele ser una recomendación natural porque ofrece el mejor equilibrio marginal. Se puede identificar calculando la máxima distancia a la línea que conecta los extremos de la frontera.

**Perfiles de preferencia.** En lugar de un único \(\lambda\), el sistema puede ofrecer perfiles predefinidos: "económico" (prioriza costo), "rápido" (prioriza tiempo), "equilibrado" (punto de codo), "robusto" (minimiza P90 de tiempo). El usuario selecciona un perfil y el sistema recomienda la solución correspondiente.

### 4.5 Integración con optimizadores de secuencia (TSP/VRP)

Para la Capa 3, se recomienda usar **Google OR-Tools** como base para el optimizador de secuencia, ya que implementa modelos de VRP con ventanas de tiempo, capacidades y múltiples vehículos【D8a】. La integración con la Capa 2 se realiza mediante una **matriz de costos** que OR-Tools utiliza como entrada.

Si el número de paradas es pequeño (< 10), se puede considerar una búsqueda exhaustiva o programación dinámica. Para instancias mayores, OR-Tools con búsqueda tabú o ALNS es apropiado.

**Advertencia sobre la dependencia temporal.** Si los costos entre puntos dependen de la hora de llegada (debido al tráfico), la matriz de costos deja de ser estática y depende de la secuencia. En ese caso, no se puede precomputar una única matriz; se necesita una formulación que evalúe los costos incrementalmente según la secuencia y la hora. Esto complica significativamente el problema y debe abordarse solo cuando el MVP esté validado.


## 5. Plan experimental mejorado

### 5.1 Fases de validación

**Fase 1: Validación matemática en grafos pequeños (semanas 1–4).**  
Construir grafos de 5 a 20 nodos donde se pueda enumerar exhaustivamente todos los caminos factibles. Verificar que el algoritmo de etiquetado devuelve exactamente la frontera de Pareto correcta. Probar casos con múltiples objetivos, restricciones de capacidad y tiempos dependientes.

**Fase 2: Pruebas de estrés en grafos sintéticos (semanas 5–8).**  
Generar grafos aleatorios con densidad y tamaño crecientes. Medir: número de etiquetas exploradas, tiempo de ejecución, memoria utilizada, y tamaño de la frontera de Pareto resultante. Identificar los umbrales donde el algoritmo deja de ser viable.

**Fase 3: Validación en red real con datos históricos (semanas 9–16).**  
Seleccionar una región piloto en México (por ejemplo, Área Metropolitana de Guadalajara o Monterrey). Obtener la red vial de INEGI RNC o OSM. Calcular rutas entre pares origen-destino. Comparar las rutas del frente de Pareto con las rutas de referencia (más rápida, más corta, más barata).

**Fase 4: Validación temporal con patrones de tráfico (semanas 17–22).**  
Incorporar patrones de tráfico histórico por hora. Comparar la recomendación del sistema a las 7:00 vs. a las 14:00 para el mismo par origen-destino. Verificar que las rutas cambian de manera razonable según el patrón de congestión.

**Fase 5: Validación con simulación microscópica (semanas 23–28).**  
Implementar un escenario simplificado en SUMO para la región piloto. Simular los vehículos siguiendo las rutas recomendadas por EcoRuta. Medir consumo y tiempo reales en simulación. Comparar con las estimaciones del modelo. Esta fase permite probar escenarios extremos sin costo ni riesgo.

**Fase 6: Validación con recorridos reales (semanas 29–36).**  
Realizar recorridos controlados en la región piloto, con medición de consumo de combustible (OBD-II o similar) y tiempo real. Comparar con las predicciones. Calibrar los parámetros del modelo de consumo.

### 5.2 Métricas de evaluación

| Dimensión | Métrica | Método de cálculo |
|---|---|---|
| Calidad económica | Ahorro porcentual vs. ruta más rápida | (Costo_rápida − Costo_eco) / Costo_rápida × 100 |
| Precisión temporal | MAE del tiempo de viaje | Promedio de \|T_estimado − T_real\| |
| Precisión de consumo | Error porcentual de litros | \|L_estimado − L_real\| / L_real × 100 |
| Factibilidad | Tasa de violación de restricciones | Número de rutas que violan restricciones duras / total |
| Calidad multiobjetivo | Hipervolumen de la frontera | Área dominada por la frontera de Pareto (requiere referencia) |
| Rendimiento | Latencia de respuesta | Tiempo de cálculo en milisegundos para consultas típicas |
| Escalabilidad | Número de etiquetas por nodo | Promedio y máximo de etiquetas no dominadas |
| Robustez | Variación de recomendación ante perturbaciones | Cambio en la ruta recomendada ante ±10% en precio de combustible |

### 5.3 Diseño de escenarios

Se propone un diseño factorial 2^k con los siguientes factores:

| Factor | Niveles |
|---|---|
| Distancia | Urbano corto (< 15 km) / Interurbano (50–150 km) |
| Hora de salida | Hora valle (10:00) / Hora pico (18:00) |
| Tipo de vehículo | Sedán compacto (rendimiento alto) / SUV (rendimiento bajo) |
| Disponibilidad de tráfico | Datos en vivo / Solo histórico / Sin datos |
| Peajes | Con peajes relevantes / Sin peajes |
| Paradas | Origen-destino simple / Múltiples paradas con orden fijo |

Esto genera 64 escenarios base, que pueden ampliarse con casos extremos (cierre de vía, precio de combustible atípico, clima adverso).


## 6. Riesgos técnicos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Explosión de etiquetas en redes grandes | Alta | Alto | Bounding box, reducción dimensional, umbral de etiquetas con aproximación controlada |
| Datos de tráfico insuficientes fuera de zonas urbanas | Alta | Medio | Usar velocidades por defecto basadas en tipo de vía y límite de velocidad; documentar incertidumbre |
| Modelo de consumo inexacto | Media | Alto | Calibración escalonada; comenzar con curva empírica; validar con OBD-II en fase piloto |
| Costos de API comercial prohibitivos | Media | Medio | Priorizar fuentes abiertas (OSM, SAKBÉ, CNE); usar APIs comerciales solo para validación |
| Dependencia de un único proveedor | Media | Alto | Abstraer la capa de conectores; poder intercambiar proveedores sin afectar el núcleo |
| Interpretación errónea de datos de seguridad | Media | Alto | Etiquetar explícitamente la resolución y confianza; no usar como restricción dura sin validación |
| Cambio de precios de combustible durante el viaje | Baja | Bajo | Usar precio reportado con timestamp; documentar antigüedad del dato |
| Red no-FIFO en funciones de tiempo | Baja | Medio | Verificar empíricamente; implementar espera en nodos si es necesario |


## 7. Conclusiones del análisis

El documento original de EcoRuta establece una base conceptual sólida pero requiere profundización en varios frentes para convertirse en un proyecto de investigación robusto y publicable. Las principales mejoras identificadas son:

1. **Fundamentación algorítmica rigurosa.** La elección de algoritmos de etiquetado debe justificarse con análisis de complejidad, condiciones de correctitud y estrategias de control de explosión de etiquetas. La literatura de 2024–2025 ofrece resultados cuantitativos que permiten dimensionar el esfuerzo computacional esperado.

2. **Modelo de consumo basado en física.** El km/l constante es insuficiente. Un modelo basado en fuerzas (resistencia aerodinámica, rodadura, pendiente) proporciona una base más defendible y permite calibrarse con datos reales.

3. **Integración explícita de la dependencia temporal.** El enrutamiento dependiente del tiempo no es una propiedad trivial; requiere verificar FIFO, discretizar adecuadamente y adaptar los algoritmos de búsqueda.

4. **Tratamiento diferenciado de la incertidumbre.** No debe ser un objetivo más, sino una dimensión que modifica la evaluación de costo y tiempo. Los enfoques robustos (min-max, P90) son más adecuados que la simple suma ponderada.

5. **Validación escalonada con simulación.** Antes de recorridos reales, la simulación microscópica de tráfico permite validar las rutas en escenarios extremos de manera segura y económica.

6. **Selección de motor de enrutamiento informada.** Valhalla ofrece la flexibilidad de costos dinámicos necesaria para EcoRuta; OSRM es una alternativa si el rendimiento es prioritario y los perfiles son limitados.

7. **Manejo ético de datos de seguridad.** La información del SESNSP no debe convertirse en puntuaciones de riesgo por calle. Debe presentarse como contexto territorial con limitaciones explícitas.

La afirmación de valor de EcoRuta —comparar rutas factibles mediante un modelo de costo personalizable, explicar el compromiso entre tiempo y dinero, y mostrar la incertidumbre y procedencia de los datos— sigue siendo válida y está mejor fundamentada después de este análisis.


## Anexo: Referencias bibliográficas ampliadas

**Algoritmos multiobjetivo y caminos mínimos**

- Bazgan, C., Kager, J., Thielen, C., & Vanderpooten, D. (2025). A general label setting algorithm and tractability analysis for the multiobjective temporal shortest path problem. *Networks*, 85(1), 76–90. https://doi.org/10.1002/net.22253
- Silva, J. M. da, Ramos, G. de O., & Barbosa, J. L. V. (2025). An efficient all-pairs approach for multi-objective dynamic shortest path problems. *Neural Computing and Applications*. https://doi.org/10.1007/s00521-025-11437-6
- OPMOS: Ordered Parallel Algorithm for Multi-Objective Shortest-Paths. (2025). *Proceedings of the 39th ACM International Conference on Supercomputing*. https://doi.org/10.1145/3721145.3725781
- Kergosien, Y., Giret, A., Néron, E., & Sauvanet, G. (2022). An Efficient Label-Correcting Algorithm for the Multiobjective Shortest Path Problem. *INFORMS Journal on Computing*, 34(1), 76–92. https://doi.org/10.1287/ijoc.2021.1081

**Eco-routing y modelos de consumo**

- Fahmin, A., et al. (2024). Eco-Friendly Route Planning Algorithms: Taxonomies, Literature Review and Future Directions. *ACM Computing Surveys*, 57(1), Article 21. https://doi.org/10.1145/3691624
- Zhou, M., Jin, H., & Wang, W. (2016). A review of vehicle fuel consumption models to evaluate eco-driving and eco-routing. *Transportation Research Part D*, 49, 203–218. https://doi.org/10.1016/j.trd.2016.09.008
- Correlation between carbon emissions, fuel consumption of vehicles and speed limit on expressway. (2024). *ScienceDirect*. https://doi.org/10.1016/j.trd.2024.104203
- Zhao, B., Soga, K., & Iwama, M. (2024). Spatial system perspective of understanding “fuel-sensitive routes” using regional-scale case studies. *Transportation Research Part D*, 131, 104203.

**GTDVRP y enrutamiento verde**

- Machine learning multi-objective optimization for time-dependent green vehicle routing problem. (2025). *Energy Economics*, 148, 108628. https://doi.org/10.1016/j.eneco.2025.108628
- A recent review of solution approaches for green vehicle routing problem and its variants. (2024). *ScienceDirect*. https://doi.org/10.1016/j.susoc.2024.01.001
- Gülmez, B., Emmerich, M., & Fan, Y. (2024). Multi-objective Optimization for Green Delivery Routing Problems with Flexible Time Windows. *Applied Artificial Intelligence*. https://doi.org/10.1080/08839514.2024.2325302

**Incertidumbre y robustez**

- Ensemble-forecast-based uncertainty-robust framework for ship energy-efficient weather routing. (2026). *Computers & Industrial Engineering*. https://doi.org/10.1016/j.cie.2026.108721
- Ensemble-based ship weather multi-objective route optimization. (2026). *ScienceDirect*. 

**Vehículos eléctricos**

- Data-driven, personalized route planning for connected electric vehicles. (2025). *ScienceDirect*. https://doi.org/10.1016/j.apenergy.2025.125432
- A fine-grained predictive optimization framework for dynamic eco-routing of electric vehicles. (2025). *ScienceDirect*. 

**Validación y simulación**

- EvoRoute: An Evolutionary Multi-Agent Framework for Sustainable and Congestion-Aware Routing. (2026). *IEEE*. 
- Designing a simulation framework to develop and evaluate an eco-routing strategy. *NSTL*. 

**Fuentes de datos mexicanas**

- INEGI. Red Nacional de Caminos y API SAKBÉ v3.1. https://www.inegi.org.mx/programas/rnc/
- CNE. Precios de expendio de gasolinas y diésel. https://www.cne.gob.mx/consultaprecios/gasolinasydiesel/gasolinasydiesel.html
- SESNSP. Datos abiertos de incidencia delictiva. https://www.gob.mx/sesnsp/acciones-y-programas/datos-abiertos-de-incidencia-delictiva
- CONAGUA. Atlas Nacional de Riesgo por Inundación. https://www.gob.mx/conagua/acciones-y-programas/atlas-nacional-de-riesgo-por-inundacion-204625

**Motores de enrutamiento**

- Valhalla. Dynamic costing. https://valhalla.github.io/valhalla/
- OSRM. HTTP API Documentation. https://project-osrm.org/docs/v5.24.0/api/
- Google OR-Tools. Vehicle Routing Problem with Time Windows. https://developers.google.com/optimization/routing/vrptw


*Este documento de análisis ha sido elaborado como complemento al informe original de EcoRuta. No constituye una implementación ni una validación experimental. Su propósito es fortalecer la base teórica y metodológica del proyecto antes de pasar a la fase de desarrollo.*