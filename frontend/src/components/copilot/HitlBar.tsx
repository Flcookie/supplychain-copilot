import { useState } from "react";
import { useCopilot } from "../../context/CopilotContext";
import { t } from "../../i18n";
import type { ChatMessage } from "../../types/api";

export function HitlBar({ message }: { message: ChatMessage }) {
  const { lang, loading, resumeApproval } = useCopilot();
  const L = t(lang).copilot;
  const [note, setNote] = useState("");

  if (!message.paused) return null;

  const action = message.proposedAction || message.route_info?.proposed_action;
  const reasons = (message.interrupt?.reasons as string[] | undefined) || [];

  return (
    <div
      className="mt-3 space-y-2 border px-3 py-2 text-xs"
      style={{ borderColor: "var(--warn)", background: "#f5efe3", color: "var(--ink)" }}
    >
      <p className="font-medium">{L.pausedHitl}</p>
      {action ? (
        <p style={{ color: "var(--muted)" }}>
          {L.proposedAction}: {String(action)}
        </p>
      ) : null}
      {reasons.length ? (
        <ul className="list-disc pl-4" style={{ color: "var(--muted)" }}>
          {reasons.slice(0, 4).map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      ) : null}
      <p style={{ color: "var(--muted)" }}>{L.hitlNoWrite}</p>
      <input
        type="text"
        className="field w-full text-xs"
        value={note}
        placeholder={L.hitlNote}
        onChange={(e) => setNote(e.target.value)}
        disabled={loading}
      />
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="btn btn-sm btn-primary"
          disabled={loading}
          onClick={() => void resumeApproval(true, note)}
        >
          {L.approve}
        </button>
        <button
          type="button"
          className="btn btn-sm btn-secondary"
          disabled={loading}
          onClick={() => void resumeApproval(false, note)}
        >
          {L.reject}
        </button>
      </div>
    </div>
  );
}
