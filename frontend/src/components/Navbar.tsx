import type { ReactElement } from "react";

export type PageId = "rutas" | "documentacion" | "contexto" | "antecedentes" | "informacion";

const ITEMS: { id: PageId; label: string }[] = [
  { id: "rutas", label: "Rutas" },
  { id: "documentacion", label: "Documentación" },
  { id: "contexto", label: "Contexto" },
  { id: "antecedentes", label: "Antecedentes" },
  { id: "informacion", label: "Información general" }
];

interface NavbarProps {
  page: PageId;
  onNavigate: (page: PageId) => void;
}

export default function Navbar({ page, onNavigate }: NavbarProps): ReactElement {
  return (
    <header className="border-b bg-white shadow-sm">
      <div className="flex flex-wrap items-center gap-4 px-6 py-3">
        <div className="mr-2">
          <h1 className="text-lg font-bold leading-tight text-ecoruta-green">
            EcoRuta
          </h1>
          <p className="text-[11px] text-slate-500">
            Optimización multiobjetivo de rutas · Costo vs. Tiempo
          </p>
        </div>
        <nav className="flex flex-wrap gap-1">
          {ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                page === item.id
                  ? "bg-ecoruta-green text-white"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </div>
    </header>
  );
}
