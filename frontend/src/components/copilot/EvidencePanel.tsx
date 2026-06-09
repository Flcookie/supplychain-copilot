import { t } from "../../i18n";
import type { ChatMessage, Lang } from "../../types/api";

function SqlBlock({ sql }: { sql: Record<string, unknown> }) {
  return (
    <div className="space-y-1 text-sm">
      {Object.entries(sql).map(([k, v]) =>
        k === "query" && typeof v === "string" ? (
          <pre
            key={k}
            className="overflow-x-auto p-2 text-xs"
            style={{ background: "var(--ink)", color: "#e8e2d9" }}
          >
            {v}
          </pre>
        ) : (
          <p key={k}>
            <span className="font-medium">{k}:</span> {String(v ?? "n/a")}
          </p>
        ),
      )}
    </div>
  );
}

export function EvidencePanel({
  message,
  lang,
}: {
  message: ChatMessage;
  lang: Lang;
}) {
  const L = t(lang).copilot;
  const evidence = message.evidence || {};
  const sql = (evidence.sql as Record<string, unknown>) || {};
  const verified = (evidence.verified_facts as string[]) || [];
  const recommendations = (evidence.recommendations as string[]) || [];
  const hasEvidence =
    Object.keys(sql).length || verified.length || recommendations.length;

  const hasDebug =
    message.route_info ||
    (message.citations && message.citations.length) ||
    (message.sources && message.sources.length);

  if (!hasEvidence && !hasDebug) return null;

  return (
    <div className="mt-3 space-y-2">
      {hasEvidence ? (
        <details className="panel text-sm">
          <summary className="cursor-pointer px-3 py-2 font-medium">{L.evidence}</summary>
          <div className="border-t px-3 py-2" style={{ borderColor: "var(--line)" }}>
            {Object.keys(sql).length > 0 && <SqlBlock sql={sql} />}
            {verified.map((f) => (
              <p key={f} style={{ color: "var(--ink-soft)" }}>
                · {f}
              </p>
            ))}
            {recommendations.map((r) => (
              <p key={r} style={{ color: "var(--ink-soft)" }}>
                → {r}
              </p>
            ))}
          </div>
        </details>
      ) : null}

      {hasDebug ? (
        <details className="panel text-sm">
          <summary className="cursor-pointer px-3 py-2 font-medium">{L.debug}</summary>
          <div className="border-t px-3 py-2" style={{ borderColor: "var(--line)" }}>
            {message.route_info ? (
              <pre className="overflow-x-auto text-xs">{JSON.stringify(message.route_info, null, 2)}</pre>
            ) : null}
            {message.sources?.map((src, i) => (
              <p key={i} className="text-xs" style={{ color: "var(--muted)" }}>
                [{i + 1}] {String(src.source || "Policy")}:{" "}
                {String(src.content || "").slice(0, 200)}
              </p>
            ))}
          </div>
        </details>
      ) : null}
    </div>
  );
}

export function MessageBubble({
  message,
  lang,
}: {
  message: ChatMessage;
  lang: Lang;
}) {
  const L = t(lang).copilot;
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div
          className="max-w-[90%] px-3 py-2 text-sm"
          style={{ background: "var(--ink)", color: "var(--sidebar-active)" }}
        >
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="panel p-3 text-sm">
      <div className="whitespace-pre-wrap leading-relaxed">{message.content}</div>
      {message.route_info?.human_approval_required ? (
        <p
          className="mt-2 border px-2 py-1 text-xs"
          style={{ borderColor: "var(--warn)", color: "var(--warn)", background: "#f5efe3" }}
        >
          {L.humanApproval}
        </p>
      ) : null}
      <EvidencePanel message={message} lang={lang} />
    </div>
  );
}
