import { Link } from "react-router-dom";

function pct(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export function MetricCard({
  label,
  value,
  highlight,
  subtitle,
  actionHint,
  to,
  onClick,
}: {
  label: string;
  value: string | number;
  highlight?: "danger" | "warning" | "neutral";
  subtitle?: string;
  actionHint?: string;
  to?: string;
  onClick?: () => void;
}) {
  const ring =
    highlight === "danger"
      ? "border-red-300 bg-red-50 hover:border-red-400"
      : highlight === "warning"
        ? "border-orange-300 bg-orange-50 hover:border-orange-400"
        : "border-slate-200 bg-white hover:border-[#1e3a5f]/30";

  const inner = (
    <>
      <p className="text-sm font-medium text-slate-600">{label}</p>
      <p
        className={`mt-1 text-3xl font-bold ${
          highlight === "danger"
            ? "text-red-700"
            : highlight === "warning"
              ? "text-orange-700"
              : "text-[#1e3a5f]"
        }`}
      >
        {value}
      </p>
      {subtitle ? (
        <p className="mt-1 text-xs text-slate-500">{subtitle}</p>
      ) : null}
      {actionHint ? (
        <p className="mt-2 text-xs font-medium text-[#553c9a]">{actionHint} →</p>
      ) : null}
    </>
  );

  const className = `block rounded-xl border p-5 transition-shadow hover:shadow-md ${ring} ${
    to || onClick ? "cursor-pointer" : ""
  }`;

  if (to) {
    return (
      <Link to={to} className={className}>
        {inner}
      </Link>
    );
  }

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={`${className} w-full text-left`}>
        {inner}
      </button>
    );
  }

  return <div className={className}>{inner}</div>;
}

export function KpiBar({
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
  const gap = invert ? value - target : target - value;
  const good = invert ? value <= target : value >= target;
  const ratio = invert
    ? Math.min(1, target / Math.max(value, 0.0001))
    : Math.min(1, value / target);
  const pctWidth = Math.max(8, ratio * 100);

  const valueStr =
    unit === "%" && !invert
      ? pct(value)
      : unit === "%" && invert
        ? pct(value)
        : `${value.toFixed(1)}${unit === "d" ? "d" : unit}`;
  const targetStr =
    unit === "%" ? pct(target) : `${target.toFixed(1)}${unit === "d" ? "d" : unit}`;

  const gapLabel = good
    ? unit === "d"
      ? `${Math.abs(gap).toFixed(1)}d under target`
      : invert
        ? `${(Math.abs(gap) * 100).toFixed(1)} pp under target`
        : `${pct(Math.abs(gap))} above target`
    : unit === "d"
      ? `${gap.toFixed(1)}d over target`
      : invert
        ? `${(gap * 100).toFixed(1)} pp over target`
        : `${pct(Math.abs(gap))} below target`;

  return (
    <div className="mb-4 rounded-lg border border-slate-100 bg-slate-50/80 p-3">
      <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
        <div>
          <span className="font-medium text-slate-800">{label}</span>
          <span
            className={`ml-2 rounded-full px-2 py-0.5 text-xs font-semibold ${
              good
                ? "bg-green-100 text-green-800"
                : "bg-orange-100 text-orange-900"
            }`}
          >
            {good ? "On track" : "Below target"}
          </span>
        </div>
        <div className="text-right text-sm">
          <span className="font-bold text-[#1e3a5f]">{valueStr}</span>
          <span className="text-slate-500"> / target {targetStr}</span>
        </div>
      </div>
      <div className="relative h-3 overflow-hidden rounded-full bg-slate-200">
        <div
          className={`h-3 rounded-full transition-all ${good ? "bg-[#276749]" : "bg-[#e53e3e]"}`}
          style={{ width: `${pctWidth}%` }}
        />
        <div
          className="absolute top-0 h-3 w-0.5 bg-slate-600/60"
          style={{ left: `${Math.min(98, ratio * 100)}%` }}
          title="Target position"
        />
      </div>
      <p className={`mt-1.5 text-xs ${good ? "text-green-700" : "text-red-700"}`}>
        {good ? "✓ " : "⚠ "}
        {gapLabel}
      </p>
    </div>
  );
}

export function RiskBadge({ level }: { level: string }) {
  const config: Record<string, { cls: string; label: string }> = {
    high: { cls: "bg-red-100 text-red-900 ring-1 ring-red-300", label: "High risk" },
    medium: {
      cls: "bg-orange-100 text-orange-900 ring-1 ring-orange-300",
      label: "Medium risk",
    },
    low: { cls: "bg-green-100 text-green-900 ring-1 ring-green-300", label: "Low risk" },
  };
  const c = config[level] || { cls: "bg-slate-100", label: level };
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${c.cls}`}>
      {c.label}
    </span>
  );
}

export function RatingBadge({ rating }: { rating: string }) {
  const letter = rating.charAt(0).toUpperCase();
  const tier =
    letter === "A"
      ? { cls: "bg-green-100 text-green-900 ring-green-400", hint: "Preferred" }
      : letter === "B"
        ? { cls: "bg-blue-100 text-blue-900 ring-blue-300", hint: "Acceptable" }
        : letter === "C"
          ? { cls: "bg-red-100 text-red-900 ring-red-400", hint: "Review required" }
          : { cls: "bg-slate-100 text-slate-800 ring-slate-300", hint: "Watch" };

  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={`inline-flex h-8 w-8 items-center justify-center rounded-lg text-sm font-bold ring-2 ${tier.cls}`}
        title={tier.hint}
      >
        {rating}
      </span>
      <span className="text-xs text-slate-500">{tier.hint}</span>
    </span>
  );
}

export function VersionBadge({ version }: { version: string }) {
  return (
    <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-mono text-slate-600 ring-1 ring-slate-200">
      v{version.replace(/^v/i, "")}
    </span>
  );
}

export function CategoryBadge({ category }: { category: string }) {
  const colors: Record<string, string> = {
    ESG: "bg-emerald-100 text-emerald-800",
    Quality: "bg-blue-100 text-blue-800",
    Procurement: "bg-indigo-100 text-indigo-800",
    Compliance: "bg-amber-100 text-amber-900",
  };
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${colors[category] || "bg-slate-100 text-slate-700"}`}
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
    <div className="space-y-2">
      <div className="flex items-center gap-0">
        {steps.map((s, i) => (
          <div key={s.id} className="flex flex-1 items-center">
            <div className="flex flex-col items-center">
              <div
                className={`flex h-9 w-9 items-center justify-center rounded-full text-sm font-bold ${
                  current > s.id
                    ? "bg-green-600 text-white"
                    : current === s.id
                      ? "bg-[#1e3a5f] text-white ring-4 ring-[#1e3a5f]/20"
                      : "bg-slate-200 text-slate-500"
                }`}
              >
                {current > s.id ? "✓" : s.id}
              </div>
              <span
                className={`mt-1 max-w-[6rem] text-center text-xs ${
                  current === s.id ? "font-semibold text-[#1e3a5f]" : "text-slate-500"
                }`}
              >
                {s.label}
              </span>
            </div>
            {i < steps.length - 1 ? (
              <div
                className={`mx-1 mb-5 h-0.5 flex-1 ${
                  current > s.id ? "bg-green-500" : "bg-slate-200"
                }`}
              />
            ) : null}
          </div>
        ))}
      </div>
      <p className="text-sm text-slate-600">
        Step {current} of {steps.length}:{" "}
        <strong>{steps.find((s) => s.id === current)?.label}</strong>
      </p>
    </div>
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
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="mb-2 flex justify-between text-sm">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="text-slate-600">
          {completed}/{total} done ({pctDone}%)
        </span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-slate-200">
        <div
          className="h-2.5 rounded-full bg-[#1e3a5f] transition-all"
          style={{ width: `${pctDone}%` }}
        />
      </div>
    </div>
  );
}

