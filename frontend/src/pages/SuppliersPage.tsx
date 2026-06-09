import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchSupplier, fetchSuppliers } from "../api/client";
import { useCopilot } from "../context/CopilotContext";
import { t } from "../i18n";
import type { Supplier } from "../types/api";
import {
  ActionCell,
  ButtonBar,
  DataTable,
  ListPanel,
  OtdCell,
  PageHeader,
  RatingBadge,
  RiskBadge,
} from "../components/shared/UiBits";

export function SuppliersPage() {
  const { lang } = useCopilot();
  const L = t(lang).suppliers;
  const [searchParams] = useSearchParams();
  const [items, setItems] = useState<Supplier[]>([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [risk, setRisk] = useState(searchParams.get("risk") || "");

  useEffect(() => {
    const r = searchParams.get("risk");
    if (r) setRisk(r);
  }, [searchParams]);

  useEffect(() => {
    fetchSuppliers({
      search: search || undefined,
      category: category || undefined,
      risk_level: risk || undefined,
    })
      .then((r) => setItems(r.items))
      .catch(console.error);
  }, [search, category, risk]);

  const categories = useMemo(
    () => [...new Set(items.map((s) => s.category))],
    [items],
  );

  return (
    <div>
      <PageHeader title={L.title} />

      <div className="toolbar mb-4">
        <input
          type="search"
          placeholder={L.search}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="field field-grow"
        />
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="field"
        >
          <option value="">{L.filters.category}</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select
          value={risk}
          onChange={(e) => setRisk(e.target.value)}
          className="field"
        >
          <option value="">{L.filters.risk}</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      <ListPanel>
        <DataTable>
          <thead>
            <tr>
              <th>Supplier</th>
              <th>Category</th>
              <th>Rating</th>
              <th>OTD</th>
              <th>Risk</th>
              <th>Status</th>
              <th className="col-actions">Action</th>
            </tr>
          </thead>
          <tbody>
            {items.map((s) => (
              <tr key={s.id}>
                <td>
                  <div className="font-medium">{s.name}</div>
                  <div className="text-xs tabular-nums" style={{ color: "var(--muted)" }}>
                    {s.id}
                  </div>
                </td>
                <td style={{ color: "var(--ink-soft)" }}>{s.category}</td>
                <td>
                  <RatingBadge rating={s.rating} />
                </td>
                <td>
                  <OtdCell rate={s.otd_rate} />
                </td>
                <td>
                  <RiskBadge level={s.risk_level} />
                </td>
                <td style={{ color: "var(--muted)" }}>{s.status}</td>
                <ActionCell>
                  <Link to={`/suppliers/${s.id}`} className="btn btn-sm btn-primary">
                    {L.details}
                  </Link>
                </ActionCell>
              </tr>
            ))}
          </tbody>
        </DataTable>
      </ListPanel>
    </div>
  );
}

export function SupplierDetailPage({ supplierId }: { supplierId: string }) {
  const { lang, setPageContext, openWithQuestion } = useCopilot();
  const L = t(lang).suppliers;
  const [supplier, setSupplier] = useState<Supplier | null>(null);

  useEffect(() => {
    fetchSupplier(supplierId).then(setSupplier);
  }, [supplierId]);

  useEffect(() => {
    if (!supplier) return;
    setPageContext((prev) => ({
      ...prev,
      page: "supplier-detail",
      supplierId: supplier.id,
      supplierName: supplier.name,
    }));
  }, [supplier, setPageContext]);

  if (!supplier) return <p className="page-meta">{t(lang).common.loading}</p>;

  const trend = supplier.kpi_trend || {};
  const chartData = (trend.months || []).map((m, i) => ({
    month: m,
    otd: ((trend.otd || [])[i] ?? 0) * 100,
    defect: ((trend.defect || [])[i] ?? 0) * 100,
  }));

  return (
    <div>
      <Link to="/suppliers" className="link mb-4 inline-block text-sm">
        ← {L.back}
      </Link>

      <PageHeader
        title={supplier.name}
        meta={`${supplier.id} · ${supplier.category} · ${supplier.country}`}
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <RatingBadge rating={supplier.rating} />
        <RiskBadge level={supplier.risk_level} />
      </div>

      <section className="page-section">
        <div className="page-section-head">
          <h2 className="panel-title">Profile</h2>
        </div>
        <ListPanel>
          <DataTable>
            <tbody>
              <tr>
                <td style={{ color: "var(--muted)", width: "12rem" }}>Contract expiry</td>
                <td>{supplier.contract_expiry}</td>
              </tr>
              <tr>
                <td style={{ color: "var(--muted)" }}>Last review</td>
                <td>{supplier.last_review}</td>
              </tr>
              <tr>
                <td style={{ color: "var(--muted)" }}>Status</td>
                <td>{supplier.status}</td>
              </tr>
            </tbody>
          </DataTable>
        </ListPanel>
      </section>

      <section className="page-section">
        <div className="page-section-head">
          <h2 className="panel-title">KPI trend</h2>
        </div>
        <ListPanel className="panel-pad">
          {chartData.length ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData}>
                <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" />
                <XAxis dataKey="month" tick={{ fill: "var(--muted)", fontSize: 12 }} />
                <YAxis yAxisId="left" tick={{ fill: "var(--muted)", fontSize: 12 }} />
                <YAxis yAxisId="right" orientation="right" tick={{ fill: "var(--muted)", fontSize: 12 }} />
                <Tooltip
                  contentStyle={{
                    background: "var(--surface)",
                    border: "1px solid var(--line)",
                    borderRadius: 0,
                  }}
                />
                <Legend />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="otd"
                  stroke="var(--ink)"
                  strokeWidth={1.5}
                  dot={false}
                  name="OTD %"
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="defect"
                  stroke="var(--accent)"
                  strokeWidth={1.5}
                  dot={false}
                  name="Defect %"
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              No trend data
            </p>
          )}
        </ListPanel>
      </section>

      <ButtonBar>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() =>
            openWithQuestion(
              `Why did supplier ${supplier.id} receive a ${supplier.rating} rating? What actions should we take?`,
            )
          }
        >
          {L.askMore}
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() =>
            openWithQuestion(
              `Start formal review for ${supplier.id} ${supplier.name}. Summarize risk and recommend next steps.`,
            )
          }
        >
          {L.startReview}
        </button>
      </ButtonBar>
    </div>
  );
}
