import type { ReactElement } from "react";
import type { DataProvenanceAudit } from "../types";

interface DataAuditBadgeProps {
  audit: DataProvenanceAudit;
}

export default function DataAuditBadge({ audit }: DataAuditBadgeProps): ReactElement {
  return (
    <div className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900">
      <p className="mb-1 font-semibold">Auditoría de datos (procedencia)</p>
      <ul className="space-y-1">
        <li>
          <span className="font-medium">Red vial:</span> {audit.road_network_source}
        </li>
        <li>
          <span className="font-medium">Precios de combustible:</span> {audit.fuel_price_source}
        </li>
        <li>
          <span className="font-medium">Peajes:</span> {audit.toll_source}
        </li>
        <li>
          <span className="font-medium">Incertidumbre:</span> {audit.uncertainty_mode}
        </li>
        <li>
          <span className="font-medium">Calculado (UTC):</span> {audit.computed_at_utc}
        </li>
      </ul>
      <p className="mt-2 italic">{audit.safety_context_notice}</p>
    </div>
  );
}
