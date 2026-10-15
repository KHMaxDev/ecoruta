import { useState } from "react";
import type { ReactElement } from "react";
import Navbar from "./components/Navbar";
import type { PageId } from "./components/Navbar";
import { BackgroundPage, ContextPage, DocsPage, InfoPage } from "./pages/ContentPages";
import RoutePlannerPage from "./RoutePlannerPage";

export default function App(): ReactElement {
  const [page, setPage] = useState<PageId>("rutas");

  return (
    <div className="flex h-full flex-col bg-slate-100">
      <Navbar page={page} onNavigate={setPage} />

      {page === "rutas" ? (
        <RoutePlannerPage />
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto">
          {page === "documentacion" && <DocsPage />}
          {page === "contexto" && <ContextPage />}
          {page === "antecedentes" && <BackgroundPage />}
          {page === "informacion" && <InfoPage />}
        </div>
      )}
    </div>
  );
}
