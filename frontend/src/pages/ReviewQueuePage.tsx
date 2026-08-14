import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import { EmbeddedInsight } from "../components/copilot/EmbeddedInsight";
import { fetchReviewQueue } from "../api/client";
import { useCopilot } from "../context/CopilotContext";
import { t } from "../i18n";
import type { ChatMessage, ReviewQueueItem } from "../types/api";
import {
  ActionCell,
  ButtonBar,
  DataTable,
  ListPanel,
  PageHeader,
  ReviewProgress,
} from "../components/shared/UiBits";

function statusLabel(st: string, L: ReturnType<typeof t>["review"]) {
  if (st === "in_progress") return L.statusInProgress;
  if (st === "scheduled") return L.statusScheduled;
  return L.statusPending;
}

function priorityStyle(priority: string): CSSProperties {
  if (priority === "P1") return { color: "var(--danger)" };
  if (priority === "P2") return { color: "var(--warn)" };
  return { color: "var(--sage)" };
}

function isActiveReview(st: string) {
  return st === "in_progress" || st === "completed";
}

export function ReviewQueuePage() {
  const { lang, setOpen, setPageContext, ask } = useCopilot();
  const L = t(lang).review;
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [statusMap, setStatusMap] = useState<Record<string, string>>({});
  const [insights, setInsights] = useState<Record<string, ChatMessage>>({});
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchReviewQueue()
      .then((r) => {
        setItems(r.items);
        const initial: Record<string, string> = {};
        for (const task of r.items) {
          initial[task.supplier_id] = task.status;
        }
        setStatusMap(initial);
        if (r.items.length) setSelectedId(r.items[0].supplier_id);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const completedCount = useMemo(() => {
    return items.filter((task) => {
      const st = statusMap[task.supplier_id] ?? task.status;
      return isActiveReview(st);
    }).length;
  }, [items, statusMap]);

  const selectedTask = items.find((t) => t.supplier_id === selectedId) ?? null;

  const selectTask = (task: ReviewQueueItem) => {
    setSelectedId(task.supplier_id);
    setPageContext((prev) => ({
      ...prev,
      page: "review-queue",
      supplierId: task.supplier_id,
      supplierName: task.supplier_name || undefined,
      reviewTaskId: task.supplier_id,
    }));
  };

  const runReview = async (task: ReviewQueueItem, force = false) => {
    selectTask(task);
    const id = task.supplier_id;
    if (!force && insights[id]) return;

    setBusyId(id);
    const question = `Review supplier ${task.supplier_id} ${task.supplier_name}. Priority ${task.priority}. Reason: ${task.reason}. Summarize risk and recommend next steps.`;
    try {
      const msg = await ask(question);
      if (msg) {
        setInsights((prev) => ({ ...prev, [id]: msg }));
        setStatusMap((s) => ({ ...s, [id]: "in_progress" }));
      }
    } finally {
      setBusyId(null);
    }
  };

  if (loading) return <p className="page-meta">{t(lang).common.loading}</p>;

  if (error) {
    return (
      <div>
        <PageHeader title={L.title} meta={error} />
      </div>
    );
  }

  return (
    <div>
      <PageHeader title={L.title} />

      <ReviewProgress
        completed={completedCount}
        total={items.length}
        label={L.progress}
      />

      <ListPanel>
        <DataTable>
          <thead>
            <tr>
              <th>Priority</th>
              <th>Supplier</th>
              <th>Status</th>
              <th>Due</th>
              <th>Reason</th>
              <th className="col-actions">Action</th>
            </tr>
          </thead>
          <tbody>
            {items.map((task) => {
              const st = statusMap[task.supplier_id] ?? task.status;
              const reviewing = busyId === task.supplier_id;
              const selected = selectedId === task.supplier_id;
              return (
                <tr
                  key={task.supplier_id}
                  className={`row-clickable ${selected ? "row-selected" : ""}`}
                  onClick={() => selectTask(task)}
                >
                  <td>
                    <span
                      className="text-xs font-semibold uppercase tracking-wide"
                      style={priorityStyle(task.priority)}
                    >
                      {task.priority}
                    </span>
                  </td>
                  <td>
                    <div className="font-medium">{task.supplier_name}</div>
                    <div className="text-xs tabular-nums" style={{ color: "var(--muted)" }}>
                      {task.supplier_id}
                    </div>
                  </td>
                  <td style={{ color: "var(--ink-soft)" }}>{statusLabel(st, L)}</td>
                  <td className="tabular-nums" style={{ color: "var(--muted)" }}>
                    {task.due_date}
                  </td>
                  <td style={{ color: "var(--ink-soft)", maxWidth: "20rem" }}>
                    {task.reason}
                  </td>
                  <ActionCell>
                    <button
                      type="button"
                      disabled={reviewing}
                      onClick={(e) => {
                        e.stopPropagation();
                        void runReview(task, !insights[task.supplier_id]);
                      }}
                      className="btn btn-sm btn-primary"
                    >
                      {reviewing
                        ? t(lang).common.loading
                        : insights[task.supplier_id]
                          ? L.viewAnalysis
                          : isActiveReview(st)
                            ? L.continue
                            : L.start}
                    </button>
                    <Link
                      to={`/suppliers/${task.supplier_id}`}
                      className="btn btn-sm btn-ghost"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {t(lang).suppliers.details}
                    </Link>
                  </ActionCell>
                </tr>
              );
            })}
          </tbody>
        </DataTable>
      </ListPanel>

      {selectedTask ? (
        <>
          <EmbeddedInsight
            title={L.workspaceTitle}
            loading={busyId === selectedTask.supplier_id}
            message={insights[selectedTask.supplier_id] ?? null}
            lang={lang}
            emptyHint={L.workspaceEmpty}
            onOpenAssistant={() => setOpen(true)}
          />
          {insights[selectedTask.supplier_id] ? (
            <ButtonBar>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => alert("PIP draft simulated")}
              >
                {L.pip}
              </button>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => alert("Requires manager approval")}
              >
                {L.blacklist}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => void runReview(selectedTask, true)}
              >
                {L.rerunAnalysis}
              </button>
            </ButtonBar>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
