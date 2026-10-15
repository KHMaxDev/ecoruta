import type { OptimizeResponse, RouteRequest, VehicleProfile, WeatherOut } from "./types";

const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8010";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Error ${res.status}: ${detail}`);
  }
  return (await res.json()) as T;
}

export const listVehicleProfiles = (): Promise<VehicleProfile[]> =>
  request<VehicleProfile[]>("/api/v1/vehicles/profiles");

export const optimizeRoute = (body: RouteRequest): Promise<OptimizeResponse> =>
  request<OptimizeResponse>("/api/v1/routes/optimize", {
    method: "POST",
    body: JSON.stringify(body)
  });

export const fetchWeather = (lat: number, lon: number): Promise<WeatherOut> =>
  request<WeatherOut>(`/api/v1/weather?lat=${lat}&lon=${lon}`);
