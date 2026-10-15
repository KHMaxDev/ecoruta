export const TAG_COLORS: Record<string, string> = {
  preferencia_usuario: "#2563eb",
  punto_de_codo_equilibrado: "#16a34a",
  minimo_costo: "#7c3aed",
  minimo_tiempo: "#dc2626"
};

export const TAG_LABELS: Record<string, string> = {
  preferencia_usuario: "Tu preferencia",
  punto_de_codo_equilibrado: "Equilibrada",
  minimo_costo: "Más barata",
  minimo_tiempo: "Más rápida"
};

const FALLBACK = ["#0891b2", "#ea580c", "#0d9488", "#9333ea", "#65a30d", "#e11d48"];

export function colorFor(tag: string, index = 0): string {
  return TAG_COLORS[tag] ?? FALLBACK[index % FALLBACK.length];
}

export function labelFor(tag: string, index = 0): string {
  if (TAG_LABELS[tag]) {
    return TAG_LABELS[tag];
  }
  const match = /^pareto_(\d+)$/.exec(tag);
  return match ? `Alternativa ${Number(match[1]) + 1}` : `Ruta ${index + 1}`;
}

export function hexToRgb(hex: string): [number, number, number] {
  const value = hex.replace("#", "");
  return [
    parseInt(value.slice(0, 2), 16),
    parseInt(value.slice(2, 4), 16),
    parseInt(value.slice(4, 6), 16)
  ];
}
