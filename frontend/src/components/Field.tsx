import type { ReactElement, ReactNode } from "react";

interface FieldProps {
  label: string;
  help: string;
  children: ReactNode;
}

/**
 * Campo de formulario con etiqueta y ayuda contextual (tooltip al pasar el ratón).
 */
export default function Field({ label, help, children }: FieldProps): ReactElement {
  return (
    <label className="block text-sm">
      <span className="mb-1 flex items-center gap-1.5">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="group relative inline-flex">
          <span
            className="flex h-4 w-4 cursor-help items-center justify-center rounded-full bg-slate-200 text-[10px] font-bold text-slate-600"
            aria-label={help}
          >
            ?
          </span>
          <span
            role="tooltip"
            className="pointer-events-none absolute left-1/2 top-5 z-30 hidden w-56 -translate-x-1/2 rounded-lg bg-slate-900 px-3 py-2 text-xs font-normal text-white shadow-lg group-hover:block"
          >
            {help}
          </span>
        </span>
      </span>
      {children}
    </label>
  );
}
