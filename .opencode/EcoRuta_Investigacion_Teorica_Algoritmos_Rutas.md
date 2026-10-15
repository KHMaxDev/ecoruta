# EcoRuta
## Investigación teórica y estado del arte para un sistema de optimización multiobjetivo de rutas de bajo costo

**Tipo de documento:** informe de investigación y propuesta técnica preliminar  
**Fecha de consulta de fuentes:** 14 de octubre de 2026  
**Ámbito inicial sugerido:** México, con posibilidad de ampliación a otras regiones  
**Estado:** marco teórico; todavía no constituye una implementación ni una validación experimental

---

## Resumen ejecutivo

EcoRuta se plantea como un sistema de planificación de rutas que busca minimizar el costo económico de un desplazamiento sin ignorar el tiempo, la seguridad, la confiabilidad del trayecto ni las condiciones reales de circulación. En lugar de considerar únicamente la distancia o el tiempo previsto, el sistema modelaría la red vial como un grafo y evaluaría sus segmentos según el vehículo, el horario, el tráfico, el combustible, los peajes, el clima, los cierres viales y otras variables relevantes.

El problema es de **optimización multiobjetivo**. Una ruta puede ser más barata y tardar más; otra puede llegar antes, pero consumir más combustible o incluir peajes. No siempre existe una única alternativa que sea mejor en todas las dimensiones. Por eso se propone calcular un conjunto de rutas no dominadas —una frontera de Pareto— y después seleccionar o presentar alternativas de acuerdo con las preferencias del usuario y con restricciones de seguridad y factibilidad.

La revisión identifica varias familias de algoritmos con funciones distintas:

- Dijkstra y A* como líneas base para problemas de camino mínimo con un objetivo.
- Algoritmos de etiquetado multiobjetivo (*label-setting* y *label-correcting*) para calcular rutas no dominadas.
- Suma ponderada y método de restricciones ε para convertir las preferencias del usuario en una decisión interpretable.
- Algoritmos evolutivos, como NSGA-II, y búsqueda local para explorar problemas combinatorios grandes.
- Métodos para TSP/VRP cuando hay múltiples paradas cuyo orden debe optimizarse.

La recomendación no es construir un algoritmo monolítico que intente resolver todos los componentes simultáneamente. Se propone una arquitectura híbrida: datos cartográficos y de contexto, modelo de consumo y tiempo por segmento, optimizador multiobjetivo, optimizador de paradas cuando proceda, y una capa de selección que explica la ruta recomendada.

El documento también identifica fuentes de datos públicas y comerciales, entre ellas la Red Nacional de Caminos de INEGI, datos de precios de combustibles de la Comisión Nacional de Energía (CNE), información de incidencia delictiva del SESNSP y atlas de inundación de CONAGUA/CENAPRED. Estas fuentes tienen distintas escalas, coberturas, frecuencias de actualización y limitaciones. En consecuencia, la precisión del sistema dependerá no solo del algoritmo, sino también de la calidad y actualidad de los datos usados.

**Conclusión principal:** para un primer prototipo científico se recomienda definir un modelo de grafo dirigido con costos dependientes de la hora y del vehículo, estudiar el problema de camino mínimo multiobjetivo con algoritmos de etiquetado y comparar las soluciones con Dijkstra/A*, el menor costo monetario y una ruta más rápida. Las variables avanzadas —inundaciones, seguridad territorial, incertidumbre, abastecimiento y orden flexible de paradas— deben incorporarse por etapas y evaluarse empíricamente.

---

## Índice

1. Introducción y planteamiento del problema  
2. Objetivos, alcance e hipótesis  
3. Estado del arte  
4. Modelo del problema mediante grafos  
5. Variables de EcoRuta  
6. Formulación matemática  
7. Comparación de algoritmos  
8. Tratamiento de múltiples paradas  
9. Fuentes de datos y proveedores  
10. Arquitectura conceptual  
11. Propuesta de experimentación y evaluación  
12. Riesgos, limitaciones y consideraciones éticas  
13. Plan de trabajo recomendado  
14. Conclusiones y decisión técnica  
15. Anexo A: tabla de variables y datos requeridos  
16. Anexo B: fuentes oficiales y documentación técnica  
17. Anexo C: bibliografía científica inicial

---

# 1. Introducción y planteamiento del problema

## 1.1 Contexto

Los sistemas de navegación convencionales ayudan a encontrar caminos entre puntos geográficos y suelen priorizar el tiempo de viaje, la distancia o criterios de eficiencia que dependen del proveedor. Algunos ya ofrecen funciones ecológicas que estiman rutas de menor consumo de combustible o energía. Por tanto, EcoRuta no debe presentarse como la primera solución que considera el ahorro de combustible.

La oportunidad de investigación es construir un sistema que **estime el costo monetario total del viaje de manera personalizable y transparente**, incorporando más explícitamente el perfil del vehículo, los precios locales de combustible, los peajes, las restricciones de seguridad, la incertidumbre y las preferencias de tiempo del conductor. También debe distinguir entre datos actuales, datos históricos y estimaciones.

Por ejemplo, una ruta más corta no necesariamente es la más barata: puede tener tráfico intenso, muchas detenciones, mayor pendiente o un peaje. Una ruta más rápida tampoco tiene que minimizar el gasto. El sistema debe comparar las alternativas bajo un mismo modelo y mostrar las compensaciones entre ellas.

## 1.2 Pregunta de investigación

**¿Cómo diseñar un algoritmo de optimización multiobjetivo basado en grafos que recomiende rutas de bajo costo monetario, equilibrando gasto y tiempo y considerando las condiciones del tráfico, el clima, los peligros viales, la seguridad, el vehículo, los precios locales de combustible, los peajes y las múltiples paradas?**

## 1.3 Problema formal

Dada una red vial representada por un grafo, un origen, un destino, un horario de salida, un perfil de vehículo y un conjunto de condiciones ambientales y de circulación, se busca encontrar uno o varios caminos factibles que ofrezcan resultados eficientes en varios objetivos. Entre ellos se encuentran el costo monetario total y la duración del viaje; también pueden contemplarse la seguridad estimada y la incertidumbre del tiempo o costo.

El sistema debe respetar restricciones duras, como cierres confirmados, carreteras no transitables, límites de peso o dimensiones del vehículo y restricciones de acceso. Esas condiciones no deben tratarse como simples penalizaciones económicas que el algoritmo pueda ignorar a cambio de ahorrar unos pesos.

## 1.4 ¿Qué significa «optimizar» en este proyecto?

No se puede prometer una ruta perfecta para todas las circunstancias. La red vial cambia, los datos pueden ser incompletos y los modelos de consumo son aproximaciones. La meta profesional es conseguir una solución:

- **Correcta respecto al modelo:** optimiza el problema matemático definido y respeta sus supuestos.
- **Factible:** no recomienda caminos incompatibles con el vehículo ni tramos que se hayan confirmado como cerrados o intransitables.
- **Económicamente útil:** calcula y explica el costo de las alternativas de forma comparable.
- **Temporalmente confiable:** considera el horario, el tráfico y la variabilidad cuando existan datos suficientes.
- **Escalable:** responde en un tiempo razonable en redes de tamaño relevante.
- **Auditable:** conserva el origen de los datos, las fechas de actualización, los supuestos y el motivo de la recomendación.

La calidad final será una combinación de algoritmo, modelo matemático, datos, operación y validación experimental.

---

# 2. Objetivos, alcance e hipótesis

## 2.1 Objetivo general

Diseñar y evaluar un modelo de optimización multiobjetivo basado en grafos para recomendar rutas que equilibren el costo económico y el tiempo de viaje, sujeto a restricciones de factibilidad y seguridad, considerando las características del vehículo y las condiciones cambiantes del entorno.

## 2.2 Objetivos específicos

1. Revisar las principales técnicas de caminos mínimos, optimización multiobjetivo, enrutamiento dependiente del tiempo y planificación de rutas con múltiples paradas.
2. Definir una representación matemática de la red vial y de los costos de recorrer cada segmento.
3. Investigar modelos de consumo de combustible que incorporen vehículo, velocidad, pendiente, tráfico y carga.
4. Determinar qué fuentes de datos permiten estimar tráfico, precios de combustible, peajes, condiciones meteorológicas, inundaciones y seguridad territorial.
5. Comparar algoritmos exactos y aproximados bajo escenarios controlados y datos reales cuando estén disponibles.
6. Proponer una arquitectura modular que separe las fuentes de datos, la estimación de costos, el motor de optimización y la interfaz de usuario.
7. Evaluar el ahorro estimado, la precisión temporal y de consumo, la factibilidad de las rutas y el rendimiento computacional.

## 2.3 Hipótesis de trabajo

Una estimación segmentada del consumo y del tiempo, combinada con una búsqueda multiobjetivo y restricciones explícitas de factibilidad, puede producir recomendaciones más útiles para el costo total del conductor que las estrategias que solo minimizan la distancia o el tiempo.

La hipótesis no debe considerarse demostrada hasta que los resultados se comparen con rutas de referencia y, en una fase posterior, con recorridos reales y mediciones de combustible.

## 2.4 Alcance recomendado del primer prototipo

Para evitar una complejidad imposible de evaluar desde el inicio, el primer MVP debería limitarse a:

- Un perfil de transporte inicial, preferentemente automóvil particular.
- Origen y destino, con horario de salida elegido.
- Dos objetivos principales: costo monetario y tiempo.
- Costos de combustible calculados a partir de un perfil de vehículo y un precio elegido o consultado.
- Peajes cuando exista información confiable.
- Una lista de rutas alternativas o un motor de enrutamiento que permita construir candidatos.
- Restricciones de acceso y de transitabilidad basadas en información disponible.
- Resultados explicables: costo, duración, combustible estimado, peajes, ahorro frente a rutas de referencia y fecha de los datos.

La seguridad territorial, la incertidumbre probabilística, la optimización flexible de paradas, las flotas, la autonomía eléctrica y el abastecimiento en estaciones concretas son extensiones posteriores.

---

# 3. Estado del arte

## 3.1 Eco-routing y estimación de consumo

El *eco-routing* estudia cómo seleccionar rutas que reduzcan el consumo de combustible, energía o emisiones. La revisión de Fahmin y colaboradores (publicada en *ACM Computing Surveys*, vol. 57, n.º 1) revisó 2,494 artículos y seleccionó 76 estudios de acuerdo con criterios de inclusión. Organiza la literatura en cinco taxonomías: modelos de estimación, problemas y algoritmos de eco-routing, tipos de vehículos, tráfico y características de la red vial [S1].

