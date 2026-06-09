import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchDashboard } from "../api/client";
import { useCopilot } from "../context/CopilotContext";
import { t } from "../i18n";
import type { DashboardSummary } from "../types/api";
import {
  AiPrimaryButton,
  KpiBar,
  MetricCard,
  NextStepBanner,
  severityClass,
} from "../components/shared/UiBits";

export function HomePage() {
  const { lang, openWithQuestion } = useCopilot();
  const L = t(lang).home;
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboard()
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <p>{t(lang).common.loading}</p>;

  const kpi = data.yarn_kpi_snapshot;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#1e3a5f]">{data.greeting}</h1>
        <p className="text-slate-500">{data.period_label}</p>
      </div>

      <NextStepBanner
        title={L.nextStepTitle}
        description={L.nextStepDesc}
        actionLabel={L.nextStepAction}
        to="/review"
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Active Suppliers"
          value={data.active_suppliers}
          subtitle={L.metricActive}
          actionHint={L.tapToView}
          to="/suppliers"
        />
        <MetricCard
          label="At-Risk Suppliers"
          value={data.at_risk_suppliers}
          highlight="danger"
          subtitle={L.metricAtRisk}
          actionHint={L.tapToView}
          to="/suppliers?risk=high"
        />
        <MetricCard
          label="Reviews Due This Month"
          value={data.reviews_due_this_month}
          highlight="warning"
          subtitle={L.metricReviews}
          actionHint={L.tapToView}
          to="/review"
        />
        <MetricCard
          label="Open Qualifications"
          value={data.open_qualifications}
          subtitle={L.metricQual}
          actionHint={L.tapToView}
          to="/qualification"
        />
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="mb-4 font-semibold">{L.riskAlerts}</h2>
        <ul className="space-y-3">
          {data.risk_alerts.map((a) => (
            <li
              key={a.supplier_id}
              className={`flex flex-wrap items-center justify-between gap-3 rounded-lg px-4 py-3 ${severityClass(a.severity)}`}
            >
              <div>
                <span
                  className={`mr-2 rounded px-1.5 py-0.5 text-xs font-bold uppercase ${
                    a.severity === "high"
                      ? "bg-red-200 text-red-900"
                      : "bg-orange-200 text-orange-900"
                  }`}
                >
                  {a.severity}
                </span>
                <span className="text-sm font-medium text-slate-800">
                  {a.message}
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                <Link
                  to={`/suppliers/${a.supplier_id}`}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-[#1e3a5f] hover:bg-slate-50"
                >
                  {L.viewDetails}
                </Link>
                <Link
                  to="/review"
                  className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-[#1e3a5f] hover:bg-slate-50"
                >
                  {L.startReview}
                </Link>
                <AiPrimaryButton
                  label={t(lang).review.aiExplain}
                  onClick={() => openWithQuestion(a.ask_ai_question)}
                />
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="mb-4 font-semibold">{L.kpiSnapshot}</h2>
        <KpiBar label="OTD Rate" value={kpi.otd_rate} target={kpi.otd_target} />
        <KpiBar
          label="Defect Rate"
          value={kpi.defect_rate}
          target={kpi.defect_target}
          invert
        />
        <KpiBar
          label="Lead Time"
          value={kpi.lead_time_days}
          target={kpi.lead_time_target}
          invert
          unit="d"
        />
      </section>
    </div>
  );
}
