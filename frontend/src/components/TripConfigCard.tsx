import type { ReactElement } from "react";
import { PILOT_CITIES } from "../cities";
import Field from "./Field";
import type { RouteRequest, VehicleProfile } from "../types";

interface TripConfigCardProps {
  profiles: VehicleProfile[];
  value: RouteRequest;
  onChange: (next: RouteRequest) => void;
  onSubmit: () => void;
  loading: boolean;
  collapsed: boolean;
  onToggleCollapse: () => void;
  pickingMode: "origin" | "dest" | null;
  onStartPick: (mode: "origin" | "dest" | null) => void;
}

function nearestCityName(lat: number, lon: number): string {
  let best = PILOT_CITIES[0];
  let bestDist = Number.POSITIVE_INFINITY;
  for (const c of PILOT_CITIES) {
    const d = (c.lat - lat) ** 2 + (c.lon - lon) ** 2;
    if (d < bestDist) {
      bestDist = d;
      best = c;
    }
  }
  return bestDist < 0.05 ? best.name : "Punto personalizado";
}

const STEP_LABELS = ["Ruta", "Vehículo", "Condiciones", "Preferencias"];

export default function TripConfigCard({
  profiles,
  value,
  onChange,
  onSubmit,
  loading,
  collapsed,
  onToggleCollapse,
  pickingMode,
  onStartPick
}: TripConfigCardProps): ReactElement {
  const update = <K extends keyof RouteRequest>(key: K, next: RouteRequest[K]): void => {
    onChange({ ...value, [key]: next });
  };

  const numberInput = (raw: string): number => (raw === "" ? 0 : Number(raw));

  const selectedProfile = profiles.find((p) => p.code === value.vehicle_code);

  const pointPicker = (which: "origin" | "dest", label: string, help: string): ReactElement => {
    const lat = which === "origin" ? value.origin_lat : value.dest_lat;
    const lon = which === "origin" ? value.origin_lon : value.dest_lon;
    const active = pickingMode === which;
    const city = nearestCityName(lat, lon);
    return (
      <Field label={label} help={help}>
        <div className="flex gap-2">
          <select
            className="w-full rounded border px-2 py-1 text-sm"
            value={PILOT_CITIES.some((c) => c.name === city) ? city : ""}
            onChange={(e) => {
              const found = PILOT_CITIES.find((c) => c.name === e.target.value);
              if (found) {
                if (which === "origin") {
                  onChange({ ...value, origin_lat: found.lat, origin_lon: found.lon });
                } else {
                  onChange({ ...value, dest_lat: found.lat, dest_lon: found.lon });
                }
              }
            }}
          >
            <option value="">{city}</option>
            {PILOT_CITIES.map((c) => (
              <option key={c.name} value={c.name}>
                {c.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => onStartPick(active ? null : which)}
            title="Fija este punto haciendo clic sobre el mapa"
            className={`shrink-0 rounded px-2 py-1 text-xs font-medium ${
              active ? "bg-ecoruta-amber text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            {active ? "Clic en mapa…" : "Mapa"}
          </button>
        </div>
        <span className="mt-1 block text-xs text-slate-500">
          {lat.toFixed(4)}, {lon.toFixed(4)}
        </span>
      </Field>
    );
  };

  if (collapsed) {
    return (
      <div className="rounded-xl bg-white p-4 shadow">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Viaje configurado</p>
            <p className="font-semibold text-ecoruta-green">
              {nearestCityName(value.origin_lat, value.origin_lon)} →{" "}
              {nearestCityName(value.dest_lat, value.dest_lon)}
            </p>
            <p className="text-xs text-slate-500">
              {selectedProfile?.name ?? value.vehicle_code} · salida {value.departure_hour}:00 ·{" "}
              {value.day_type === "weekday" ? "entre semana" : "fin de semana"}
            </p>
          </div>
          <button
            type="button"
            onClick={onToggleCollapse}
            className="rounded-lg border border-ecoruta-green px-3 py-1.5 text-sm font-medium text-ecoruta-green hover:bg-ecoruta-green hover:text-white"
          >
            Editar
          </button>
        </div>
      </div>
    );
  }

  return (
    <form
      className="space-y-4 rounded-xl bg-white p-4 shadow"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-ecoruta-green">Configuración del viaje</h2>
        <button
          type="button"
          onClick={onToggleCollapse}
          className="text-xs text-slate-500 hover:text-slate-800"
        >
          Colapsar ▴
        </button>
      </div>

      <ol className="flex flex-wrap gap-1 text-[11px]">
        {STEP_LABELS.map((s, i) => (
          <li key={s} className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">
            <span className="font-semibold text-ecoruta-green">{i + 1}.</span> {s}
          </li>
        ))}
      </ol>

      <div className="space-y-3">
        {pointPicker(
          "origin",
          "Origen",
          "Punto de partida. Elige una ciudad o presiona 'Mapa' y haz clic sobre el mapa."
        )}
        {pointPicker(
          "dest",
          "Destino",
          "Punto de llegada. Elige una ciudad o presiona 'Mapa' y haz clic sobre el mapa."
        )}
      </div>

      <Field label="Vehículo" help="Perfil físico usado por el modelo de consumo: masa, aerodinámica, ejes y combustible.">
        <select
          className="w-full rounded border px-2 py-1 text-sm"
          value={value.vehicle_code}
          onChange={(e) => update("vehicle_code", e.target.value)}
        >
          {profiles.length === 0 && <option value="">Cargando…</option>}
          {profiles.map((p) => (
            <option key={p.code} value={p.code}>
              {p.name} ({p.fuel_type})
            </option>
          ))}
        </select>
      </Field>

      {selectedProfile && (
        <div className="rounded-lg bg-slate-50 p-2 text-xs text-slate-600">
          Combustible <b>{selectedProfile.fuel_type}</b> · {selectedProfile.num_axles} ejes ·{" "}
          {selectedProfile.empty_mass_kg.toFixed(0)} kg ·{" "}
          {selectedProfile.height_m.toFixed(2)} m de alto
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <Field label="Hora de salida" help="Hora del día (0-23). El motor usa el perfil de velocidad de esa hora.">
          <input
            type="number"
            min={0}
            max={23}
            className="w-full rounded border px-2 py-1"
            value={value.departure_hour}
            onChange={(e) => update("departure_hour", numberInput(e.target.value))}
          />
        </Field>
        <Field label="Carga (kg)" help="Masa adicional transportada. Incrementa el consumo por inercia y rodadura.">
          <input
            type="number"
            min={0}
            className="w-full rounded border px-2 py-1"
            value={value.cargo_mass_kg}
            onChange={(e) => update("cargo_mass_kg", numberInput(e.target.value))}
          />
        </Field>
        <Field label="Tipo de día" help="Entre semana usa un perfil de tráfico; fin de semana otro más libre.">
          <select
            className="w-full rounded border px-2 py-1"
            value={value.day_type}
            onChange={(e) => update("day_type", e.target.value as RouteRequest["day_type"])}
          >
            <option value="weekday">Entre semana</option>
            <option value="weekend">Fin de semana</option>
          </select>
        </Field>
        <Field
          label="Valor del tiempo"
          help="Cuánto vale 1 minuto para ti (MXN/min). Se usa para elegir tu mejor compromiso costo/tiempo."
        >
          <input
            type="number"
            step="0.1"
            min={0}
            className="w-full rounded border px-2 py-1"
            value={value.willingness_to_pay_mxn_per_min}
            onChange={(e) => update("willingness_to_pay_mxn_per_min", numberInput(e.target.value))}
          />
        </Field>
      </div>

      <div className="flex flex-wrap gap-4 text-sm">
        <label className="flex items-center gap-2" title="El aire acondicionado añade potencia auxiliar constante.">
          <input
            type="checkbox"
            checked={value.ac_enabled}
            onChange={(e) => update("ac_enabled", e.target.checked)}
          />
          Aire acondicionado
        </label>
        <label
          className="flex items-center gap-2"
          title="Evalúa tiempos en el percentil P90 de congestión (escenario robusto/peor caso)."
        >
          <input
            type="checkbox"
            checked={value.use_robust_p90}
            onChange={(e) => update("use_robust_p90", e.target.checked)}
          />
          Modo robusto (P90)
        </label>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-lg bg-ecoruta-green px-4 py-2 font-medium text-white transition hover:opacity-90 disabled:opacity-50"
      >
        {loading ? "Calculando frente de Pareto…" : "Optimizar ruta"}
      </button>
    </form>
  );
}