Esta revisión es un punto de entrada apropiado para el estado del arte porque muestra que el resultado depende de dos grandes componentes: (1) estimar correctamente el consumo o las emisiones en una ruta y (2) encontrar un camino que optimice ese valor dentro de la red.

Un algoritmo de rutas puede ser matemáticamente correcto y aun así recomendar una ruta poco conveniente si las estimaciones de combustible son deficientes. Por eso la estimación del costo no debe considerarse un detalle secundario.

## 3.2 Modelos de consumo de combustible

Zhou, Jin y Wang (2016), en su revisión sobre modelos de consumo publicada en *Transportation Research Part D: Transport and Environment*, comparan enfoques usados para evaluar eco-driving y eco-routing y analizan factores que afectan el consumo [S2]. El consumo real es no lineal y depende de factores que incluyen velocidad, aceleraciones, detenciones, vehículo, carretera y condiciones de circulación. Un rendimiento nominal expresado únicamente en km/l es útil para una primera aproximación, pero no representa con precisión todas las condiciones de un viaje.

Para EcoRuta se recomienda comenzar con una tabla de rendimiento o una curva empírica por rangos de velocidad y después calibrar el modelo con mediciones reales. Si los datos lo permiten, se puede incorporar pendiente, masa transportada, detenciones, operación de accesorios y condiciones de tráfico. No se debe asumir que la cilindrada, por sí sola, determina el consumo: es una característica relevante del vehículo, pero no sustituye una curva o medición de rendimiento.

## 3.3 Rutas dependientes del tiempo

Gendreau, Ghiani y Guerriero (2015), en *Time-dependent routing problems: A review*, describen el enrutamiento donde el tiempo de recorrido de una arista puede variar durante el horizonte de planificación. También distinguen problemas de origen a destino de problemas de múltiples puntos y analizan cómo influye la calidad y evolución de la información [S3]. Una revisión posterior de Adamo y colaboradores (2024) estudia avances en ruteo vehicular dependiente del tiempo, predicción de tiempos de viaje y reoptimización en tiempo real [S6].

Esto es fundamental para las horas pico y el tráfico dinámico. El costo de cruzar un segmento no debe ser necesariamente una constante: su duración puede depender de la hora a la que el vehículo llega al segmento. La ruta óptima para salir a las 10:00 puede dejar de serlo si la salida cambia a las 17:30.

## 3.4 Caminos mínimos multiobjetivo

En los problemas de camino mínimo multiobjetivo, cada ruta posee un vector de resultados, por ejemplo costo y tiempo. Una ruta es **no dominada** cuando no existe otra ruta factible que sea igual o mejor en todos los objetivos y estrictamente mejor en al menos uno. El conjunto de rutas no dominadas constituye la frontera de Pareto.

Kergosien y colaboradores publicaron un algoritmo exacto de tipo *label-correcting* para el problema de camino mínimo multiobjetivo de un origen a un destino. El trabajo describe técnicas de mejora y experimentos con grafos grandes, incluso con millones de nodos y aristas en conjuntos de prueba [S4]. Es evidencia de que los métodos exactos pueden ser competitivos, pero no garantiza que un modelo más complejo de EcoRuta tenga el mismo rendimiento: el resultado depende de los objetivos, las restricciones y la estructura de los datos.

## 3.5 Planificación de múltiples visitas

Cuando un viaje requiere visitar varios lugares, existen dos problemas diferentes:

1. **Secuencia fija:** se debe visitar A, luego B y luego C. Se puede calcular cada tramo y sumar los costos, teniendo en cuenta el horario de llegada.
2. **Secuencia flexible:** hay que visitar A, B, C y D, pero el orden puede cambiar. En ese caso también se optimiza la secuencia, lo que conduce a problemas de tipo TSP o VRP.

Si además existen ventanas horarias, límites de carga, varios vehículos o un depósito, el problema se vuelve más complejo. La literatura de VRP con ventanas de tiempo ofrece métodos exactos y heurísticos para estas situaciones [S5]. Google OR-Tools documenta modelos de rutas y ventanas de tiempo que pueden utilizarse como referencia o componente auxiliar [D8].

## 3.6 Consecuencia para EcoRuta

La investigación no debe buscar un algoritmo mágico único. Debe elegir técnicas diferentes según la tarea:

- Un modelo de estimación para asignar tiempo, consumo y riesgo a cada tramo.
- Un algoritmo de camino multiobjetivo para generar alternativas entre origen y destino.
- Un selector de preferencias para elegir una alternativa equilibrada.
- Un optimizador de visitas si el orden de paradas puede cambiar.
- Un sistema de actualización para recalcular o corregir la ruta cuando cambien las condiciones.

---

# 4. Modelo del problema mediante grafos

## 4.1 Grafo vial dirigido

Se propone representar la red vial mediante un grafo dirigido y ponderado:

\[
G=(V,E)
\]

Donde:

- \(V\) es el conjunto de nodos: intersecciones, accesos, cruces, estaciones, destinos y otros puntos relevantes.
- \(E\) es el conjunto de aristas dirigidas: segmentos de carretera que conectan dos nodos y respetan el sentido de circulación.
- \(P\) es un camino factible entre el origen y el destino, formado por una secuencia de aristas.
- \(t\) representa el instante de salida o llegada a un segmento.
- \(v\) representa el perfil del vehículo o modo de transporte.
- \(\omega\) representa el escenario ambiental y operacional: tráfico, clima, cierres, incidentes y demás condiciones.

Las aristas pueden contener atributos relativamente estáticos —longitud, tipo de vía, pendiente estimada, límite de velocidad— y atributos dinámicos —velocidad actual, condiciones meteorológicas, cierre o incidente temporal—.

## 4.2 Por qué los pesos no pueden ser siempre constantes

Un modelo sencillo puede asignar a cada arista una distancia y un costo fijo. Sin embargo, eso no representa bien tráfico, horas pico ni condiciones variables. Para avanzar hacia un modelo realista se necesita una función de costo dependiente de variables relevantes:

\[
\mathbf{w}_e(t,v,\omega)=
\begin{bmatrix}
C_e(t,v,\omega)\\
T_e(t,v,\omega)\\
R_e(t,\omega)\\
U_e(t,v,\omega)
\end{bmatrix}
\]

Aquí cada componente representa un objetivo o una medida que debe controlarse. El vector puede ampliarse, pero no conviene convertir toda entrada en un objetivo. Por ejemplo, la lluvia es principalmente una condición que modifica el tiempo, el consumo y ciertos riesgos, no necesariamente un objetivo independiente.

## 4.3 Estado de búsqueda

En un modelo temporal, no basta con que el algoritmo conozca el nodo actual. La hora de llegada afecta el costo de las siguientes aristas. Si se optimizan paradas o combustible disponible, el estado puede necesitar más información:

\[
s=(i,t,b,M)
\]

Donde, a modo conceptual:

- \(i\): nodo actual.
- \(t\): hora o intervalo de llegada.
- \(b\): estado de combustible o energía disponible, si se modela abastecimiento.
- \(M\): conjunto de visitas realizadas, si el orden de paradas se optimiza.

No todas las implementaciones necesitan almacenar todo este estado desde el inicio. La selección depende del alcance del problema y de la complejidad aceptable.

## 4.4 Concurrencia y tráfico

El término «concurrencia» debe precisarse en el diseño. Puede referirse a volumen de vehículos, densidad, flujo, conflictos de intersección o cantidad de vehículos que atraviesan un punto por intervalo. No son variables intercambiables. Si se dispone de velocidades o niveles de tráfico directamente de un proveedor, conviene usarlos como observaciones del estado vial; si se dispone de conteos, se necesita un modelo que relacione esos conteos con velocidad y demora.

## 4.5 Restricciones viales

Cada arista debe comprobar las reglas relevantes del vehículo:

- Sentido de circulación y acceso permitido.
- Altura, peso, ancho, longitud y número de ejes, si corresponde.
- Tipo de vehículo admitido en la vía.
- Restricciones horarias y de acceso.
- Cierres y tramos declarados intransitables.
- Compatibilidad con autonomía y abastecimiento en modelos avanzados.

Las restricciones confirmadas deben tratarse como condiciones de factibilidad, no como penalizaciones que puedan compensarse por un costo menor.

---

# 5. Variables consideradas por EcoRuta

## 5.1 Costo monetario

La dimensión monetaria puede incorporar:

- Combustible o energía consumida.
- Peajes y tarifas viales.
- Estacionamiento u otros gastos durante el trayecto, si corresponden.
- Costos variables adicionales por kilómetro, si el sistema está orientado a flotas (mantenimiento variable, desgaste, etc.).
- Costo de abastecer combustible en distintas estaciones, si se modela esa decisión.

Conviene distinguir **costo directo del viaje** y **costo operativo ampliado**. El MVP debe comenzar por combustible y peajes; los costos de mantenimiento son más difíciles de calcular de forma fiable sin datos del vehículo y de operación.

## 5.2 Tiempo y tráfico

Variables relevantes:

- Distancia y velocidad estimada por tramo.
- Horario de salida y hora probable de llegada a cada arista.
- Horas pico y patrones históricos.
- Tráfico actual o nivel de congestión.
- Semáforos, intersecciones, detenciones y giros, cuando el proveedor lo permita.
- Restricciones temporales o eventos de vía.

La duración total es la suma de los tiempos de cada segmento evaluados a la hora a la que se espera recorrerlos. En redes con tráfico dependiente del tiempo, recalcular la hora de llegada a cada tramo es esencial.

## 5.3 Vehículo o medio de transporte

Perfil mínimo recomendado:

- Tipo de transporte: automóvil, motocicleta, camión, autobús, bicicleta, caminata u otro modo admitido.
- Marca, modelo, año y versión, si se pueden identificar correctamente.
- Tipo de combustible o fuente de energía.
- Rendimiento observado por velocidad o tipo de trayecto.
- Cilindrada, tipo de motor y transmisión como datos auxiliares.
- Masa del vehículo y carga transportada.
- Dimensiones, altura, ancho, largo y número de ejes cuando afecten restricciones o peajes.
- Autonomía y combustible/energía disponible cuando se analice el abastecimiento.

El cilindraje no debe utilizarse como un sustituto directo del rendimiento. Dos vehículos con la misma cilindrada pueden tener consumos distintos por peso, aerodinámica, transmisión, motor, mantenimiento y patrones de conducción. En lo posible, debe priorizarse información específica del vehículo o calibrada mediante datos reales.

