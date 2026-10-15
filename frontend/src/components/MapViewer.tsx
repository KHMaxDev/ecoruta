import { useEffect, useRef } from "react";
import type { ReactElement } from "react";
import { MapboxOverlay } from "@deck.gl/mapbox";
import { PathLayer } from "@deck.gl/layers";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { colorFor, hexToRgb } from "../palette";
import type { OptimizationResult, RoutePoint } from "../types";

// Estilo vectorial gratuito con calles, carreteras y nombres (sin API key).
const BASE_STYLE = "https://tiles.openfreemap.org/styles/liberty";

function routeColor(route: RoutePoint, index: number): [number, number, number] {
  return hexToRgb(colorFor(route.recommendation_tag, index));
}

type LngLat = [number, number];

interface MapViewerProps {
  result: OptimizationResult | null;
  activeTag: string;
  origin: LngLat;
  destination: LngLat;
  pickingMode: "origin" | "dest" | null;
  onPick: (lon: number, lat: number) => void;
}

export default function MapViewer({
  result,
  activeTag,
  origin,
  destination,
  pickingMode,
  onPick
}: MapViewerProps): ReactElement {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const originMarkerRef = useRef<maplibregl.Marker | null>(null);
  const destMarkerRef = useRef<maplibregl.Marker | null>(null);
  const pickRef = useRef<{ mode: "origin" | "dest" | null; onPick: (lon: number, lat: number) => void }>({
    mode: pickingMode,
    onPick
  });

  useEffect(() => {
    pickRef.current = { mode: pickingMode, onPick };
  }, [pickingMode, onPick]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) {
      return;
    }
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASE_STYLE,
      center: [-99.1332, 19.4326],
      zoom: 8
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");

    const overlay = new MapboxOverlay({ interleaved: true, layers: [] });
    map.addControl(overlay);

    map.on("click", (e: maplibregl.MapMouseEvent) => {
      const { mode, onPick: handler } = pickRef.current;
      if (mode) {
        handler(e.lngLat.lng, e.lngLat.lat);
      }
    });

    originMarkerRef.current = new maplibregl.Marker({ color: "#16a34a" });
    destMarkerRef.current = new maplibregl.Marker({ color: "#dc2626" });

    mapRef.current = map;
    overlayRef.current = overlay;

    return () => {
      map.remove();
      mapRef.current = null;
      overlayRef.current = null;
      originMarkerRef.current = null;
      destMarkerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }
    originMarkerRef.current?.setLngLat(origin).addTo(map);
    destMarkerRef.current?.setLngLat(destination).addTo(map);
  }, [origin, destination]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }
    map.getCanvas().style.cursor = pickingMode ? "crosshair" : "";
  }, [pickingMode]);

  useEffect(() => {
    const overlay = overlayRef.current;
    if (!overlay || !result) {
      return;
    }
    const routes = result.pareto_frontier;
    const inactive = routes
      .map((r, i) => ({ route: r, color: routeColor(r, i) }))
      .filter((d) => d.route.recommendation_tag !== activeTag)
      .map((d) => ({ path: d.route.coordinates, color: d.color }));
    const activeEntry = routes
      .map((r, i) => ({ route: r, color: routeColor(r, i) }))
      .find((d) => d.route.recommendation_tag === activeTag);

    const layers: PathLayer[] = [
      new PathLayer({
        id: "ecoruta-pareto-contexto",
        data: inactive,
        pickable: false,
        widthUnits: "pixels",
        getWidth: 3,
        getColor: (d: { color: [number, number, number] }) => d.color,
        widthMinPixels: 2,
        opacity: 0.75
      })
    ];
    if (activeEntry) {
      layers.push(
        new PathLayer({
          id: "ecoruta-pareto-activa",
          data: [{ path: activeEntry.route.coordinates, color: activeEntry.color }],
          pickable: false,
          widthUnits: "pixels",
          getWidth: 7,
          getColor: (d: { color: [number, number, number] }) => d.color,
          widthMinPixels: 4
        })
      );
    }
    overlay.setProps({ layers });
  }, [result, activeTag]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !result) {
      return;
    }
    const routes = result.pareto_frontier;
    const active = routes.find((r) => r.recommendation_tag === activeTag) ?? routes[0];
    if (active && active.coordinates.length > 0) {
      const bounds = active.coordinates.reduce(
        (acc, coord) => acc.extend(coord),
        new maplibregl.LngLatBounds(active.coordinates[0], active.coordinates[0])
      );
      map.fitBounds(bounds, { padding: 80, duration: 700 });
    }
  }, [result, activeTag]);

  return <div ref={containerRef} className="h-full w-full" />;
}
