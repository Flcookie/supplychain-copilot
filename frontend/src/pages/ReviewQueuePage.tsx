import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchReviewQueue, sendChat } from "../api/client";
import { useCopilot } from "../context/CopilotContext";
import { t } from "../i18n";
import type { ReviewQueueItem } from "../types/api";
import {
  AiPrimaryButton,
  AskAiButton,
  ReviewProgress,
} from "../components/shared/UiBits";

function statusLabel(st: string, L: ReturnType<typeof t>["review"]) {
  if (st === "in_progress") return L.statusInProgress;
  if (st === "scheduled") return L.statusScheduled;
  return L.statusPending;
}

export function ReviewQueuePage() {
  const { lang, setOpen, openWithQuestion, setPageContext } = useCopilot();
  const L = t(lang).review;
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Record<string, string>>({});
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [statusMap, setStatusMap] = useState<Record<string, string>>({});
  const [humanApproval, setHumanApproval] = useState<Record<string, boolean>>(
    {},
  );

  useEffect(() => {
    fetchReviewQueue().then((r) => setItems(r.items));
  }, []);

  const completedCount = useMemo(() => {
    return items.filter((task) => {
      const st = statusMap[task.supplier_id] || task.status;
      return st === "in_progress" || st === "completed";
    }).length;
  }, [items, statusMap]);

  const runReview = async (task: ReviewQueueItem) => {
    setExpanded(task.supplier_id);
    setLoadingId(task.supplier_id);
    setOpen(true);
    setPageContext({
      page: "review-queue",
      supplierId: task.supplier_id,
      supplierName: task.supplier_name || undefined,
      reviewTaskId: task.supplier_id,
    });
    const question = `Which suppliers should be reviewed this month due to high risk? Focus on ${task.supplier_id} ${task.supplier_name}. Reason: ${task.reason}`;
    try {
      const res = await sendChat({ question, language: lang });
      setAnalysis((a) => ({ ...a, [task.supplier_id]: res.answer }));
      setHumanApproval((h) => ({
        ...h,
        [task.supplier_id]: Boolean(res.route_info.human_approval_required),
      }));
      setStatusMap((s) => ({ ...s, [task.supplier_id]: "in_progress" }));
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-[#1e3a5f]">{L.title}</h1>
      <p className="text-slate-600">
        {items.length} {L.pending}
      </p>

      <ReviewProgress
        completed={completedCount}
        total={items.length}
        label={L.progress}
      />

      <p className="text-xs text-[#553c9a]">💡 {L.aiAutoHint}</p>

      <div className="space-y-3">
        {items.map((task) => {
          const st = statusMap[task.supplier_id] || task.status;
          const isOpen = expanded === task.supplier_id;
          return (
            <div
              key={task.supplier_id}
              className="rounded-xl border border-slate-200 bg-white"
            >
              <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`rounded px-1.5 py-0.5 text-xs font-bold ${
                        task.priority === "P1"
                          ? "bg-red-200 text-red-900"
                          : task.priority === "P2"
                            ? "bg-orange-200 text-orange-900"
                            : "bg-green-200 text-green-900"
                      }`}
                    >
                      {task.priority}
                    </span>
                    <span className="font-medium">
                      {task.supplier_name} ({task.supplier_id})
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        st === "in_progress"
                          ? "bg-blue-100 text-blue-800"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {statusLabel(st, L)}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-slate-600">{task.reason}</p>
                  <p className="text-xs text-slate-400">Due {task.due_date}</p>
                </div>
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                  <button
                    type="button"
                    onClick={() => void runReview(task)}
                    className="rounded-lg bg-[#1e3a5f] px-4 py-2 text-xs font-semibold text-white"
                  >
                    {st === "in_progress" ? L.continue : L.start}
                  </button>
                  <AiPrimaryButton
                    label={L.aiExplain}
                    sublabel={L.aiSummary}
                    onClick={() =>
                      openWithQuestion(
                        `Explain the risk for ${task.supplier_id} ${task.supplier_name} and recommend buyer actions. Context: ${task.reason}`,
                      )
                    }
                  />
                  <Link
                    to={`/suppliers/${task.supplier_id}`}
                    className="text-center text-xs text-[#1e3a5f] underline"
                  >
                    Supplier profile
                  </Link>
                </div>
              </div>

              {isOpen && (
                <div className="border-t border-purple-100 bg-gradient-to-b from-purple-50/80 to-slate-50 px-4 py-4 text-sm">
                  <p className="mb-2 text-xs font-semibold uppercase text-[#553c9a]">
                    🤖 {L.aiSummary}
                  </p>
                  {loadingId === task.supplier_id ? (
                    <p>{t(lang).common.loading}</p>
                  ) : (
                    <p className="whitespace-pre-wrap">{analysis[task.supplier_id]}</p>
                  )}
                  {humanApproval[task.supplier_id] ? (
                    <p className="mt-2 rounded border border-amber-300 bg-amber-50 px-2 py-1 text-xs">
                      {t(lang).copilot.humanApproval}
                    </p>
                  ) : null}
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="rounded border bg-white px-2 py-1 text-xs"
                      onClick={() => alert("PIP draft simulated")}
                    >
                      {L.pip}
                    </button>
                    <button
                      type="button"
                      className="rounded border border-red-200 bg-white px-2 py-1 text-xs text-red-700"
                      onClick={() => {
                        setHumanApproval((h) => ({
                          ...h,
                          [task.supplier_id]: true,
                        }));
                        alert("Requires manager approval");
                      }}
                    >
                      {L.blacklist}
                    </button>
                    <AskAiButton
                      label={L.aiExplain}
                      onClick={() =>
                        openWithQuestion(
                          `What PIP or remediation steps for ${task.supplier_id}?`,
                        )
                      }
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