Los modelos eléctricos requieren una formulación energética distinta: consumo en kWh, regeneración, estado de carga, estaciones compatibles, potencia de carga y tiempos de recarga. Es preferible incorporarlos como una extensión especializada en vez de aplicarles una fórmula de litros por kilómetro.

## 5.4 Carretera y topografía

- Distancia por segmento.
- Pendiente positiva o negativa y perfil de elevación.
- Tipo de superficie y estado conocido de la vía.
- Curvatura, clase de camino, velocidad permitida y cantidad estimada de detenciones.
- Restricciones y accesibilidad.

La pendiente puede afectar el consumo y el tiempo; el tipo de vía, la velocidad y la frecuencia de detenciones afectan el comportamiento esperado del vehículo.

## 5.5 Clima y condiciones ambientales

- Precipitación actual y pronosticada.
- Temperatura.
- Viento, visibilidad y fenómenos meteorológicos relevantes.
- Alertas oficiales y severidad estimada.
- Hora del pronóstico y grado de incertidumbre.

El clima no debe convertirse automáticamente en una penalización uniforme. Su efecto depende del tramo, del tipo de vehículo, de las condiciones reales y de la severidad del fenómeno. La lluvia ligera y una inundación que cubre la calzada no son situaciones equivalentes.

## 5.6 Inundaciones, cierres y peligros viales

Las capas de peligro por inundación y los registros de eventos históricos permiten reconocer zonas expuestas, pero no confirman por sí mismos el estado actual de una carretera. Se debe distinguir entre:

1. **Susceptibilidad o peligro histórico:** aumenta la atención sobre una zona, pero no prueba que esté cerrada hoy.
2. **Alerta o reporte actual:** aporta evidencia temporal que puede requerir validación.
3. **Cierre confirmado o vía intransitable:** puede convertir una arista en no factible.

El sistema debe guardar el origen y la hora de cada alerta, y mostrar cuando la información sea incompleta o antigua.

## 5.7 Seguridad e incidencia delictiva

Los datos del SESNSP se basan en delitos reportados por las fiscalías y carpetas de investigación. Son importantes para análisis territorial, pero la desagregación estatal o municipal no equivale a una probabilidad precisa de sufrir un delito en una calle específica.

Para estimar seguridad por segmento se necesitaría, de manera ideal, información georreferenciada y temporal con calidad suficiente, metodología documentada y denominadores adecuados para medir exposición. Cuando solo existan datos municipales, el sistema debe etiquetar la estimación como territorial o de baja resolución; no debe dibujarla como un nivel preciso de seguridad de cada tramo.

La seguridad puede modelarse como:

- Una restricción para excluir condiciones definidas como inaceptables, cuando la evidencia lo justifique.
- Un objetivo o indicador de exposición territorial para comparar rutas admisibles.
- Una explicación informativa que indique la antigüedad, escala espacial y confianza de los datos.

No debe prometer «ruta segura» ni presentar estadísticas agregadas como garantía. El algoritmo debe evitar estigmatizar comunidades por registros incompletos o diferencias de denuncia.

## 5.8 Precios de combustible y abastecimiento

Para cada combustible y estación se necesita, idealmente:

- Ubicación de la estación.
- Tipo de combustible.
- Precio reportado y moneda.
- Fecha y hora del reporte.
- Estado del dato: actualizado, vencido o no disponible.
- Compatibilidad con el vehículo.

La CNE ofrece precios reportados por estación de servicio y señala en su página de consulta una actualización diaria a las 18:00, hora GMT-6. Se debe verificar la documentación vigente y la fecha de cada registro antes de usarlo. El dato reportado no necesariamente representa una medición instantánea en el dispensador al momento de llegar.

Si el sistema decide dónde cargar combustible, el problema cambia: hay que incorporar estaciones como puntos de paso, autonomía, combustible restante, desvío, tiempo de carga y evolución de precios. Este componente es más complejo que calcular el gasto a partir de un único precio por litro.

## 5.9 Consistencia o confiabilidad

En este proyecto se interpreta «constancia» como **consistencia del tiempo y del costo**: una ruta que, aun sin ser la más rápida en promedio, suele tener resultados más predecibles puede ser valiosa para quien debe llegar a una hora determinada.

Se podrían evaluar:

- Variación histórica del tiempo de viaje.
- Percentiles de duración, por ejemplo P50 y P90.
- Error observado entre tiempo estimado y real.
- Variación del consumo ante cambios de velocidad o tráfico.
- Frescura y nivel de confianza de los datos.

La confiabilidad no debe confundirse con seguridad física. Pueden relacionarse en el análisis general, pero deben tener definiciones y métricas distintas.

---

# 6. Formulación matemática preliminar

## 6.1 Costo de combustible por segmento

Una aproximación básica para un vehículo convencional es:

\[
C_f=\frac{D}{R}\times P
\]

Donde:

- \(D\): distancia recorrida en kilómetros.
- \(R\): rendimiento en kilómetros por litro.
- \(P\): precio por litro.
- \(C_f\): costo monetario estimado del combustible.

Este modelo sirve como línea base, pero supone un rendimiento constante. No debe considerarse un modelo final si se busca capturar variaciones de pendiente, velocidad, tráfico y carga.

En un modelo segmentado, el combustible consumido en una arista se representa como:

\[
L_e=f(e,v,\bar{u}_e,\ell,g_e,q_e,\omega)
\]

Donde \(v\) identifica el vehículo; \(\bar{u}_e\), el perfil de velocidad; \(\ell\), la masa o carga; \(g_e\), la pendiente y características del tramo; \(q_e\), las detenciones y aceleraciones estimadas; y \(\omega\), el contexto de circulación y clima. Si se estima el consumo en litros, el costo de combustible del tramo puede escribirse como:

\[
C_{f,e}=L_e\cdot P_e
\]

El precio \(P_e\) debe corresponder a la estrategia de abastecimiento definida. Si el combustible se compra en más de una estación, el modelo debe decidir en qué punto abastecer, no asignar arbitrariamente el precio de una única estación a todos los litros.

## 6.2 Costo total del viaje

Una primera definición operativa es:

\[
C(P)=\sum_{e\in P} L_eP_e + C_{peajes}(P)+C_{otros}(P)
\]

\(C_{otros}\) es opcional y debe activarse solo cuando exista un método razonable de estimación. Para un MVP, puede fijarse en cero o excluirse explícitamente.

Los peajes pueden depender del tipo de vehículo, número de ejes, categoría vial y método de pago. Si no hay tarifa fiable, la aplicación debe marcar el costo como desconocido o estimado, no presentar una cifra inventada.

## 6.3 Tiempo dependiente de la hora

El tiempo para recorrer una arista se representa como:

\[
\tau_e=\tau_e(t,v,\omega)
\]

La hora de llegada al siguiente segmento depende de la hora de llegada al segmento actual:

\[
t_{i+1}=t_i+\tau_{e_i}(t_i,v,\omega)
\]

Así se modelan las horas pico, los cambios de tráfico y las restricciones temporales. Si la fuente entrega solamente una duración estática, el sistema debe registrar que el resultado tiene menor sensibilidad al horario.

## 6.4 Riesgo e incertidumbre

El riesgo y la incertidumbre deben definirse antes de asignarles valores. Un indicador territorial derivado de delitos municipales no debe interpretarse automáticamente como probabilidad de delito por kilómetro.

De forma conceptual, puede utilizarse:

\[
R(P)=\sum_{e\in P} r_e\,x_e
\]

Donde \(r_e\) es un indicador de riesgo con escala y procedencia documentadas, y \(x_e\) representa una medida de exposición, como tiempo o longitud recorrida. La validez de esta fórmula depende de que \(r_e\) tenga una interpretación consistente para cada segmento.

La incertidumbre puede representarse con la variación de la duración o el costo bajo distintos escenarios. Si existen datos suficientes, se pueden estimar percentiles o evaluar el costo en escenarios de tráfico y clima. Si no existen, es preferible reportar la falta de información en vez de asignar una confianza ficticia.

## 6.5 Vector multiobjetivo

Una formulación inicial sería:

\[
\min_{P\in\mathcal{F}}\mathbf{F}(P)=
\left[C(P),\;T(P),\;R(P),\;U(P)\right]
\]

Donde:

- \(C(P)\): costo monetario total estimado.
- \(T(P)\): duración del viaje.
- \(R(P)\): indicador de riesgo definido para el modelo.
- \(U(P)\): incertidumbre o variabilidad de tiempo/costo.
- \(\mathcal{F}\): conjunto de rutas factibles que cumplen las restricciones.

No es obligatorio activar todos los objetivos desde la primera versión. Para el MVP se recomienda comenzar con costo y tiempo, y tratar los peligros graves como restricciones duras. Seguridad territorial y confiabilidad pueden incorporarse cuando las medidas sean defendibles y los datos lo permitan.

## 6.6 Restricciones de factibilidad

El conjunto \(\mathcal{F}\) puede definirse con condiciones como:

- La ruta comienza en el origen y termina en el destino.
- Cada arista respeta el sentido de circulación.
- No se atraviesan tramos confirmados como cerrados o intransitables.
- El vehículo cumple las restricciones de peso, dimensiones y tipo.
- La autonomía y capacidad son suficientes si el modelo las considera.
- Se respetan las ventanas horarias o fechas límite del usuario.
- Se evitan zonas o condiciones que se hayan definido explícitamente como no admisibles y existan datos adecuados para identificarlas.

La seguridad debe tratarse cuidadosamente: no todos los datos permiten justificar una exclusión automática. Las restricciones por riesgo necesitan criterios publicados y evaluación para evitar resultados injustos o falsos niveles de certeza.

## 6.7 Selección mediante suma ponderada

Después de generar rutas no dominadas, el sistema puede permitir que el usuario elija un equilibrio entre costo y tiempo:

\[
J(P)=C(P)+\lambda T(P)
\]

Si \(C\) se mide en pesos y \(T\) en minutos, \(\lambda\) debe expresarse en pesos por minuto. El parámetro indica cuánto estaría dispuesto a pagar el usuario por ahorrar tiempo.

Esto es más interpretable que asignar pesos sin unidades. También es necesario evitar sumar valores en unidades incompatibles sin normalización o interpretación económica. La suma ponderada no encuentra necesariamente todas las soluciones eficientes en un problema discreto o no convexo; por eso se recomienda usarla como selector de preferencias y compararla con métodos de restricciones.

## 6.8 Método de restricciones ε

Otra forma de formular la preferencia es:

\[
\min C(P)\quad\text{sujeto a}\quad T(P)\leq T_{max}
\]

Se pueden añadir restricciones de riesgo, autonomía o hora de llegada. Esta formulación es muy explicable: «minimizar el costo sin tardar más de 90 minutos».

También se puede invertir el objetivo —minimizar tiempo bajo un presupuesto máximo—. Al resolver el problema con diferentes límites se obtiene una visión del compromiso entre objetivos.

## 6.9 Dominancia de Pareto

Una ruta \(P_1\) domina a una ruta \(P_2\) si es igual o mejor en todos los objetivos minimizados y estrictamente mejor en por lo menos uno. Las rutas dominadas se pueden descartar sin que el usuario pierda una alternativa eficiente respecto a los objetivos considerados.

En algoritmos de etiquetado, el mismo criterio se utiliza para descartar estados parciales cuando la etiqueta alternativa es comparable en el mismo estado y cumple las condiciones de dominancia. En modelos dependientes del tiempo o con recursos, la comparación debe incluir las variables de estado necesarias; no es correcto comparar dos etiquetas solo porque se encuentran en una coordenada geográfica si representan horarios o recursos incompatibles.

---

# 7. Comparación de algoritmos

## 7.1 Dijkstra

**Objetivo:** encontrar un camino de costo mínimo cuando cada arista tiene un costo no negativo y se optimiza una función escalar.

**Ventajas:** es bien conocido, tiene garantías formales y funciona como línea base sólida. Si el costo de una arista expresa pesos de combustible más peajes, Dijkstra puede encontrar el camino mínimo según esa función si el grafo y los costos están bien definidos.

**Limitaciones:** la versión convencional no genera una frontera costo-tiempo. Para varios objetivos, el problema no se resuelve simplemente guardando un único costo por nodo.

**Uso en EcoRuta:** algoritmo de referencia y herramienta para prototipos de mínimo costo o mínimo tiempo.

## 7.2 A*

**Objetivo:** acelerar la búsqueda hacia un destino utilizando una heurística que estime el costo restante.

**Ventajas:** puede explorar menos nodos cuando la heurística es informativa y cumple las propiedades requeridas.

**Limitaciones:** la heurística debe ser compatible con la función de costo. Una distancia en kilómetros no se puede sumar directamente a pesos; es necesario convertirla en una cota monetaria admisible o utilizar otra estimación consistente. A* convencional optimiza un objetivo y no produce por sí solo todas las soluciones de Pareto.

**Uso en EcoRuta:** comparar eficiencia para búsquedas de un objetivo y estudiar extensiones multiobjetivo si el rendimiento de la red lo requiere.

## 7.3 Enrutamiento dependiente del tiempo

No es una sola familia de algoritmo, sino una propiedad del modelo: los tiempos o costos de las aristas cambian con la hora. Puede combinarse con técnicas de búsqueda específicas. El algoritmo debe evaluar el costo de una arista en el tiempo de llegada previsto, no necesariamente al momento en que se inició toda la ruta.

**Ventaja:** representa mejor tráfico y horas pico.

**Limitación:** requiere datos temporales y cuidado con las propiedades matemáticas del modelo. Un dato histórico por hora no equivale a información de tráfico en vivo.

**Uso en EcoRuta:** componente necesario para una versión que considere el horario de salida y el tráfico variable.

## 7.4 Etiquetado multiobjetivo: label-setting y label-correcting

En lugar de almacenar una sola distancia por nodo, estos algoritmos mantienen etiquetas con los costos acumulados de caminos parciales. Por ejemplo:

\[
L=(C,T,R,U)
\]

Las etiquetas dominadas se eliminan y las no dominadas continúan explorándose. Las variantes *label-setting* y *label-correcting* difieren en cómo seleccionan, procesan y actualizan etiquetas; ambas son familias relevantes para el problema.

**Ventajas:** modelan directamente el conjunto de soluciones no dominadas y, bajo los supuestos adecuados, pueden ofrecer resultados exactos.

**Limitaciones:** el número de etiquetas puede crecer mucho. Cuando se agregan objetivos, restricciones de tiempo, carga, combustible o visitas, la cantidad de estados puede aumentar y el costo computacional convertirse en un cuello de botella.

**Uso en EcoRuta:** candidato principal para el núcleo de optimización de origen a destino. Debe implementarse primero en grafos controlados y compararse con un algoritmo de referencia.

## 7.5 Suma ponderada

Convierte varios objetivos en uno mediante pesos o coeficientes de preferencia. La forma costo-tiempo \(J(P)=C(P)+\lambda T(P)\) permite expresar una disposición a pagar por tiempo.

**Ventajas:** simple, rápido y relativamente fácil de explicar.

**Limitaciones:** los pesos pueden ser arbitrarios si no reflejan preferencias reales; las unidades deben interpretarse correctamente; algunos puntos eficientes de la frontera de Pareto pueden no aparecer mediante sumas ponderadas en problemas discretos.

**Uso en EcoRuta:** selector para personalizar recomendaciones y línea de comparación experimental, pero no el único método de investigación.

## 7.6 Método de restricciones ε

Optimiza un objetivo y restringe los demás, por ejemplo minimizar el gasto bajo una duración máxima.

**Ventajas:** permite restricciones claras y verificables; encaja bien con solicitudes como «no gastar más de $250» o «llegar antes de las 18:00».

**Limitaciones:** generar toda la frontera puede exigir resolver el modelo varias veces y escoger valores límite apropiados.

**Uso en EcoRuta:** método recomendado para transformar necesidades del usuario en una decisión auditable.

## 7.7 Métodos evolutivos y NSGA-II

Los algoritmos evolutivos mantienen una población de soluciones y usan selección, recombinación y mutación para aproximar una frontera de Pareto. NSGA-II es una alternativa conocida en optimización multiobjetivo.

**Ventajas:** pueden explorar problemas combinatorios donde resulta difícil enumerar todas las alternativas; sirven para investigar rutas con varias paradas y muchos criterios.

**Limitaciones:** normalmente no garantizan el óptimo global; los resultados dependen de parámetros, representación y criterio de parada. Requieren comparación con referencias y análisis de estabilidad.

**Uso en EcoRuta:** candidato para secuencias complejas de paradas o redes grandes cuando los métodos exactos resulten demasiado costosos.

## 7.8 Búsqueda local, ALNS y OR-Tools para múltiples paradas

Para visitas en orden flexible se pueden estudiar técnicas de búsqueda local, búsqueda tabú, algoritmos genéticos y *Adaptive Large Neighborhood Search* (ALNS), además de herramientas como OR-Tools. Un optimizador de ruta multipunto necesita definir si cada destino se visita una vez, si hay ventanas horarias, si existe un depósito, si se permiten varios vehículos y cuál es la función objetivo.

**Ventaja:** pueden encontrar soluciones útiles para problemas de rutas combinatorias.

**Limitación:** si se usan heurísticas, la solución normalmente no se debe presentar como óptimo matemático garantizado.

**Uso en EcoRuta:** capa independiente de planificación de paradas, que invoca el modelo de costo vial para evaluar los tramos.

## 7.9 Tabla comparativa

| Método | Tipo de problema | Exactitud o garantía | Escalabilidad típica | Rol propuesto |
|---|---|---|---|---|
| Dijkstra | Un objetivo, pesos no negativos | Exacto para el modelo definido | Buena con estructuras adecuadas; puede explorar mucho | Línea base de distancia, tiempo o costo |
| A* | Un objetivo y destino definido | Exacto con heurística apropiada | A menudo explora menos nodos | Aceleración y comparación |
| Búsqueda dependiente del tiempo | Aristas con costos temporales | Depende del algoritmo y supuestos temporales | Depende de la representación y los datos | Tráfico y horas pico |
| Label-setting / label-correcting | Caminos multiobjetivo | Puede ser exacto | Frontera de Pareto puede crecer mucho | Núcleo multiobjetivo |
| Suma ponderada | Varios objetivos convertidos en uno | Exacta para la función escalar elegida, no para toda la frontera | Generalmente sencilla | Personalización costo-tiempo |
| Restricciones ε | Un objetivo con límites en otros | Puede resolver exactamente cada subproblema si se usa un método exacto | Resolver toda la frontera puede ser costoso | Límites de tiempo y presupuesto |
| NSGA-II y otros evolutivos | Optimización multiobjetivo combinatoria | Normalmente aproximada | Flexible, depende de configuración | Problemas grandes y multipunto |
| Búsqueda local / ALNS / OR-Tools | TSP/VRP y variantes | Depende del método y configuración | Útil para muchos problemas prácticos | Orden de visitas y flotas |

### Recomendación de algoritmos

Para el primer estudio, no se recomienda empezar por NSGA-II. Primero es necesario demostrar una formulación consistente y comparar:

1. Dijkstra para tiempo mínimo, distancia mínima o una función escalar de costo.
2. Un etiquetado multiobjetivo para obtener alternativas costo-tiempo.
3. Un selector por suma ponderada y otro por restricciones ε.
4. Una heurística de rutas multipunto solo cuando se incorpore el orden flexible de paradas.

Este diseño permite conocer qué mejora aporta cada componente.

---

# 8. Tratamiento de rutas con múltiples paradas

## 8.1 Orden fijo

Si el usuario define el orden A → B → C → destino, se calcula cada tramo con su hora de llegada y se agregan costos. La estimación de un tramo debe considerar el tiempo de salida desde el punto anterior; no siempre es correcto sumar tiempos calculados para una misma hora fija.

## 8.2 Orden flexible

Si el usuario solo entrega el conjunto {A, B, C, D}, el sistema debe encontrar el orden conveniente. Esto puede ser un TSP o una variante de VRP. El crecimiento combinatorio hace poco adecuado intentar enumerar todos los órdenes cuando el número de visitas es grande.

## 8.3 Restricciones adicionales

El modelo puede necesitar:

- Ventanas de llegada a cada punto.
- Duración del servicio o tiempo de estancia.
- Obligación de regresar al origen.
- Capacidad y autonomía del vehículo.
- Estaciones de abastecimiento o carga.
- Varios vehículos y capacidades, para un uso de flotillas.

## 8.4 Estrategia sugerida

Separar el sistema en dos niveles:

1. Un modelo de camino vial que calcula alternativas y costos entre pares de puntos.
2. Un optimizador de la secuencia de visitas que usa esos costos para planificar el recorrido completo.

Cuando el tiempo depende de la hora, la matriz de costos entre puntos también puede depender del horario y de la secuencia previa. En esos casos, no se debe tratar la matriz como si fuera completamente estática sin validar esa aproximación.