export function AiPrimaryButton({
  onClick,
  label,
  sublabel,
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
      className="flex flex-col items-start rounded-lg bg-gradient-to-r from-[#553c9a] to-[#6b46c1] px-4 py-2.5 text-left text-white shadow-sm hover:from-[#44307a] hover:to-[#553c9a] disabled:opacity-50"
    >
      <span className="flex items-center gap-1.5 text-sm font-semibold">
        <span aria-hidden>🤖</span> {label}
      </span>
      {sublabel ? (
        <span className="mt-0.5 text-xs text-purple-100">{sublabel}</span>
      ) : null}
    </button>
  );
}

export function AskAiButton({
  onClick,
  label = "Ask AI",
  variant = "secondary",
}: {
  onClick: () => void;
  label?: string;
  variant?: "primary" | "secondary";
}) {
  if (variant === "primary") {
    return <AiPrimaryButton onClick={onClick} label={label} />;
  }
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-lg border border-[#553c9a] bg-purple-50 px-3 py-1.5 text-xs font-medium text-[#553c9a] hover:bg-purple-100"
    >
      🤖 {label}
    </button>
  );
}

export function NextStepBanner({
  title,
  description,
  actionLabel,
  onAction,
  to,
}: {
  title: string;
  description: string;
  actionLabel: string;
  onAction?: () => void;
  to?: string;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#1e3a5f]/20 bg-blue-50 px-4 py-3">
      <div>
        <p className="font-semibold text-[#1e3a5f]">{title}</p>
        <p className="text-sm text-slate-600">{description}</p>
      </div>
      {to ? (
        <Link
          to={to}
          className="shrink-0 rounded-lg bg-[#1e3a5f] px-4 py-2 text-sm font-medium text-white hover:bg-[#152a45]"
        >
          {actionLabel}
        </Link>
      ) : (
        <button
          type="button"
          onClick={onAction}
          className="shrink-0 rounded-lg bg-[#1e3a5f] px-4 py-2 text-sm font-medium text-white hover:bg-[#152a45]"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}

export function OtdCell({ rate }: { rate: number }) {
  const pctVal = rate * 100;
  const bad = pctVal < 70;
  const warn = pctVal >= 70 && pctVal < 85;
  return (
    <span
      className={`font-semibold ${
        bad ? "text-red-700" : warn ? "text-orange-700" : "text-green-800"
      }`}
    >
      {pctVal.toFixed(1)}%
      {bad ? " ⚠" : warn ? " ↓" : ""}
    </span>
  );
}

export function severityClass(severity: string): string {
  const map: Record<string, string> = {
    high: "border-l-4 border-l-red-500 bg-red-50/50",
    medium: "border-l-4 border-l-orange-500 bg-orange-50/50",
    low: "border-l-4 border-l-green-500 bg-green-50/50",
  };
  return map[severity] || "";
}
