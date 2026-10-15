import type { ReactElement } from "react";
import { Card, PageShell } from "./PageShell";

export function DocsPage(): ReactElement {
  return (
    <PageShell
      title="Documentación"
      subtitle="Cómo usar EcoRuta, qué calcula y qué significan los resultados."
    >
      <Card title="¿Qué hace EcoRuta?">
        <p>
          Calcula el <b>frente de Pareto</b> entre el <b>costo monetario total</b> (combustible +
          peajes) y el <b>tiempo de viaje</b> para un vehículo dado. No devuelve una sola ruta, sino
          todas las alternativas no dominadas: no existe otra ruta que sea a la vez más barata y más
          rápida.
        </p>
      </Card>
      <Card title="Flujo de uso">
        <ol className="list-decimal space-y-1 pl-5">
          <li>Configura origen, destino y vehículo en el panel izquierdo.</li>
          <li>Ajusta condiciones (hora de salida, carga, tipo de día) y tus preferencias.</li>
          <li>Presiona <b>Optimizar ruta</b>. El panel se colapsa y aparece el resumen.</li>
          <li>
            Revisa las gráficas: costo, tiempo y el frente de Pareto. Haz clic en una barra o en un
            botón para cambiar la alternativa activa trazada en el mapa.
          </li>
        </ol>
      </Card>
      <Card title="Alternativas recomendadas">
        <ul className="list-disc space-y-1 pl-5">
          <li><b>Más barata:</b> minimiza el costo total.</li>
          <li><b>Más rápida:</b> minimiza el tiempo de viaje.</li>
          <li><b>Equilibrada:</b> el punto de codo del frente (mejor compromiso costo/tiempo).</li>
          <li><b>Tu preferencia:</b> usa el valor que asignas a un minuto (MXN/min).</li>
        </ul>
      </Card>
      <Card title="Modo robusto (P90)">
        <p>
          Con el modo robusto activado, el motor optimiza sobre velocidades del percentil 10 (peor
          congestión), por lo que los tiempos reflejan un escenario conservador/robusto.
        </p>
      </Card>
    </PageShell>
  );
}

export function ContextPage(): ReactElement {
  return (
    <PageShell
      title="Contexto"
      subtitle="El entorno vial mexicano y las variables que condicionan el ruteo."
    >
      <Card title="Restricciones físicas duras">
        <p>
          En México existen límites regulatorios de <b>altura</b> (típicamente ≤ 4.15–5.5 m según
          vía) y <b>peso por eje</b> (NOM-012-SCT). Las aristas que violan el gálibo del vehículo se
          excluyen del subgrafo antes de la búsqueda. Un dato de cierre confirmado también desactiva
          la arista.
        </p>
      </Card>
      <Card title="Congestión dependiente del tiempo">
        <p>
          La velocidad de cada tramo varía por hora del día y tipo de día. El motor usa perfiles
          horarios regularizados para cumplir la condición <b>FIFO</b>, evitando "adelantar" a otros
          vehículos en la red.
        </p>
      </Card>
      <Card title="Peajes y precios de combustible">
        <p>
          Los peajes provienen de la Red Nacional de Caminos (RNC/SAKBÉ) y los precios de
          combustible de la Comisión Nacional de Energía (CNE). Cada respuesta incluye la auditoría
          de procedencia con su fuente y fecha.
        </p>
      </Card>
      <Card title="Seguridad y riesgo hídrico">
        <p>
          Los datos del SESNSP tienen resolución <b>municipal</b>. Nunca se asignan puntuaciones por
          calle: se muestran como <b>avisos contextuales</b> y, cuando aplica, como zonas de riesgo
          hídrico del Atlas Nacional (CONAGUA).
        </p>
      </Card>
    </PageShell>
  );
}

export function BackgroundPage(): ReactElement {
  return (
    <PageShell
      title="Antecedentes"
      subtitle="El problema de ruteo multiobjetivo y los algoritmos empleados."
    >
      <Card title="El problema">
        <p>
          El ruteo biobjetivo busca el conjunto de rutas no dominadas entre costo y tiempo. A
          diferencia del camino más corto clásico (Dijkstra), aquí ambas magnitudes interactúan: una
          ruta con más kilómetros puede ser más rápida pero más cara, y viceversa.
        </p>
      </Card>
      <Card title="TD-MOLS (Time-Dependent Multi-Objective Label Setting)">
        <p>
          Algoritmo de etiquetado que expande etiquetas por nodo manteniendo el <b>conjunto de
          Pareto</b> local. Se podan etiquetas dominadas y se frena la expansión con una cota
          (épsilon) para acotar el número de etiquetas por nodo. Los tiempos dependen de la hora de
          llegada a cada arista.
        </p>
      </Card>
      <Card title="Modelo físico de consumo">
        <p>
          El consumo no usa un rendimiento estático (km/l). Se calcula con un modelo longitudinal de
          fuerzas: resistencia aerodinámica, rodadura, trabajo contra la gravedad por pendiente
          (sin α) y energía por inercia asociada a la congestión, calibrado por un factor κ del
          vehículo.
        </p>
      </Card>
      <Card title="Subgrafo factible">
        <p>
          Antes de buscar, se extrae un corredor elíptico alrededor de las rutas candidatas
          extremas, excluyendo cierres y violaciones de gálibo. Esto evita ejecutar el algoritmo
          sobre la red nacional completa.
        </p>
      </Card>
    </PageShell>
  );
}

export function InfoPage(): ReactElement {
  return (
    <PageShell
      title="Información general"
      subtitle="Alcance, procedencia de datos y limitaciones del sistema."
    >
      <Card title="Estado actual">
        <p>
          Esta demostración opera sobre una <b>red sintética</b> de la región piloto
          CDMX–Puebla–Toluca–Querétaro. Los resultados validan el motor; el frente de Pareto es
          correcto para la red cargada, no para la red vial real de México.
        </p>
      </Card>
      <Card title="Procedencia de datos (auditoría)">
        <ul className="list-disc space-y-1 pl-5">
          <li><b>Red vial:</b> RNC/SAKBÉ (INEGI) — en producción.</li>
          <li><b>Combustible:</b> CNE, resolución municipal/estatal.</li>
          <li><b>Peajes:</b> RNC, por caseta.</li>
          <li><b>Clima:</b> pronóstico Open-Meteo/SMN.</li>
          <li><b>Seguridad:</b> SESNSP, resolución municipal (solo contexto).</li>
        </ul>
        <p className="text-xs text-slate-500">
          Cada respuesta incluye el bloque <code>data_provenance_audit</code> con fuente, resolución
          espacial y timestamp.
        </p>
      </Card>
      <Card title="Limitaciones">
        <ul className="list-disc space-y-1 pl-5">
          <li>Solo dos objetivos primarios: costo (MXN) y tiempo (s).</li>
          <li>La incertidumbre se modela con perfiles P50 (esperado) vs. P10 (robusto P90).</li>
          <li>Sin datos reales cargados, los puntos fuera de la malla no tienen ruta.</li>
        </ul>
      </Card>
      <Card title="Stack">
        <p>
          Rust (PyO3) + PostgreSQL/PostGIS/pgRouting + FastAPI/Pydantic v2 + React 19/TypeScript +
          maplibre-gl/deck.gl + recharts.
        </p>
      </Card>
    </PageShell>
  );
}
