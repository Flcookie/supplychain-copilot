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
import { fetchSupplier, fetchSuppliers, sendChat } from "../api/client";
import { useCopilot } from "../context/CopilotContext";
import { t } from "../i18n";
import type { Supplier } from "../types/api";
import { AiPrimaryButton, OtdCell, RatingBadge, RiskBadge } from "../components/shared/UiBits";

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
    fetchSuppliers({ search: search || undefined, category: category || undefined, risk_level: risk || undefined })
      .then((r) => setItems(r.items))
      .catch(console.error);
  }, [search, category, risk]);

  const categories = useMemo(
    () => [...new Set(items.map((s) => s.category))],
    [items],
  );

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-[#1e3a5f]">{L.title}</h1>

      <div className="flex flex-wrap gap-3">
        <input
          type="search"
          placeholder={L.search}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
        />
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
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
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
        >
          <option value="">{L.filters.risk}</option>
          <option value="high">high</option>
          <option value="medium">medium</option>
          <option value="low">low</option>
        </select>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead className="border-b bg-slate-50 text-left text-slate-600">
            <tr>
              <th className="px-4 py-3">Supplier</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Rating</th>
              <th className="px-4 py-3">OTD</th>
              <th className="px-4 py-3">Risk</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {items.map((s) => (
              <tr key={s.id} className="border-b border-slate-100">
                <td className="px-4 py-3 font-medium">{s.name}</td>
                <td className="px-4 py-3">{s.category}</td>
                <td className="px-4 py-3">
                  <RatingBadge rating={s.rating} />
                </td>
                <td className="px-4 py-3">
                  <OtdCell rate={s.otd_rate} />
                </td>
                <td className="px-4 py-3">
                  <RiskBadge level={s.risk_level} />
                </td>
                <td className="px-4 py-3">{s.status}</td>
                <td className="px-4 py-3">
                  <Link
                    to={`/suppliers/${s.id}`}
                    className="text-[#1e3a5f] underline"
                  >
                    {L.details}
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function SupplierDetailPage({ supplierId }: { supplierId: string }) {
  const { lang, setPageContext, setOpen, openWithQuestion, sendMessage } =
    useCopilot();
  const L = t(lang).suppliers;
  const [supplier, setSupplier] = useState<Supplier | null>(null);
  const [aiSummary, setAiSummary] = useState<string | null>(null);
  const [loadingAi, setLoadingAi] = useState(false);

  useEffect(() => {
    fetchSupplier(supplierId).then(setSupplier);
  }, [supplierId]);

  useEffect(() => {
    if (!supplier) return;
    setPageContext({
      page: "supplier-detail",
      supplierId: supplier.id,
      supplierName: supplier.name,
    });
    setLoadingAi(true);
    sendChat({
      question: `[Context: supplier ${supplier.id} ${supplier.name}]\nWhy did supplier ${supplier.id} receive a ${supplier.rating} rating?`,
      language: lang,
    })
      .then((r) => setAiSummary(r.answer))
      .catch(console.error)
      .finally(() => setLoadingAi(false));
  }, [supplier, lang, setPageContext]);

  if (!supplier) return <p>{t(lang).common.loading}</p>;

  const trend = supplier.kpi_trend || {};
  const chartData = (trend.months || []).map((m, i) => ({
    month: m,
    otd: ((trend.otd || [])[i] ?? 0) * 100,
    defect: ((trend.defect || [])[i] ?? 0) * 100,
  }));

  return (
    <div className="space-y-4">
      <Link to="/suppliers" className="text-sm text-[#1e3a5f] underline">
        ← {L.back}
      </Link>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold text-[#1e3a5f]">{supplier.name}</h1>
        <span className="text-slate-500">{supplier.id}</span>
        <RatingBadge rating={supplier.rating} />
        <RiskBadge level={supplier.risk_level} />
      </div>
      <p className="text-slate-600">
        {supplier.category} · {supplier.country}
      </p>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 font-semibold">Profile</h2>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-slate-500">Rating</dt>
            <dd>{supplier.rating}</dd>
            <dt className="text-slate-500">OTD</dt>
            <dd>{(supplier.otd_rate * 100).toFixed(1)}%</dd>
            <dt className="text-slate-500">Contract expiry</dt>
            <dd>{supplier.contract_expiry}</dd>
            <dt className="text-slate-500">Last review</dt>
            <dd>{supplier.last_review}</dd>
          </dl>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 font-semibold">KPI trend (6 mo)</h2>
          {chartData.length ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip />
                <Legend />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="otd"
                  stroke="#1e3a5f"
                  name="OTD %"
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="defect"
                  stroke="#dd6b20"
                  name="Defect %"
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-slate-500">No trend data</p>
          )}
        </div>
      </div>

      <div className="rounded-xl border-2 border-[#553c9a]/30 bg-gradient-to-br from-blue-50 to-purple-50 p-5">
        <h2 className="mb-2 font-semibold text-[#553c9a]">🤖 {L.aiAnalysis}</h2>
        {loadingAi ? (
          <p className="text-sm text-slate-600">{t(lang).common.loading}</p>
        ) : (
          <p className="whitespace-pre-wrap text-sm">{aiSummary}</p>
        )}
        <div className="mt-4 flex flex-wrap gap-2">
          <AiPrimaryButton
            label={L.askMore}
            sublabel="Follow-up in Copilot"
            onClick={() => {
              setOpen(true);
              void sendMessage(
                `What actions should we take for ${supplier.name}?`,
              );
            }}
          />
          <button
            type="button"
            className="rounded-lg bg-[#1e3a5f] px-3 py-1 text-xs text-white"
            onClick={() =>
              openWithQuestion(
                `Start formal review for ${supplier.id} ${supplier.name}`,
              )
            }
          >
            {L.startReview}
          </button>
        </div>
      </div>
    </div>
  );
}
