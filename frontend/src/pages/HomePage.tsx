import { Fragment, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchDashboard } from "../api/client";
import { EmbeddedInsight } from "../components/copilot/EmbeddedInsight";
import { useCopilot } from "../context/CopilotContext";
import { t } from "../i18n";
import type { ChatMessage, DashboardSummary } from "../types/api";
import {
  ActionCell,
  DataTable,
  KpiTableRow,
  ListPanel,
  PageHeader,
  severityStyle,
} from "../components/shared/UiBits";

const EMPTY_KPI = {
  otd_rate: 0,
  otd_target: 0,
  defect_rate: 0,
  defect_target: 0,
  lead_time_days: 0,
  lead_time_target: 0,
};

function alertSupplierLabel(message: string): string {
  return message.split("·")[0]?.trim() ?? "";
}

function buildAlertQuestion(
  supplierId: string,
  alertMessage: string,
  question: string,
): string {
  const name = alertSupplierLabel(alertMessage);
  const who = name ? `${supplierId} (${name})` : supplierId;
  return `For supplier ${who}, alert: ${alertMessage}\n\n${question}`;
}

export function HomePage() {
  const { lang, ask, setPageContext } = useCopilot();
  const L = t(lang).home;
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedAlertId, setExpandedAlertId] = useState<string | null>(null);
  const [alertInsights, setAlertInsights] = useState<Record<string, ChatMessage>>({});
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    fetchDashboard()
      .then((res) => setData(res))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const analyzeAlert = async (
    supplierId: string,
    alertMessage: string,
    question: string,
  ) => {
    const supplierName = alertSupplierLabel(alertMessage);
    setExpandedAlertId(supplierId);
    setPageContext((prev) => ({
      ...prev,
      page: "home",
      supplierId,
      supplierName,
    }));

    const cached = alertInsights[supplierId];
    if (cached && !cached.clarificationRequired) return;

    const explicitQuestion = buildAlertQuestion(supplierId, alertMessage, question);
    setAnalyzingId(supplierId);
    try {
      const msg = await ask(explicitQuestion, {
        fresh: true,
        contextOverride: { page: "home", supplierId, supplierName },
      });
      if (msg) {
        setAlertInsights((prev) => ({ ...prev, [supplierId]: msg }));
      }
    } finally {
      setAnalyzingId(null);
    }
  };

  const replyToAlertClarification = async (supplierId: string, reply: string) => {
    setAnalyzingId(supplierId);
    try {
      const msg = await ask(reply);
      if (msg) {
        setAlertInsights((prev) => ({ ...prev, [supplierId]: msg }));
      }
    } finally {
      setAnalyzingId(null);
    }
  };

  if (loading) return <p className="page-meta">{t(lang).common.loading}</p>;

  if (error || !data) {
    return (
      <div>
        <PageHeader title={t(lang).common.error} meta={error ?? undefined} />
        <div className="btn-bar">
          <button type="button" className="btn btn-primary" onClick={load}>
            {t(lang).common.retry}
          </button>
        </div>
      </div>
    );
  }

  const alerts = data.risk_alerts ?? [];
  const kpi = { ...EMPTY_KPI, ...(data.yarn_kpi_snapshot ?? {}) };

  const summaryRows = [
    { label: "Active suppliers", value: data.active_suppliers, to: "/suppliers" },
    {
      label: "At risk",
      value: data.at_risk_suppliers,
      to: "/suppliers?risk=high",
      warn: true,
    },
    {
      label: "Reviews due",
      value: data.reviews_due_this_month,
      to: "/review",
      warn: true,
    },
    {
      label: "Open qualifications",
      value: data.open_qualifications,
      to: "/qualification",
    },
  ];

  return (
    <div>
      <PageHeader title={data.greeting} meta={data.period_label} />

      <section className="page-section">
        <div className="page-section-head">
          <h2 className="panel-title">Overview</h2>
        </div>
        <ListPanel>
          <DataTable>
            <thead>
              <tr>
                <th>Metric</th>
                <th>Count</th>
                <th className="col-actions">Action</th>
              </tr>
            </thead>
            <tbody>
              {summaryRows.map((row) => (
                <tr key={row.label}>
                  <td>{row.label}</td>
                  <td
                    className="tabular-nums font-medium"
                    style={{ color: row.warn ? "var(--warn)" : "var(--ink)" }}
                  >
                    {row.value}
                  </td>
                  <ActionCell>
                    <Link to={row.to} className="btn btn-sm btn-ghost">
                      View
                    </Link>
                  </ActionCell>
                </tr>
              ))}
            </tbody>
          </DataTable>
        </ListPanel>
      </section>

      <section className="page-section">
        <div className="page-section-head">
          <h2 className="panel-title">{L.riskAlerts}</h2>
        </div>
        <ListPanel>
          <DataTable>
            <thead>
              <tr>
                <th>Supplier</th>
                <th>Alert</th>
                <th>Severity</th>
                <th className="col-actions">Action</th>
              </tr>
            </thead>
            <tbody>
              {alerts.length === 0 ? (
                <tr>
                  <td colSpan={4} style={{ color: "var(--muted)" }}>
                    No open alerts
                  </td>
                </tr>
              ) : (
                alerts.map((a) => (
                  <Fragment key={a.supplier_id}>
                    <tr
                      className={
                        expandedAlertId === a.supplier_id ? "row-selected" : undefined
                      }
                    >
                      <td className="tabular-nums">{a.supplier_id}</td>
                      <td style={{ color: "var(--ink-soft)" }}>{a.message}</td>
                      <td>
                        <span
                          className="text-xs font-medium uppercase"
                          style={severityStyle(a.severity)}
                        >
                          {a.severity}
                        </span>
                      </td>
                      <ActionCell>
                        <Link
                          to={`/suppliers/${a.supplier_id}`}
                          className="btn btn-sm btn-ghost"
                        >
                          {L.viewDetails}
                        </Link>
                        <button
                          type="button"
                          className="btn btn-sm btn-secondary"
                          disabled={analyzingId === a.supplier_id}
                          onClick={() => {
                            void analyzeAlert(a.supplier_id, a.message, a.ask_ai_question);
                          }}
                        >
                          {analyzingId === a.supplier_id
                            ? t(lang).common.loading
                            : L.analyze}
                        </button>
                      </ActionCell>
                    </tr>
                    {expandedAlertId === a.supplier_id ? (
                      <tr className="row-insight">
                        <td colSpan={4}>
                          <EmbeddedInsight
                            variant="inline"
                            title={`${a.supplier_id} · ${alertSupplierLabel(a.message)}`}
                            loading={analyzingId === a.supplier_id}
                            message={alertInsights[a.supplier_id] ?? null}
                            lang={lang}
                            showDebug={false}
                            onClarifyReply={(reply) => {
                              void replyToAlertClarification(a.supplier_id, reply);
                            }}
                          />
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                ))
              )}
            </tbody>
          </DataTable>
        </ListPanel>
      </section>

      <section className="page-section">
        <div className="page-section-head">
          <h2 className="panel-title">{L.kpiSnapshot}</h2>
        </div>
        <ListPanel>
          <DataTable>
            <thead>
              <tr>
                <th>Metric</th>
                <th>Actual</th>
                <th>Target</th>
                <th>Progress</th>
              </tr>
            </thead>
            <tbody>
              <KpiTableRow label="OTD rate" value={kpi.otd_rate} target={kpi.otd_target} />
              <KpiTableRow
                label="Defect rate"
                value={kpi.defect_rate}
                target={kpi.defect_target}
                invert
              />
              <KpiTableRow
                label="Lead time"
                value={kpi.lead_time_days}
                target={kpi.lead_time_target}
                invert
                unit="d"
              />
            </tbody>
          </DataTable>
        </ListPanel>
      </section>
    </div>
  );
}