---

# 9. Fuentes de datos y proveedores

## 9.1 Criterios para seleccionar fuentes

Cada fuente debe evaluarse por:

- Cobertura geográfica, especialmente en ciudades, caminos rurales y carreteras.
- Resolución espacial y temporal.
- Latencia y frecuencia de actualización.
- Exactitud, completitud y método de medición.
- Disponibilidad de histórico y posibilidad de validar el dato.
- Licencia, condiciones de uso, atribución y límites de almacenamiento.
- Costo por consulta, volumen permitido y disponibilidad de un servicio estable.
- Capacidad de identificar la fecha y fuente de cada observación.

No se recomienda combinar datos como si todos fueran igualmente actuales. Deben conservarse metadatos de fuente, timestamp, cobertura y calidad.

## 9.2 Cartografía y red vial

### INEGI: Red Nacional de Caminos (RNC)

La RNC es una representación cartográfica digital y georreferenciada de la infraestructura vial mexicana, estructurada para apoyar el cálculo de rutas. Su documentación indica que incluye carreteras, vialidades, caminos rurales y conexiones de transporte; también contempla información de tarifas de peaje por tipo de vehículo y número de ejes, así como estaciones de abastecimiento en los atributos descritos por el producto. INEGI también informa de un servicio de ruteo denominado SAKBÉ [D1].

**Ventaja:** es una fuente especialmente relevante para un proyecto centrado en México.  
**Limitación:** hay que revisar la edición, la actualización, el diccionario, la licencia y las condiciones específicas del servicio antes de utilizarlo en producción.

Enlace: https://www.inegi.org.mx/programas/rnc/

### OpenStreetMap (OSM)

OpenStreetMap ofrece datos cartográficos abiertos bajo la Open Database License (ODbL). El uso de sus datos requiere atribución; el tratamiento y la redistribución de bases derivadas deben respetar la licencia [D2].

**Ventaja:** cobertura amplia y ecosistema de herramientas.  
**Limitación:** la calidad y actualidad pueden variar por zona; disponer de datos de carreteras no equivale a disponer de tráfico actual, precios o cierres en vivo.

Enlace: https://www.openstreetmap.org/  
Licencia: https://www.openstreetmap.org/copyright/es

### OSRM

OSRM es un motor de enrutamiento de código abierto que ofrece servicios HTTP para obtener rutas, tablas de duración/distancia y otras operaciones. Su servicio de ruta busca el camino más rápido según el perfil preparado y permite solicitar alternativas, aunque estas no están garantizadas en todas las consultas [D3].

**Uso sugerido:** obtener geometrías o candidatos de ruta en un prototipo; para un modelo económico propio se debe verificar cómo representar costos personalizados y si el motor estándar cumple las necesidades.

Enlace: https://project-osrm.org/docs/v5.24.0/api/

### Valhalla

Valhalla es un motor de rutas de código abierto que admite diferentes modos de transporte y opciones de costo configurables. Su documentación describe cómo una solicitud define ubicaciones, modo y modelo de costo [D4].

**Uso sugerido:** alternativa a estudiar cuando se requiera mayor control sobre los costos y preferencias del enrutamiento. La flexibilidad exacta debe probarse con el perfil y versión que se elija.

Enlace: https://valhalla.github.io/valhalla/api/turn-by-turn/overview/

## 9.3 APIs comerciales de rutas

### Google Maps Platform Routes API

La Routes API permite calcular rutas, tiempos y distancias, obtener rutas alternativas y solicitar información de tráfico y peajes, según las funciones, región y condiciones del producto. Google también documenta la funcionalidad de rutas ecológicas y estimación del consumo a partir del tipo de motor y factores como tráfico y características de la vía [D5–D8].

Hay limitaciones importantes para el diseño de EcoRuta:

- La disponibilidad de rutas ecológicas varía por región.
- La documentación consultada indica que el modo ecológico no admite puntos de referencia intermedios en esa funcionalidad.
- La solicitud de rutas alternativas y las opciones de peajes tienen condiciones y posibles costos de facturación.
- La API calcula rutas con el modelo del proveedor; no entrega automáticamente control absoluto sobre el algoritmo interno de optimización.
- Deben revisarse las condiciones de uso, atribución, almacenamiento y facturación antes de depender del servicio.

**Uso sugerido:** prototipo rápido para obtener rutas candidatas, distancias, duraciones, tráfico y posiblemente peajes o información ecológica donde esté disponible. No se debe confundir la comparación de alternativas del proveedor con una búsqueda exacta del óptimo monetario en toda la red.

Documentación:
- https://developers.google.com/maps/documentation/routes/
- https://developers.google.com/maps/documentation/routes/eco-routes?hl=es-419
- https://developers.google.com/maps/documentation/routes/alternative-routes?hl=es-419
- https://developers.google.com/maps/documentation/routes/traffic_on_polylines?hl=es
- https://developers.google.com/maps/documentation/routes/calculate_toll_fees?hl=es

### HERE Routing API

La documentación de HERE contempla estimaciones de consumo por tramo y parámetros de vehículo. Su modelo empírico para vehículos de combustión permite utilizar curvas de consumo según la velocidad en condiciones de flujo libre y tráfico denso, y considera componentes adicionales como el consumo de sistemas auxiliares y el ascenso. La documentación señala que la funcionalidad del modelo de consumo de combustible se encuentra en beta, por lo que puede estar sujeta a cambios [D9–D11].

**Uso sugerido:** estudiar HERE como proveedor candidato para estimación de consumo y tráfico. Antes de seleccionarlo, probar cobertura en México, precisión, costo, condiciones del servicio y estabilidad de las funciones necesarias.

Documentación:
- https://docs.here.com/routing/reference/routing-api-v8-calculateroutes
- https://docs.here.com/routing/docs/routing-v8-consumption-ice-empirical
- https://docs.here.com/routing/docs/routing-v8-calculate-fuel-consumption
- https://docs.here.com/routing/docs/routing-v8-traffic-in-routing

## 9.4 Precios de combustible en México

La CNE publica una consulta de precios comerciales reportados por permisionarios, con listado de precios de gasolina regular, premium y diésel por estación. La página consultada indica una actualización diaria a las 18:00 GMT-6 [D12].

Enlace oficial: https://www.cne.gob.mx/consultaprecios/gasolinasydiesel/gasolinasydiesel.html

Antes de construir un conector automático, se deberá verificar:

- Si existe un archivo descargable estable y su estructura.
- La fecha/hora asociada al registro.
- Qué significa exactamente el precio reportado y cómo se corrigen registros.
- Si hay condiciones técnicas o legales de consulta y redistribución.
- Cómo actuar cuando no existe un precio reciente para una estación.

La estrategia segura es conservar el timestamp y marcar la antigüedad del precio; no mostrar un dato antiguo como si fuese actual.

## 9.5 Clima y meteorología

El Servicio Meteorológico Nacional de CONAGUA es una fuente oficial para información meteorológica en México [D13]. Las APIs meteorológicas de terceros pueden facilitar pronósticos por coordenadas y series temporales, pero se deben revisar cobertura, licencia, periodicidad y condiciones de uso.

Fuente oficial: https://smn.conagua.gob.mx/es/

EcoRuta debe vincular cada pronóstico a su hora de emisión y periodo de validez. Un pronóstico de lluvia puede ajustar una estimación de conducción, pero no prueba que exista una inundación en una carretera ni sustituye una alerta de cierre.

## 9.6 Inundaciones y peligros naturales

CONAGUA documenta el Atlas Nacional de Riesgo por Inundación y remite a las capas publicadas en el Atlas Nacional de Riesgos del CENAPRED. La cobertura y el tipo de información disponible varían por región; algunos atlas representan índices de inundabilidad, inundaciones históricas, ciudades, cuencas, ríos y presas [D14].

Enlaces:
- CONAGUA: https://www.gob.mx/conagua/acciones-y-programas/atlas-nacional-de-riesgo-por-inundacion-204625
- Visor de capas citado por CONAGUA: http://atlasnacionalderiesgos.gob.mx/archivo/visor-capas.html
- CENAPRED: https://www.gob.mx/cenapred

Los mapas de peligro son capas contextuales o históricas. Para convertir un tramo en no transitable se requiere evidencia actual apropiada, como avisos oficiales o reportes de cierre validados.

## 9.7 Seguridad e incidencia delictiva

El SESNSP publica datos abiertos e informes de incidencia delictiva en México. Su documentación explica que la información se deriva de presuntos delitos registrados en averiguaciones previas o carpetas de investigación reportadas por las fiscalías, y que existen datos agregados estatales y municipales [D15–D16].

Enlaces oficiales:
- Información de incidencia delictiva nacional: https://www.gob.mx/sesnsp/acciones-y-programas/informacion-de-incidencia-delictiva-nacional
- Datos abiertos de incidencia delictiva: https://www.gob.mx/sesnsp/acciones-y-programas/datos-abiertos-de-incidencia-delictiva
- Mapas de incidencia delictiva: https://www.gob.mx/sesnsp/documentos/mapas-de-incidencia-delictiva

Estos datos son útiles para una exploración territorial, pero **no deben interpretarse como una probabilidad precisa de delito por calle o segmento vial** cuando la resolución publicada es municipal o estatal. Los niveles de denuncia, los cambios metodológicos, el tamaño de población y los tiempos de publicación afectan la interpretación.

## 9.8 Peajes y costos de vía

La Red Nacional de Caminos de INEGI documenta tarifas de peaje por tipo de vehículo y número de ejes [D1]. La Routes API de Google también puede estimar tarifas en determinadas ubicaciones, considerando ciertas configuraciones de vehículo y pase de peaje; la propia documentación advierte que hay rutas sin precio disponible y regiones con soporte limitado [D8].

Enlace RNC: https://www.inegi.org.mx/programas/rnc/  
Enlace Google: https://developers.google.com/maps/documentation/routes/calculate_toll_fees?hl=es

Toda tarifa debe clasificarse como confirmada, reportada, estimada o desconocida. La salida de EcoRuta debe declarar cuál de esas categorías aplica.

## 9.9 Resumen de disponibilidad de datos

