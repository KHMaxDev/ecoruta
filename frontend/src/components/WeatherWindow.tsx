import type { ReactElement } from "react";
import type { WeatherOut } from "../types";

interface WeatherWindowProps {
  weather: WeatherOut | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
}

/** Ventana flotante (overlay) sobre el mapa con el clima de hoy en tiempo real. */
export default function WeatherWindow({
  weather,
  loading,
  error,
  onClose
}: WeatherWindowProps): ReactElement {
  return (
    <div className="absolute left-3 top-3 z-20 w-64 rounded-xl border border-slate-200 bg-white/95 p-3 shadow-xl backdrop-blur">
      <div className="mb-1 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-ecoruta-green">Clima de hoy (origen)</h3>
        <button
          type="button"
          onClick={onClose}
          className="rounded px-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          aria-label="Cerrar"
        >
          ✕
        </button>
      </div>

      {loading && <p className="text-xs text-slate-500">Consultando clima en tiempo real…</p>}
      {error && !loading && <p className="text-xs text-red-700">{error}</p>}

      {weather && !loading && (
        <div className="text-xs text-slate-700">
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-ecoruta-ink">
              {weather.temperature_c.toFixed(1)}°
            </span>
            <span className="text-slate-600">{weather.condition}</span>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-1">
            <span className="rounded bg-slate-50 px-1.5 py-1">
              Lluvia {weather.precipitation_mmh.toFixed(1)} mm/h
            </span>
            <span className="rounded bg-slate-50 px-1.5 py-1">
              Viento {weather.wind_speed_kmh.toFixed(0)} km/h
            </span>
          </div>
          <p className="mt-2 text-[10px] text-slate-400">
            {new Date(weather.observed_at).toLocaleString("es-MX")} · {weather.source} ·{" "}
            <span className={weather.status === "ok" ? "text-green-700" : "text-amber-700"}>
              {weather.status}
            </span>
          </p>
        </div>
      )}
    </div>
  );
}
