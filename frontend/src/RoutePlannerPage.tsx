import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactElement } from "react";
import { fetchWeather, listVehicleProfiles, optimizeRoute } from "./api";
import ChartsSection from "./components/ChartsSection";
import ComparisonSection from "./components/ComparisonSection";
import DataAuditBadge from "./components/DataAuditBadge";
import MapViewer from "./components/MapViewer";
import TripConfigCard from "./components/TripConfigCard";
import WeatherWindow from "./components/WeatherWindow";
import type { OptimizeResponse, RouteRequest, VehicleProfile, WeatherOut } from "./types";

const INITIAL_REQUEST: RouteRequest = {
  origin_lat: 19.4326,
  origin_lon: -99.1332,
  dest_lat: 19.0414,
  dest_lon: -98.2063,
  departure_hour: 8,
  day_type: "weekday",
  vehicle_code: "sedan_compacto",
  cargo_mass_kg: 150,
  ac_enabled: true,
  willingness_to_pay_mxn_per_min: 2.5,
  max_budget_mxn: null,
  max_duration_min: null,
  use_robust_p90: false
};

export default function RoutePlannerPage(): ReactElement {
  const [profiles, setProfiles] = useState<VehicleProfile[]>([]);
  const [request, setRequest] = useState<RouteRequest>(INITIAL_REQUEST);
  const [response, setResponse] = useState<OptimizeResponse | null>(null);
  const [activeTag, setActiveTag] = useState<string>("punto_de_codo_equilibrado");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [pickingMode, setPickingMode] = useState<"origin" | "dest" | null>(null);
  const [configCollapsed, setConfigCollapsed] = useState<boolean>(false);
  const [weather, setWeather] = useState<WeatherOut | null>(null);
  const [weatherLoading, setWeatherLoading] = useState<boolean>(false);
  const [weatherError, setWeatherError] = useState<string | null>(null);
  const [weatherOpen, setWeatherOpen] = useState<boolean>(true);
  const resultsRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    listVehicleProfiles()
      .then(setProfiles)
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setWeatherLoading(true);
    setWeatherError(null);
    fetchWeather(request.origin_lat, request.origin_lon)
      .then((w) => {
        if (!cancelled) {
          setWeather(w);
        }
      })
      .catch((e: Error) => {
        if (!cancelled) {
          setWeatherError(e.message);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setWeatherLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [request.origin_lat, request.origin_lon]);

  const onPick = useCallback(
    (lon: number, lat: number): void => {
      setRequest((prev) => {
        if (pickingMode === "origin") {
          return { ...prev, origin_lat: lat, origin_lon: lon };
        }
        if (pickingMode === "dest") {
          return { ...prev, dest_lat: lat, dest_lon: lon };
        }
        return prev;
      });
      setPickingMode(null);
    },
    [pickingMode]
  );

  const onSubmit = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const data = await optimizeRoute(request);
      setResponse(data);
      setActiveTag(data.optimization_result.recommended_knee.recommendation_tag);
      setConfigCollapsed(true);
      window.setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 150);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
      setConfigCollapsed(false);
    } finally {
      setLoading(false);
    }
  }, [request]);

  return (
    <div className="min-h-0 flex-1 overflow-y-auto bg-slate-100 p-4">
      <div className="flex gap-4" style={{ height: "62vh", minHeight: 420 }}>
        <aside className="w-96 shrink-0 space-y-4 overflow-y-auto">
          <TripConfigCard
            profiles={profiles}
            value={request}
            onChange={setRequest}
            onSubmit={onSubmit}
            loading={loading}
            collapsed={configCollapsed}
            onToggleCollapse={() => setConfigCollapsed((v) => !v)}
            pickingMode={pickingMode}
            onStartPick={setPickingMode}
          />

          {error && (
            <div className="rounded-lg bg-red-100 p-3 text-sm text-red-800">{error}</div>
          )}

          {response && <DataAuditBadge audit={response.data_provenance_audit} />}
        </aside>

        <main className="relative min-h-0 flex-1 overflow-hidden rounded-xl bg-white shadow">
          <MapViewer
            result={response?.optimization_result ?? null}
            activeTag={activeTag}
            origin={[request.origin_lon, request.origin_lat]}
            destination={[request.dest_lon, request.dest_lat]}
            pickingMode={pickingMode}
            onPick={onPick}
          />
          {weatherOpen ? (
            <WeatherWindow
              weather={weather}
              loading={weatherLoading}
              error={weatherError}
              onClose={() => setWeatherOpen(false)}
            />
          ) : (
            <button
              type="button"
              onClick={() => setWeatherOpen(true)}
              className="absolute left-3 top-3 z-20 rounded-lg bg-white/95 px-3 py-1.5 text-sm font-medium text-ecoruta-green shadow backdrop-blur hover:bg-white"
            >
              ☁ Ver clima
            </button>
          )}
        </main>
      </div>

      <div ref={resultsRef} className="mt-6 scroll-mt-4 space-y-6">
        {response ? (
          <>
            {response.comparison && <ComparisonSection comparison={response.comparison} />}
            <ChartsSection
              result={response.optimization_result}
              activeTag={activeTag}
              onSelect={setActiveTag}
            />
          </>
        ) : (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">
            Configura tu viaje y presiona <b>Optimizar ruta</b> para ver el resumen y las gráficas
            del frente de Pareto.
          </div>
        )}
      </div>
    </div>
  );
}