| Componente | Fuente inicial | ¿Puede considerarse en vivo? | Precaución principal |
|---|---|---|---|
| Geometría vial | INEGI RNC u OSM | No por defecto | Verificar fecha y cobertura |
| Ruta y tiempo | OSRM, Valhalla, Google o HERE | Depende del proveedor y configuración | El motor puede optimizar un criterio distinto al de EcoRuta |
| Tráfico | Proveedor con tráfico o histórico | Depende del servicio | Distinguir dato actual de promedio histórico |
| Combustible | CNE o entrada manual | No necesariamente | Conservar fecha y hora del precio |
| Clima | SMN/CONAGUA o API meteorológica | Según fuente | Un pronóstico no confirma estado vial |
| Inundaciones | CONAGUA/CENAPRED | No necesariamente | Atlas de peligro no es cierre vial en tiempo real |
| Delincuencia | SESNSP | Generalmente estadístico/periódico | La granularidad no suele equivaler a tramo vial |
| Peajes | INEGI RNC/proveedor/operador | Según la fuente | Tarifa por tipo de vehículo y disponibilidad |
| Consumo real | Datos de usuario, telemetría o modelo | Solo si se recopila continuamente | Calibración, privacidad y sesgos |

---

# 10. Arquitectura conceptual

## 10.1 Principios

La arquitectura debe separar los conectores externos de la lógica de optimización. Así, si se cambia el proveedor cartográfico, no es necesario reescribir el modelo matemático. También debe existir una capa de normalización de unidades, timestamps, calidad y coordenadas.

## 10.2 Módulos propuestos

1. **Interfaz de usuario:** ingreso de origen, destino, paradas, vehículo, combustible, horario y preferencias; visualización del mapa y de las alternativas.
2. **API de aplicación:** administra usuarios, vehículos, viajes, preferencias y solicitudes de cálculo.
3. **Capa de integración de datos:** obtiene datos cartográficos, tráfico, clima, cierres, precios y peajes.
4. **Normalizador y almacenamiento:** transforma los datos a un esquema interno, guarda el origen, la fecha, el estado de calidad y las unidades.
5. **Estimador de costo por arista:** calcula tiempo, combustible, precio, peajes, indicadores de riesgo e incertidumbre.
6. **Motor de grafos y búsqueda:** implementa las líneas base y el algoritmo multiobjetivo.
7. **Optimizador multipunto:** determina el orden de visitas cuando el usuario permite cambiarlo.
8. **Selector de preferencias:** filtra rutas no factibles y ordena las alternativas según presupuesto, hora límite y disposición a pagar por tiempo.
9. **Monitor de cambios:** identifica cambios de condiciones y decide si se necesita recalcular.
10. **Evaluación y telemetría:** registra predicciones y resultados observados, con consentimiento y protección de datos.

## 10.3 Tecnologías posibles

La tecnología debe elegirse después de validar el modelo; no debe condicionar la formulación matemática. Una combinación posible para una aplicación web es:

- Frontend: React + TypeScript.
- API de negocio: Laravel/PHP o un backend equivalente.
- Base de datos: PostgreSQL con PostGIS para datos geográficos y relaciones; el diseño final depende del volumen y del tipo de datos.
- Procesamiento de rutas: servicio separado para el motor de grafos si el cálculo exige más recursos que la API web.
- Mapas: proveedor externo o capas basadas en datos abiertos, respetando licencia y atribución.
- Colas y tareas programadas: para actualizar datos y ejecutar cálculos costosos sin bloquear solicitudes web.

Esta es una arquitectura de referencia, no una decisión definitiva. Deben medirse el volumen de peticiones, latencia, costo de los proveedores y carga de cálculo antes de seleccionar infraestructura.

## 10.4 Flujo de una petición

1. El usuario introduce origen, destino, paradas opcionales, vehículo, hora y preferencias.
2. El sistema valida entradas y restricciones del vehículo.
3. Los conectores recuperan una red/rutas y datos de contexto disponibles.
4. El normalizador indica la antigüedad y calidad de cada fuente.
5. El estimador calcula el vector de costo para cada tramo o candidato.
6. El optimizador genera rutas no dominadas o rutas candidatas según el método configurado.
7. El selector aplica los límites de seguridad y factibilidad y ordena las alternativas.
8. La interfaz presenta costo, duración, combustible, peajes, ahorro frente a referencias e incertidumbre.
9. Si cambian condiciones críticas, el monitor determina si puede hacer una replanificación y explica por qué.

---

# 11. Propuesta de experimentación y evaluación

## 11.1 Líneas base

Para probar si EcoRuta realmente aporta valor, deben compararse métodos con las mismas condiciones iniciales:

1. Ruta de menor distancia.
2. Ruta de menor tiempo previsto.
3. Ruta de menor consumo estimado.
4. Ruta de menor costo monetario total (combustible + peajes que puedan calcularse).
5. Ruta seleccionada por suma ponderada costo-tiempo.
6. Conjunto de rutas no dominadas generado por el algoritmo multiobjetivo.
7. En la fase multipunto, un método de referencia para el orden de visitas y, si procede, una heurística.

La ruta más corta, la más rápida y la de menor costo no deben suponerse equivalentes. La prueba busca medir cuánto difieren en escenarios comparables.

## 11.2 Escenarios de prueba

Se recomienda construir escenarios que varíen:

- Longitud del trayecto: urbano corto, interurbano y de carretera larga.
- Hora de salida: hora valle y horas pico.
- Vehículo: distintos perfiles de rendimiento y tipo de energía.
- Precio de combustible: estación local, precio manual o escenarios de sensibilidad.
- Peajes: con peajes, evitando peajes y casos con tarifas desconocidas.
- Clima: condiciones normales y escenarios meteorológicos cuando haya datos adecuados.
- Cierres o inundaciones simuladas: retirar una o más aristas para comprobar que no sean utilizadas.
- Seguridad y calidad de datos: alta, baja o desactualizada, evitando presentar datos agregados como precisos por calle.
- Paradas: orden fijo y flexible.

Las inundaciones y cierres deben probarse primero en simulación. No se recomienda depender de alertas experimentales para navegación operativa sin validar la fuente.

## 11.3 Métricas

### Calidad económica

- Costo total estimado por viaje.
- Ahorro absoluto en pesos respecto a cada línea base.
- Ahorro porcentual, cuando el denominador sea distinto de cero.
- Diferencia entre costo previsto y costo observado, cuando existan viajes reales comparables.

### Precisión temporal

- Error absoluto medio (MAE) entre tiempo previsto y observado.
- Error porcentual cuando sea apropiado.
- Percentiles de duración, por ejemplo mediana (P50) y P90.
- Variación de la duración por hora de salida.

### Precisión de consumo

- Error entre litros previstos y litros medidos.
- Error por clase de vehículo, tipo de trayecto y condición de tráfico.
- Calibración del modelo con datos de entrenamiento separados de la evaluación.

### Seguridad y factibilidad

- Número y porcentaje de rutas que violan restricciones.
- Capacidad de evitar aristas declaradas cerradas en los escenarios de prueba.
- Cobertura y antigüedad de la información utilizada.
- Trazabilidad de las razones por las cuales una ruta se excluye o recibe una advertencia.

### Calidad multiobjetivo

- Cantidad de soluciones no dominadas.
- Tiempo de cálculo y memoria.
- Número de etiquetas exploradas y podadas.
- Comparación de la frontera obtenida con una frontera de referencia en grafos pequeños.
- En experimentos evolutivos, métricas de calidad como hipervolumen o distancia generacional, siempre que se defina una referencia válida y se expliquen sus supuestos.

### Eficiencia operacional

- Latencia de respuesta del sistema.
- Costo económico por consulta del proveedor externo.
- Tasa de fallos de cada fuente.
- Tiempo necesario para actualizar o recalcular una ruta.

## 11.4 Diseño experimental

1. **Validación matemática en grafos pequeños:** construir ejemplos donde se pueda enumerar todos los caminos factibles y comprobar si el algoritmo devuelve la frontera correcta.
2. **Pruebas sintéticas de escala:** aumentar nodos, aristas y objetivos; medir tiempo, memoria y crecimiento de etiquetas.
3. **Evaluación con red real:** ejecutar casos de origen-destino en una región con cartografía adecuada.
4. **Validación temporal:** comparar horarios y, si hay datos, velocidades históricas frente a observaciones separadas.
5. **Validación de consumo:** comparar contra viajes reales, perfil específico de vehículo o un modelo de proveedor que sirva como referencia, sin tratarlo como verdad absoluta.
6. **Pruebas multipunto:** comparar secuencias fijas y flexibles bajo iguales ventanas de tiempo y restricciones.
7. **Análisis de sensibilidad:** variar los pesos, los límites de tiempo, los precios y la incertidumbre para observar si la recomendación cambia de forma razonable.

Si se usan datos históricos, conviene separar periodos de entrenamiento y prueba para evitar que el algoritmo sea evaluado con información que no habría estado disponible en el momento de planificar el viaje.

## 11.5 Ejemplo ilustrativo

Supóngase un vehículo con rendimiento de 14 km/l y gasolina a $24 MXN/litro. Una ruta de 100 km consumiría 100/14 ≈ 7.14 litros y costaría alrededor de $171.43 MXN en combustible, antes de agregar peajes u otros gastos. Una ruta de 115 km, bajo la simplificación de rendimiento constante, costaría aproximadamente $197.14 MXN en combustible.

Si la primera ruta incluye $80 en peajes y la segunda no incluye peajes, el costo estimado sería $251.43 frente a $197.14. La segunda costaría aproximadamente $54.29 menos; si además tardara 20 minutos más, el conductor podría evaluar si ese ahorro compensa el tiempo adicional.

Este ejemplo es didáctico, no una recomendación de ruta real. El supuesto de consumo constante es limitado: un modelo avanzado podría estimar rendimientos distintos por velocidad, pendiente, tráfico, carga y detenciones, y la diferencia real podría cambiar.

---

# 12. Riesgos, limitaciones y consideraciones éticas

## 12.1 Datos incompletos o desactualizados

Un algoritmo no puede inferir con exactitud una inundación o un precio actual si la fuente no lo registra. Debe identificar la antigüedad, mostrar la falta de información y preferir alternativas conservadoras cuando exista un peligro crítico confirmado.

## 12.2 Dependencia de proveedores

Las APIs externas pueden tener costos, límites, variaciones de cobertura y condiciones contractuales. Una solución basada en un proveedor debe respetar las condiciones de uso y tener un plan para errores o interrupciones. Las fuentes abiertas requieren igualmente verificar licencias, calidad y atribución.

## 12.3 Riesgo y falsa precisión

Las estadísticas territoriales no deben convertirse sin justificación en puntuaciones exactas por calle. Si se presenta un indicador de riesgo, deben aclararse escala, metodología, antigüedad y límites de interpretación. No debe garantizarse que una ruta sea segura.

