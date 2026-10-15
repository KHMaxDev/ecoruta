import type { ReactElement } from "react";
import type { Comparison } from "../types";

interface ComparisonSectionProps {
  comparison: Comparison;
}

/** Comparativa explícita frente a OSRM, Valhalla y Google Maps. */
export default function ComparisonSection({ comparison }: ComparisonSectionProps): ReactElement {
  const rows: { name: string; distance: string; time: string; cost: string; note: string }[] = [
    {
      name: "EcoRuta (recomendada)",
      distance: `${comparison.ecoruta_distance_km.toFixed(1)} km`,
      time: `${comparison.ecoruta_time_min.toFixed(1)} min`,
      cost: `${comparison.ecoruta_cost_mxn.toFixed(2)} MXN`,
      note: "Costo físico + peaje est. + congestión por hora"
    },
    {
      name: "OSRM (ruta más rápida)",
      distance: comparison.osrm_distance_km != null ? `${comparison.osrm_distance_km.toFixed(1)} km` : "—",
      time: comparison.osrm_time_min != null ? `${comparison.osrm_time_min.toFixed(1)} min` : "—",
      cost: "—",
      note: "Geometría real; sin modelo de costo"
    },
    {
      name: "Valhalla (más rápida)",
      distance: "—",
      time: comparison.valhalla_time_min != null ? `${comparison.valhalla_time_min.toFixed(1)} min` : "—",
      cost: "—",
      note: "Geometría real; sin modelo de costo"
    }
  ];

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-xl font-bold text-ecoruta-ink">Comparativa con otras tecnologías</h2>
          <p className="text-sm text-slate-500">{comparison.notes}</p>
        </div>
        <a
          href={comparison.google_maps_url}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-lg bg-ecoruta-ink px-4 py-2 text-sm font-semibold text-white shadow hover:opacity-90"
        >
          Ver el mismo viaje en Google Maps ↗
        </a>
      </div>

      <div className="overflow-x-auto rounded-xl bg-white shadow">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-2">Motor</th>
              <th className="px-4 py-2">Distancia</th>
              <th className="px-4 py-2">Tiempo</th>
              <th className="px-4 py-2">Costo</th>
              <th className="px-4 py-2">Qué aporta</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.name} className={i === 0 ? "bg-emerald-50 font-medium" : "border-t"}>
                <td className="px-4 py-2">{r.name}</td>
                <td className="px-4 py-2">{r.distance}</td>
                <td className="px-4 py-2">{r.time}</td>
                <td className="px-4 py-2">{r.cost}</td>
                <td className="px-4 py-2 text-slate-500">{r.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {comparison.savings_time_vs_osrm_min != null && (
        <p className="text-xs text-slate-500">
          Diferencia de tiempo frente a OSRM:{" "}
          <b>
            {comparison.savings_time_vs_osrm_min >= 0 ? "+" : ""}
            {comparison.savings_time_vs_osrm_min.toFixed(1)} min
          </b>{" "}
          (EcoRuta incorpora la congestión según la hora de salida).
        </p>
      )}
    </section>
  );
}
