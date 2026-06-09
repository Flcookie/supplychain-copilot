import { useEffect, useMemo, useState } from "react";
import { fetchPolicies } from "../api/client";
import { PolicyAiPanel } from "../components/policy/PolicyAiPanel";
import { useCopilot } from "../context/CopilotContext";
import { t } from "../i18n";
import type { PolicyDoc } from "../types/api";
import { AiPrimaryButton, CategoryBadge, VersionBadge } from "../components/shared/UiBits";

const CATEGORIES = ["All", "ESG", "Quality", "Procurement", "Compliance"];

function extractVersion(title: string): string | null {
  const m = title.match(/v[\d.]+/i);
  return m ? m[0] : null;
}

export function PolicyPage() {
  const { lang, setOpen, sendMessage } = useCopilot();
  const L = t(lang).policy;
  const [docs, setDocs] = useState<PolicyDoc[]>([]);
  const [search, setSearch] = useState("");
  const [cat, setCat] = useState("All");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchPolicies().then((r) => setDocs(r.items));
  }, []);

  const filtered = useMemo(() => {
    return docs.filter((d) => {
      const matchCat = cat === "All" || d.category === cat;
      const q = search.toLowerCase();
      const matchSearch =
        !q ||
        d.title.toLowerCase().includes(q) ||
        d.scope.toLowerCase().includes(q);
      return matchCat && matchSearch;
    });
  }, [docs, cat, search]);

  const ask = async (question: string) => {
    setLoading(true);
    setOpen(true);
    try {
      await sendMessage(question);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="space-y-4 lg:col-span-2">
        <h1 className="text-2xl font-bold text-[#1e3a5f]">{L.title}</h1>
        <div className="flex flex-wrap gap-2">
          <input
            type="search"
            placeholder={L.search}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="min-w-[200px] flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
          />
          <AiPrimaryButton
            label={t(lang).copilot.askAi}
            sublabel="Search with AI + citations"
            disabled={loading || !search.trim()}
            onClick={() => void ask(search)}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          {CATEGORIES.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setCat(c)}
              className={`rounded-full px-3 py-1 text-xs font-medium ${
                cat === c ? "bg-[#1e3a5f] text-white" : "bg-slate-200 text-slate-700"
              }`}
            >
              {c === "All" ? L.all : c}
            </button>
          ))}
        </div>
        <ul className="space-y-3">
          {filtered.map((doc) => {
            const ver = extractVersion(doc.title);
            return (
              <li
                key={doc.id}
                className="rounded-xl border border-slate-200 bg-white p-4 transition-shadow hover:shadow-sm"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <h3 className="font-medium">📄 {doc.title}</h3>
                  <div className="flex gap-1.5">
                    <CategoryBadge category={doc.category} />
                    {ver ? <VersionBadge version={ver} /> : null}
                  </div>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  Updated {doc.last_updated} · {doc.scope}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="rounded border border-slate-300 px-3 py-1 text-xs"
                    onClick={() => alert(`View ${doc.id} (demo)`)}
                  >
                    {L.view}
                  </button>
                  <AiPrimaryButton
                    label={L.askAboutDoc}
                    onClick={() => void ask(doc.quick_question)}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      </div>
      <PolicyAiPanel docs={filtered} onAsk={(q) => void ask(q)} loading={loading} />
    </div>
  );
}
