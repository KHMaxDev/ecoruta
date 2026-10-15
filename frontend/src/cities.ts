export interface City {
  name: string;
  lat: number;
  lon: number;
}

// Ciudades dentro de la región piloto (malla de demostración CDMX–Puebla–Toluca).
export const PILOT_CITIES: City[] = [
  { name: "Ciudad de México", lat: 19.4326, lon: -99.1332 },
  { name: "Puebla", lat: 19.0414, lon: -98.2063 },
  { name: "Toluca", lat: 19.2826, lon: -99.6557 },
  { name: "Cuernavaca", lat: 18.9242, lon: -99.2216 },
  { name: "Querétaro", lat: 20.5888, lon: -100.3899 },
  { name: "Pachuca", lat: 20.122, lon: -98.7322 },
  { name: "Tlaxcala", lat: 19.3138, lon: -98.24 },
  { name: "Cuautla", lat: 18.9128, lon: -98.955 }
];