## 12.4 Privacidad

Las ubicaciones, horarios y hábitos de viaje pueden ser datos sensibles en la práctica. El sistema debe recolectar solo lo necesario, proteger identificadores y ubicaciones, definir retención de datos y pedir consentimiento cuando se almacenen recorridos reales. Si se emplea telemetría para calibrar consumo, se debe explicar qué se guarda y para qué.

## 12.5 Incertidumbre de las estimaciones

El costo calculado es una predicción; puede cambiar por tráfico, precios, estilo de conducción, mantenimiento y condiciones no observadas. La interfaz debería usar expresiones como «estimado», informar cuándo se consultaron los datos y evitar cifras excesivamente precisas cuando el modelo no las respalde.

## 12.6 Seguridad por encima del ahorro

Una función monetaria no debe permitir que una condición peligrosa se compense con un ahorro económico. Los cierres confirmados, restricciones viales y condiciones de inviabilidad deben ser restricciones duras. La política para otras clases de riesgo debe definirse con criterios públicos y evidencia apropiada.

## 12.7 No confundir óptimo del modelo con óptimo real

Si el algoritmo encuentra la ruta más barata con los datos y supuestos introducidos, solo ha demostrado optimalidad respecto a ese modelo. No prueba que el gasto real vaya a ser el mínimo posible. La validación empírica es indispensable.

---

# 13. Plan de trabajo recomendado

## Etapa 1. Investigación teórica

- Leer las revisiones de eco-routing y enrutamiento dependiente del tiempo.
- Definir los objetivos, la unidad y la semántica de cada variable.
- Estudiar Dijkstra, A*, dominancia de Pareto y algoritmos de etiquetado multiobjetivo.
- Delimitar los casos con tiempo dependiente y los problemas multipunto.
- Documentar los supuestos y las restricciones del modelo.

**Entregable:** marco teórico, glosario, matriz de variables y formulación inicial.

## Etapa 2. Prototipo matemático

- Crear grafos pequeños a mano.
- Implementar Dijkstra como línea base.
- Implementar una versión inicial de etiquetado multiobjetivo para costo y tiempo.
- Comprobar la frontera de Pareto contra enumeración exhaustiva en grafos pequeños.
- Medir número de etiquetas y tiempo de ejecución.

**Entregable:** algoritmo reproducible con pruebas unitarias y ejemplos demostrables.

## Etapa 3. Prueba cartográfica

- Seleccionar una región piloto.
- Comparar INEGI RNC, OSM y motores de rutas disponibles.
- Elegir proveedor o estrategia de enrutamiento de acuerdo con cobertura, costo, licencia y acceso a geometría.
- Normalizar las rutas a segmentos de grafo.

**Entregable:** demo origen-destino sobre una red real, todavía con modelos de costo simples.

## Etapa 4. Modelo de costo y tiempo

- Definir perfil del vehículo y precio de combustible.
- Incorporar duración dinámica si la fuente ofrece tráfico temporal.
- Calcular peajes cuando haya datos fiables.
- Añadir el primer selector mediante suma ponderada y restricciones ε.
- Presentar costo y tiempo estimados en la interfaz.

**Entregable:** comparación de rutas económicas y rápidas en una región piloto.

## Etapa 5. Condiciones de riesgo y datos dinámicos

- Integrar clima y alertas con metadatos temporales.
- Añadir capas de peligrosidad por inundación, diferenciándolas de cierres confirmados.
- Explorar los datos de incidencia delictiva y documentar su resolución espacial.
- Definir calidad, caducidad y manejo de fuentes ausentes.

**Entregable:** modelo de factibilidad, avisos de calidad de datos y análisis de escenarios.

## Etapa 6. Múltiples paradas y optimización avanzada

- Resolver primero rutas con secuencia fija.
- Añadir secuencia flexible como TSP/VRP si el caso de uso lo exige.
- Comparar métodos exactos con heurísticas y medir la calidad de soluciones aproximadas.
- Optimizar el rendimiento mediante poda, caché o partición regional cuando corresponda.

**Entregable:** experimento comparativo multipunto con resultados reproducibles.

## Etapa 7. Validación

- Comparar predicciones con trayectos observados.
- Calibrar consumo y tiempo por vehículo y contexto.
- Medir ahorro, errores, latencia y factibilidad.
- Documentar limitaciones, amenazas a la validez y condiciones para desplegar el sistema.

**Entregable:** informe de resultados y criterios para decidir si el sistema está listo para pruebas de campo.

---

# 14. Conclusiones y decisión técnica

La propuesta de EcoRuta es un problema de optimización de rutas con costos económicos y temporales que cambian según la hora y el contexto. Una función simple basada en distancia y km/l puede servir para el primer prototipo, pero no basta para modelar correctamente un sistema que contemple tráfico, clima, peso, pendiente, peajes, riesgo y múltiples paradas.

La revisión sugiere una estrategia híbrida:

1. **Grafo dirigido** para representar la red vial y sus restricciones.
2. **Estimador por segmento** para costo de combustible, peajes, tiempo y variables de riesgo o incertidumbre que tengan datos defendibles.
3. **Etiquetado multiobjetivo** para encontrar alternativas no dominadas de costo y tiempo.
4. **Restricciones duras y método ε** para manejar condiciones que no deben violarse y límites expresados por el usuario.
5. **Suma ponderada como selector** cuando sea útil expresar la disposición a pagar por tiempo.
6. **Optimizador TSP/VRP** solo cuando el orden de visitas deba elegirse o existan flotas.
7. **Comparación experimental** frente a rutas más cortas, más rápidas y de menor costo escalar.

En el MVP deben priorizarse costo monetario y tiempo. Cierres confirmados y restricciones del vehículo se aplican desde el inicio como condiciones de factibilidad. Los modelos de consumo más sofisticados, la seguridad territorial, la incertidumbre y el abastecimiento por estación se incorporan cuando existan datos suficientes para evaluarlos.

La afirmación de valor que puede investigar EcoRuta no es «siempre encontrará la ruta perfecta», sino: **«compara rutas factibles mediante un modelo de costo personalizable, explica el compromiso entre tiempo y dinero y muestra la incertidumbre y procedencia de los datos usados»**.

---

# 15. Anexo A: matriz de variables y requisitos de datos

| Variable | Tipo | Unidad o formato sugerido | Efecto en el modelo | Fuente inicial posible | Prioridad MVP |
|---|---|---|---|---|---|
| Origen/destino | Entrada | Coordenadas o identificadores de lugar | Define el problema | Usuario/geocodificador | Alta |
| Distancia por tramo | Red vial | m o km | Consumo, duración | RNC, OSM, proveedor | Alta |
| Hora de salida | Entrada | Fecha-hora con zona horaria | Determina costos temporales | Usuario/reloj | Alta |
| Velocidad o tráfico | Dinámica | km/h, categoría o factor de demora | Tiempo y consumo | Proveedor/histórico | Alta si está disponible |
| Tipo de vehículo | Perfil | Categoría y restricciones | Define vías factibles y modelo de consumo | Usuario/ficha técnica | Alta |
| Rendimiento | Perfil/calibración | km/l o curva velocidad-consumo | Combustible | Usuario/medición/modelo | Alta |
| Cilindrada | Perfil auxiliar | cm³ o L | Variable explicativa, no sustituto del consumo | Ficha del vehículo | Media |
| Masa/carga | Perfil | kg | Consumo/restricciones | Usuario/ficha técnica | Media |
| Pendiente | Geoespacial | porcentaje o elevación por tramo | Consumo y tiempo | Elevación/mapa | Media |
| Precio de combustible | Variable temporal/espacial | MXN/litro, fecha-hora, estación | Costo monetario | CNE/entrada manual | Alta |
| Peaje | Costo | MXN, categoría de vehículo | Costo monetario | RNC/proveedor/operador | Alta si aplica |
| Clima | Dinámica | precipitación, temperatura, viento, visibilidad | Ajusta tiempo/consumo/riesgo | SMN/API | Media |
| Inundación | Alerta/capa de peligro | Geometría, nivel, timestamp | Restricción o alerta según evidencia | CONAGUA/CENAPRED/aviso | Alta para aviso de peligro confirmado |
| Incidencia delictiva | Estadística territorial | tasa/conteo, zona, periodo y metodología | Indicador de exposición con límites explícitos | SESNSP | Posterior |
| Variabilidad temporal | Histórico | desviación, percentiles o distribución | Confiabilidad del viaje | Proveedor/observaciones | Posterior |
| Paradas | Entrada | Lista de coordenadas, ventana de tiempo | Secuencia de visita | Usuario | Alta solo en caso multipunto |
| Autonomía | Perfil | km, litros o kWh disponibles | Factibilidad/abastecimiento | Usuario/vehículo | Posterior |
| Estaciones de combustible/carga | POI | Coordenadas, tipo, precio, disponibilidad | Decisión de abastecimiento | RNC/operadores/proveedores | Posterior |
| Calidad del dato | Metadatos | fuente, timestamp, cobertura, confianza | Advertencias/poda conservadora | Cada conector | Alta |

---

# 16. Anexo B: fuentes oficiales y documentación técnica

> **Nota de mantenimiento:** los enlaces son puntos de partida para la investigación. La existencia de una página no garantiza que un endpoint sea gratuito, estable, reutilizable sin condiciones o apto para navegación en tiempo real. Antes de implementar un conector se deben revisar su documentación vigente, licencia, términos de servicio, límites y fecha de actualización.

## B.1 Fuentes oficiales de México

| Código | Fuente | Uso para EcoRuta | Enlace |
|---|---|---|---|
| D1 | INEGI — Red Nacional de Caminos | Red vial georreferenciada, ruteo, atributos de vía y referencias de peaje | https://www.inegi.org.mx/programas/rnc/ |
| D12 | CNE — Precios de expendio de gasolinas y diésel | Precios reportados por estación y tipo de combustible | https://www.cne.gob.mx/consultaprecios/gasolinasydiesel/gasolinasydiesel.html |
| D13 | Servicio Meteorológico Nacional / CONAGUA | Información meteorológica y pronóstico | https://smn.conagua.gob.mx/es/ |
| D14 | CONAGUA — Atlas Nacional de Riesgo por Inundación | Capas de inundación y peligrosidad | https://www.gob.mx/conagua/acciones-y-programas/atlas-nacional-de-riesgo-por-inundacion-204625 |
| D14a | Visor del Atlas Nacional de Riesgos | Consulta visual de capas de riesgo | http://atlasnacionalderiesgos.gob.mx/archivo/visor-capas.html |
| D14b | CENAPRED | Prevención y documentación de riesgos | https://www.gob.mx/cenapred |
| D15 | SESNSP — Información de incidencia delictiva nacional | Contexto y metodología de las estadísticas de incidencia | https://www.gob.mx/sesnsp/acciones-y-programas/informacion-de-incidencia-delictiva-nacional |
| D16 | SESNSP — Datos abiertos de incidencia delictiva | Bases de datos estatales y municipales | https://www.gob.mx/sesnsp/acciones-y-programas/datos-abiertos-de-incidencia-delictiva |
| D16a | SESNSP — Mapas de incidencia delictiva | Mapas agregados de estadísticas de delitos | https://www.gob.mx/sesnsp/documentos/mapas-de-incidencia-delictiva |

