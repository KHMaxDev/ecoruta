import type { ReactElement, ReactNode } from "react";

interface PageShellProps {
  title: string;
  subtitle: string;
  children: ReactNode;
}

export function PageShell({ title, subtitle, children }: PageShellProps): ReactElement {
  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div>
        <h2 className="text-2xl font-bold text-ecoruta-ink">{title}</h2>
        <p className="text-sm text-slate-500">{subtitle}</p>
      </div>
      <div className="space-y-4 text-sm leading-relaxed text-slate-700">{children}</div>
    </div>
  );
}

export function Card({ title, children }: { title: string; children: ReactNode }): ReactElement {
  return (
    <section className="rounded-xl bg-white p-5 shadow">
      <h3 className="mb-2 text-base font-semibold text-ecoruta-green">{title}</h3>
      <div className="space-y-2">{children}</div>
    </section>
  );
}
