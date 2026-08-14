import { useEffect, useMemo, useState } from "react";
import { fetchPolicies } from "../api/client";
import { EmbeddedInsight } from "../components/copilot/EmbeddedInsight";
import { PolicyAiPanel } from "../components/policy/PolicyAiPanel";
import { useCopilot } from "../context/CopilotContext";
import { t } from "../i18n";
import type { ChatMessage, PolicyDoc } from "../types/api";
import {
  ActionCell,
  CategoryBadge,
  DataTable,
  ListPanel,
  PageHeader,
} from "../components/shared/UiBits";

const CATEGORIES = ["All", "ESG", "Quality", "Procurement", "Compliance"];

export function PolicyPage() {
  const { lang, ask, setOpen } = useCopilot();
  const L = t(lang).policy;
  const [docs, setDocs] = useState<PolicyDoc[]>([]);
  const [search, setSearch] = useState("");
  const [cat, setCat] = useState("All");
  const [loading, setLoading] = useState(false);
  const [lastQuestion, setLastQuestion] = useState("");
  const [answer, setAnswer] = useState<ChatMessage | null>(null);

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

  const runAsk = async (question: string) => {
    const q = question.trim();
    if (!q) return;
    setLastQuestion(q);
    setLoading(true);
    try {
      const msg = await ask(q);
      setAnswer(msg);
    } finally {
      setLoading(false);
    }
  };

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
          onKeyDown={(e) => {
            if (e.key === "Enter" && search.trim()) void runAsk(search);
          }}
        />
        <button
          type="button"
          disabled={loading || !search.trim()}
          onClick={() => void runAsk(search)}
          className="btn btn-primary"
        >
          {L.searchPolicy}
        </button>
      </div>

      <div className="toolbar mb-4">
        {CATEGORIES.map((c) => (
          <button
            key={c}
            type="button"
            onClick={() => setCat(c)}
            className={`btn btn-sm ${cat === c ? "btn-primary" : "btn-ghost"}`}
          >
            {c === "All" ? L.all : c}
          </button>
        ))}
      </div>

      {(loading || answer) && (
        <EmbeddedInsight
          title={L.answerTitle}
          loading={loading}
          message={answer}
          lang={lang}
          emptyHint={lastQuestion ? t(lang).copilot.analyzing : undefined}
          onOpenAssistant={() => setOpen(true)}
        />
      )}

      <ListPanel className="mb-6">
        <DataTable>
          <thead>
            <tr>
              <th>Document</th>
              <th>Category</th>
              <th>Updated</th>
              <th>Scope</th>
              <th className="col-actions">Action</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((doc) => (
              <tr key={doc.id}>
                <td className="font-medium">{doc.title}</td>
                <td>
                  <CategoryBadge category={doc.category} />
                </td>
                <td className="tabular-nums" style={{ color: "var(--muted)" }}>
                  {doc.last_updated}
                </td>
                <td style={{ color: "var(--ink-soft)" }}>{doc.scope}</td>
                <ActionCell>
                  <button
                    type="button"
                    onClick={() => void runAsk(doc.quick_question)}
                    className="btn btn-sm btn-secondary"
                  >
                    {L.askAboutDoc}
                  </button>
                </ActionCell>
              </tr>
            ))}
          </tbody>
        </DataTable>
      </ListPanel>

      <PolicyAiPanel onAsk={(q) => void runAsk(q)} loading={loading} />
    </div>
  );
}