## B.2 Cartografía y motores de enrutamiento

| Código | Fuente | Uso para EcoRuta | Enlace |
|---|---|---|---|
| D2 | OpenStreetMap — sitio de datos | Cartografía abierta | https://www.openstreetmap.org/ |
| D2a | OpenStreetMap — derechos y licencia | Condiciones ODbL y atribución | https://www.openstreetmap.org/copyright/es |
| D3 | OSRM — documentación API | Rutas, tablas, geometrías y alternativas | https://project-osrm.org/docs/v5.24.0/api/ |
| D4 | Valhalla — descripción de servicio de rutas | Enrutamiento abierto con modelos de costo configurables | https://valhalla.github.io/valhalla/api/turn-by-turn/overview/ |

## B.3 APIs comerciales de rutas y tráfico

| Código | Fuente | Uso para EcoRuta | Enlace |
|---|---|---|---|
| D5 | Google Maps Platform — Routes API | Rutas, matriz de rutas, alternativas y configuraciones | https://developers.google.com/maps/documentation/routes/ |
| D6 | Google — rutas ecológicas | Estimación de ruta eficiente y consumo estimado según disponibilidad regional | https://developers.google.com/maps/documentation/routes/eco-routes?hl=es-419 |
| D7 | Google — rutas alternativas | Solicitud de rutas alternativas y limitaciones de puntos intermedios | https://developers.google.com/maps/documentation/routes/alternative-routes?hl=es-419 |
| D7a | Google — tráfico en polilíneas | Información de tráfico por segmentos de geometría | https://developers.google.com/maps/documentation/routes/traffic_on_polylines?hl=es |
| D8 | Google — tarifas de peaje | Estimaciones de peajes donde están soportadas | https://developers.google.com/maps/documentation/routes/calculate_toll_fees?hl=es |
| D8a | Google OR-Tools — VRP con ventanas de tiempo | Modelado y ejemplo de rutas multipunto | https://developers.google.com/optimization/routing/vrptw |
| D9 | HERE — cálculo de rutas | Parámetros de vehículo, costos y atributos de rutas | https://docs.here.com/routing/reference/routing-api-v8-calculateroutes |
| D10 | HERE — modelo empírico de combustible | Curvas de consumo para flujo libre y tráfico | https://docs.here.com/routing/docs/routing-v8-consumption-ice-empirical |
| D11 | HERE — consumo y CO₂ por sección | Ejemplos de consumo segmentado | https://docs.here.com/routing/docs/routing-v8-calculate-fuel-consumption |
| D11a | HERE — tráfico en enrutamiento | Tráfico en vivo/histórico y restricciones temporales según disponibilidad | https://docs.here.com/routing/docs/routing-v8-traffic-in-routing |

---

# 17. Anexo C: bibliografía científica inicial

Las siguientes referencias ayudan a organizar el marco teórico. Se recomienda consultar el texto completo cuando esté disponible, documentar qué método se adopta y no trasladar resultados de un artículo a EcoRuta sin replicar las condiciones experimentales.

## C.1 Eco-routing

**[S1]** Fahmin, A., Cheema, M. A., Eunus Ali, M., Nadjaran Toosi, A., Lu, H., Li, H., Taniar, D., Rakha, H. A., & Shen, B. (2024). *Eco-Friendly Route Planning Algorithms: Taxonomies, Literature Review and Future Directions*. ACM Computing Surveys, 57(1), Article 21. https://doi.org/10.1145/3691624

Enlace adicional de la institución investigadora: https://research.monash.edu/en/publications/eco-friendly-route-planning-algorithms-taxonomies-literature-revi/

**Utilidad:** taxonomía de algoritmos, modelos de estimación, vehículos, tráfico y redes viales; punto inicial principal para el estado del arte.

## C.2 Modelos de consumo de combustible

**[S2]** Zhou, M., Jin, H., & Wang, W. (2016). *A review of vehicle fuel consumption models to evaluate eco-driving and eco-routing*. Transportation Research Part D: Transport and Environment, 49, 203–218. https://doi.org/10.1016/j.trd.2016.09.008

Página de la revista: https://www.sciencedirect.com/science/article/abs/pii/S1361920916306009

**Utilidad:** compara modelos de consumo y sus limitaciones; respalda la decisión de no utilizar únicamente una relación fija de km/l para todas las condiciones.

## C.3 Enrutamiento dependiente del tiempo

**[S3]** Gendreau, M., Ghiani, G., & Guerriero, E. (2015). *Time-dependent routing problems: A review*. Computers & Operations Research, 64, 189–197. https://doi.org/10.1016/j.cor.2015.06.001

Página de la revista: https://www.sciencedirect.com/science/article/pii/S030505481500146X

**Utilidad:** clasificación de problemas de uno o varios puntos y revisión de modelos de tiempos de viaje variables.

## C.4 Camino mínimo multiobjetivo

**[S4]** Kergosien, Y., Giret, A., Néron, E., & Sauvanet, G. (2022; publicado en línea el 26 de agosto de 2021). *An Efficient Label-Correcting Algorithm for the Multiobjective Shortest Path Problem*. INFORMS Journal on Computing, 34(1), 76–92. https://doi.org/10.1287/ijoc.2021.1081

Página del editor: https://pubsonline.informs.org/doi/abs/10.1287/ijoc.2021.1081

**Utilidad:** algoritmo exacto de etiquetado para calcular caminos no dominados y evaluación computacional en grafos grandes. Es un candidato relevante para estudiar el núcleo multiobjetivo de EcoRuta.

## C.5 Problema de rutas con ventanas de tiempo

**[S5]** Bräysy, O., & Gendreau, M. (2005). *Vehicle Routing Problem with Time Windows, Part I: Route Construction and Local Search Algorithms*. Transportation Science, 39(1), 104–118. https://doi.org/10.1287/trsc.1030.0056

Página del editor: https://pubsonline.informs.org/doi/fpi/10.1287/trsc.1030.0056

**Utilidad:** métodos de construcción de rutas y búsqueda local para la planificación de visitas con restricciones de tiempo.

**[S6]** Adamo, T., Gendreau, M., Ghiani, G., & Guerriero, E. (2024). *A review of recent advances in time-dependent vehicle routing*. European Journal of Operational Research, 319(1), 1–15. https://doi.org/10.1016/j.ejor.2024.06.016

Página de la revista: https://doi.org/10.1016/j.ejor.2024.06.016

**Utilidad:** revisión reciente sobre predicción de tiempos, reoptimización en tiempo real, discretización dinámica y métodos relacionados con el ruteo temporal.

## C.6 Documentación técnica complementaria

**[D1]** Instituto Nacional de Estadística y Geografía (INEGI). *Red Nacional de Caminos*. https://www.inegi.org.mx/programas/rnc/

**[D2]** OpenStreetMap Foundation. *Copyright and License*. https://www.openstreetmap.org/copyright/es

**[D3]** Project OSRM. *OSRM HTTP API Documentation*. https://project-osrm.org/docs/v5.24.0/api/

**[D4]** Valhalla. *Routing overview*. https://valhalla.github.io/valhalla/api/turn-by-turn/overview/

**[D5]** Google Maps Platform. *Routes API*. https://developers.google.com/maps/documentation/routes/

**[D6]** Google Maps Platform. *Get an eco-friendly route*. https://developers.google.com/maps/documentation/routes/eco-routes?hl=es-419

**[D7]** Google Maps Platform. *Get alternative routes*. https://developers.google.com/maps/documentation/routes/alternative-routes?hl=es-419

**[D8]** Google Maps Platform. *Calculate toll fees for a route*; Google OR-Tools. *Vehicle Routing Problem with Time Windows*. https://developers.google.com/maps/documentation/routes/calculate_toll_fees?hl=es ; https://developers.google.com/optimization/routing/vrptw

**[D9–D11]** HERE Technologies. *Routing API v8*, *Fuel consumption*, *Calculate fuel consumption and CO₂ emissions per section* y *Traffic in routing*. https://docs.here.com/routing/reference/routing-api-v8-calculateroutes ; https://docs.here.com/routing/docs/routing-v8-consumption-ice-empirical ; https://docs.here.com/routing/docs/routing-v8-calculate-fuel-consumption ; https://docs.here.com/routing/docs/routing-v8-traffic-in-routing

**[D12]** Comisión Nacional de Energía (CNE). *Precios de expendio de gasolinas y diésel*. https://www.cne.gob.mx/consultaprecios/gasolinasydiesel/gasolinasydiesel.html

**[D13]** Servicio Meteorológico Nacional, CONAGUA. https://smn.conagua.gob.mx/es/

**[D14]** Comisión Nacional del Agua (CONAGUA). *Atlas Nacional de Riesgo por Inundación*. https://www.gob.mx/conagua/acciones-y-programas/atlas-nacional-de-riesgo-por-inundacion-204625

**[D15–D16]** Secretariado Ejecutivo del Sistema Nacional de Seguridad Pública (SESNSP). *Información de incidencia delictiva nacional* y *Datos abiertos de incidencia delictiva*. https://www.gob.mx/sesnsp/acciones-y-programas/informacion-de-incidencia-delictiva-nacional ; https://www.gob.mx/sesnsp/acciones-y-programas/datos-abiertos-de-incidencia-delictiva

---

## Nota final sobre el uso del documento

Este documento establece una base para la investigación y una propuesta de diseño. No es una certificación de seguridad vial, no garantiza ahorros reales y no sustituye la validación de las condiciones de una carretera. Antes de utilizar EcoRuta en desplazamientos reales, será necesario validar los datos, las restricciones, los modelos de consumo, la latencia de las fuentes y los procedimientos para avisos de peligro y cierres.
