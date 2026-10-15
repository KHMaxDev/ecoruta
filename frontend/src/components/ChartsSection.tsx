import type { ReactElement } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { colorFor, labelFor } from "../palette";
import type { OptimizationResult, RoutePoint } from "../types";

interface ChartsSectionProps {
  result: OptimizationResult;
  activeTag: string;
  onSelect: (tag: string) => void;
}

export default function ChartsSection({
  result,
  activeTag,
  onSelect
}: ChartsSectionProps): ReactElement {
  const front = result.pareto_frontier;
  const indexOf = (tag: string): number => front.findIndex((r) => r.recommendation_tag === tag);

  const byTag = (tag: string): RoutePoint | undefined =>
    front.find((r) => r.recommendation_tag === tag);
  const active = byTag(activeTag) ?? result.recommended_knee;

  const costData = front.map((r, i) => ({
    tag: r.recommendation_tag,
    name: labelFor(r.recommendation_tag, i),
    costo: Number(r.total_cost_mxn.toFixed(2)),
    color: colorFor(r.recommendation_tag, i)
  }));

  const timeData = front.map((r, i) => ({
    tag: r.recommendation_tag,
    name: labelFor(r.recommendation_tag, i),
    tiempo: Number(r.duration_minutes.toFixed(1)),
    color: colorFor(r.recommendation_tag, i)
  }));

  const frontierData = [...front]
    .map((r, i) => ({
      tag: r.recommendation_tag,
      name: labelFor(r.recommendation_tag, i),
      tiempo: Number(r.duration_minutes.toFixed(1)),
      costo: Number(r.total_cost_mxn.toFixed(2)),
      color: colorFor(r.recommendation_tag, i)
    }))
    .sort((a, b) => a.tiempo - b.tiempo);

  const savings = active.savings_vs_fastest_mxn;
  const cards = [
    { label: "Costo total", value: `${active.total_cost_mxn.toFixed(2)} MXN`, tone: "text-ecoruta-green" },
    { label: "Tiempo (con congestión)", value: `${active.duration_minutes.toFixed(1)} min`, tone: "text-ecoruta-ink" },
    { label: "Distancia", value: `${active.distance_km.toFixed(1)} km`, tone: "text-ecoruta-ink" },
    { label: "Combustible", value: `${active.total_fuel_liters.toFixed(2)} L`, tone: "text-ecoruta-ink" },
    { label: "Peaje (estimado)", value: `${active.toll_cost_mxn.toFixed(2)} MXN`, tone: "text-amber-600" },
    {
      label: "Ahorro vs. más rápida",
      value: `${savings.toFixed(2)} MXN`,
      tone: savings >= 0 ? "text-green-600" : "text-red-600"
    }
  ];

  const renderBars = (
    data: { tag: string; name: string; color: string; value: number }[],
    dataKey: "costo" | "tiempo",
    unit: string,
    title: string
  ): ReactElement => (
    <div className="rounded-xl bg-white p-3 shadow">
      <h3 className="mb-1 text-sm font-semibold text-slate-700">{title}</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} />
            <YAxis tick={{ fontSize: 11 }} unit={unit} />
            <Tooltip formatter={(v: number) => [`${v} ${unit}`, dataKey === "costo" ? "Costo" : "Tiempo"]} />
            <Bar
              dataKey="value"
              radius={[5, 5, 0, 0]}
              label={{ position: "top", fontSize: 10, fill: "#334155" }}
              onClick={(d: { tag?: string }) => d.tag && onSelect(d.tag)}
            >
              {data.map((d) => (
                <Cell key={d.tag} fill={d.color} fillOpacity={d.tag === activeTag ? 1 : 0.5} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );

  return (
    <section id="resultados" className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-ecoruta-ink">Resumen del cálculo</h2>
          <p className="text-sm text-slate-500">
            {result.pareto_count} alternativa(s) en el frente de Pareto ·{" "}
            <span className="font-medium text-ecoruta-green">
              {labelFor(active.recommendation_tag, indexOf(active.recommendation_tag))}
            </span>{" "}
            seleccionada · red vial real ({active.network_source})
          </p>
        </div>
        <div className="flex flex-wrap gap-1">
          {front.map((r, i) => {
            const selected = r.recommendation_tag === activeTag;
            return (
              <button
                key={r.recommendation_tag}
                type="button"
                onClick={() => onSelect(r.recommendation_tag)}
                className="rounded-full px-3 py-1 text-xs font-semibold text-white shadow-sm transition"
                style={{
                  backgroundColor: colorFor(r.recommendation_tag, i),
                  opacity: selected ? 1 : 0.55,
                  outline: selected ? "2px solid #0f172a" : "none"
                }}
              >
                {labelFor(r.recommendation_tag, i)}
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {cards.map((c) => (
          <div key={c.label} className="rounded-xl bg-white p-3 shadow">
            <p className="text-xs text-slate-500">{c.label}</p>
            <p className={`text-lg font-bold ${c.tone}`}>{c.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {renderBars(
          costData.map((d) => ({ tag: d.tag, name: d.name, color: d.color, value: d.costo })),
          "costo",
          "$",
          "Costo total por alternativa (MXN)"
        )}
        {renderBars(
          timeData.map((d) => ({ tag: d.tag, name: d.name, color: d.color, value: d.tiempo })),
          "tiempo",
          " min",
          "Tiempo por alternativa (min)"
        )}

        <div className="rounded-xl bg-white p-3 shadow">
          <h3 className="mb-1 text-sm font-semibold text-slate-700">
            Frente de Pareto: cada punto es una ruta real
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={frontierData} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="tiempo" type="number" tick={{ fontSize: 11 }} unit=" min" domain={["dataMin - 15", "dataMax + 15"]} />
                <YAxis tick={{ fontSize: 11 }} unit=" $" width={62} />
                <Tooltip
                  formatter={(v: number, name: string) => [name === "costo" ? `${v} MXN` : `${v} min`, name]}
                  labelFormatter={(v: number) => `${v} min`}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="costo"
                  name="Costo (MXN)"
                  stroke="#0f172a"
                  strokeWidth={2}
                  dot={(props: { cx: number; cy: number; payload: { color: string; tag: string } }) => (
                    <circle
                      key={props.payload.tag}
                      cx={props.cx}
                      cy={props.cy}
                      r={props.payload.tag === activeTag ? 9 : 6}
                      fill={props.payload.color}
                      stroke="#0f172a"
                      strokeWidth={props.payload.tag === activeTag ? 2 : 1}
                    />
                  )}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">
            Abajo-derecha = más barata y lenta; arriba-izquierda = más rápida y cara. Toca un punto para
            activarla en el mapa.
          </p>
        </div>
      </div>
    </section>
  );
}
