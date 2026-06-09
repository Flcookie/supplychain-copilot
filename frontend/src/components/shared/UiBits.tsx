import type { CSSProperties, ReactNode } from "react";

function pct(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export function PageHeader({ title, meta }: { title: string; meta?: string }) {
  return (
    <header className="mb-6">
      <h1 className="page-title">{title}</h1>
      {meta ? <p className="page-meta">{meta}</p> : null}
    </header>
  );
}

export function ListPanel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={`panel overflow-x-auto ${className}`}>{children}</div>;
}

export function DataTable({ children }: { children: ReactNode }) {
  return <table className="data-table">{children}</table>;
}

export function ActionCell({ children }: { children: ReactNode }) {
  return (
    <td className="col-actions">
      <div className="actions-cell">{children}</div>
    </td>
  );
}

export function ButtonBar({ children }: { children: ReactNode }) {
  return <div className="btn-bar">{children}</div>;
}

export function KpiTableRow({
  label,
  value,
  target,
  invert,
  unit = "%",
}: {
  label: string;
  value: number;
  target: number;
  invert?: boolean;
  unit?: string;
}) {
  const good = invert ? value <= target : value >= target;
  const ratio = invert
    ? Math.min(1, target / Math.max(value, 0.0001))
    : Math.min(1, value / target);
  const pctWidth = Math.max(8, ratio * 100);
  const valueStr = unit === "%" ? pct(value) : `${value.toFixed(1)}d`;
  const targetStr = unit === "%" ? pct(target) : `${target.toFixed(1)}d`;

  return (
    <tr>
      <td className="font-medium">{label}</td>
      <td className="tabular-nums">{valueStr}</td>
      <td className="tabular-nums" style={{ color: "var(--muted)" }}>
        {targetStr}
      </td>
      <td style={{ minWidth: "8rem" }}>
        <div className="relative h-1.5 overflow-hidden" style={{ background: "var(--line)" }}>
          <div
            className="h-1.5"
            style={{
              width: `${pctWidth}%`,
              background: good ? "var(--sage)" : "var(--danger)",
            }}
          />
        </div>
      </td>
    </tr>
  );
}

export function RiskBadge({ level }: { level: string }) {
  const config: Record<string, { color: string; bg: string; label: string }> = {
    high: { color: "var(--danger)", bg: "#f5e8e8", label: "High" },
    medium: { color: "var(--warn)", bg: "#f5efe3", label: "Medium" },
    low: { color: "var(--sage)", bg: "#ecf0ea", label: "Low" },
  };
  const c = config[level] || { color: "var(--muted)", bg: "var(--paper)", label: level };
  return (
    <span
      className="inline-block px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide"
      style={{ color: c.color, background: c.bg }}
    >
      {c.label}
    </span>
  );
}

export function RatingBadge({ rating }: { rating: string }) {
  const letter = rating.charAt(0).toUpperCase();
  const tier =
    letter === "A"
      ? { border: "var(--sage)", hint: "Preferred" }
      : letter === "B"
        ? { border: "var(--line-strong)", hint: "Acceptable" }
        : letter === "C"
          ? { border: "var(--danger)", hint: "Review required" }
          : { border: "var(--muted)", hint: "Watch" };

  return (
    <span
      className="inline-flex h-7 min-w-7 items-center justify-center border px-1.5 font-serif text-base"
      style={{ borderColor: tier.border, color: "var(--ink)" }}
      title={tier.hint}
    >
      {rating}
    </span>
  );
}

export function CategoryBadge({ category }: { category: string }) {
  return (
    <span
      className="border px-2 py-0.5 text-[11px] uppercase tracking-wide"
      style={{ borderColor: "var(--line-strong)", color: "var(--ink-soft)" }}
    >
      {category}
    </span>
  );
}

export function StepWizard({
  steps,
  current,
}: {
  steps: { id: number; label: string }[];
  current: number;
}) {
  return (
    <ListPanel className="mb-6">
      <DataTable>
        <thead>
          <tr>
            <th>Step</th>
            <th>Stage</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {steps.map((s) => (
            <tr key={s.id}>
              <td className="tabular-nums">{String(s.id).padStart(2, "0")}</td>
              <td>{s.label}</td>
              <td style={{ color: "var(--muted)" }}>
                {current > s.id ? "Done" : current === s.id ? "In progress" : "Pending"}
              </td>
            </tr>
          ))}
        </tbody>
      </DataTable>
    </ListPanel>
  );
}

export function ReviewProgress({
  completed,
  total,
  label,
}: {
  completed: number;
  total: number;
  label: string;
}) {
  const pctDone = total ? Math.round((completed / total) * 100) : 0;
  return (
    <ListPanel className="mb-6">
      <DataTable>
        <tbody>
          <tr>
            <td className="font-medium">{label}</td>
            <td className="tabular-nums" style={{ width: "5rem" }}>
              {completed}/{total}
            </td>
            <td style={{ minWidth: "12rem" }}>
              <div className="h-1 overflow-hidden" style={{ background: "var(--line)" }}>
                <div
                  className="h-1"
                  style={{ width: `${pctDone}%`, background: "var(--ink)" }}
                />
              </div>
            </td>
          </tr>
        </tbody>
      </DataTable>
    </ListPanel>
  );
}

export function AiPrimaryButton({
  onClick,
  label,
  disabled,
}: {
  onClick: () => void;
  label: string;
  sublabel?: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="btn btn-sm btn-secondary"
    >
      {label}
    </button>
  );
}

export function OtdCell({ rate }: { rate: number }) {
  const pctVal = rate * 100;
  const color =
    pctVal < 70 ? "var(--danger)" : pctVal < 85 ? "var(--warn)" : "var(--sage)";
  return (
    <span className="tabular-nums font-medium" style={{ color }}>
      {pctVal.toFixed(1)}%
    </span>
  );
}

export function severityStyle(severity: string): CSSProperties {
  const colors: Record<string, string> = {
    high: "var(--danger)",
    medium: "var(--warn)",
    low: "var(--sage)",
  };
  return { color: colors[severity] || "var(--muted)" };
}
