import { intentLabels, t } from "../../i18n";
import type { ChatMessage, Lang } from "../../types/api";

function SqlBlock({ sql }: { sql: Record<string, unknown> }) {
  return (
    <div className="space-y-1 text-sm">
      {Object.entries(sql).map(([k, v]) =>
        k === "query" && typeof v === "string" ? (
          <pre
            key={k}
            className="overflow-x-auto rounded bg-slate-900 p-2 text-xs text-slate-100"
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
  const evSources = (evidence.sources as Record<string, unknown>[]) || [];
  const verified = (evidence.verified_facts as string[]) || [];
  const recommendations = (evidence.recommendations as string[]) || [];
  const hasEvidence =
    Object.keys(sql).length || evSources.length || verified.length;

  const hasDebug =
    message.route_info ||
    (message.citations && message.citations.length) ||
    (message.sources && message.sources.length);

  if (!hasEvidence && !hasDebug) return null;

  return (
    <div className="mt-3 space-y-2">
      {hasEvidence ? (
        <details className="rounded border border-slate-200 bg-white text-sm">
          <summary className="cursor-pointer px-3 py-2 font-medium">
            {L.evidence}
          </summary>
          <div className="border-t border-slate-100 px-3 py-2">
            {Object.keys(sql).length > 0 && <SqlBlock sql={sql} />}
            {verified.map((f) => (
              <p key={f} className="text-slate-700">
                • {f}
              </p>
            ))}
            {recommendations.map((r) => (
              <p key={r} className="text-slate-700">
                → {r}
              </p>
            ))}
          </div>
        </details>
      ) : null}

      {hasDebug ? (
        <details className="rounded border border-slate-200 bg-white text-sm">
          <summary className="cursor-pointer px-3 py-2 font-medium">
            {L.debug}
          </summary>
          <div className="border-t border-slate-100 px-3 py-2">
            {message.route_info ? (
              <pre className="overflow-x-auto text-xs">
                {JSON.stringify(message.route_info, null, 2)}
              </pre>
            ) : null}
            {message.sources?.map((src, i) => (
              <p key={i} className="text-xs text-slate-600">
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
        <div className="max-w-[90%] rounded-lg bg-[#1e3a5f] px-3 py-2 text-sm text-white">
          {message.content}
        </div>
      </div>
    );
  }

  const intent = message.route_info?.intent || message.intent || "general";
  const label = intentLabels[lang][intent] || intentLabels[lang].general;
  const conf = message.route_info?.confidence;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm shadow-sm">
      <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
        <span className="font-semibold text-slate-700">{L.currentTask}</span>
        <span className="rounded-full bg-purple-100 px-2 py-0.5 text-purple-800">
          {label}
        </span>
        <span>
          {L.intent}: {intent}
          {typeof conf === "number" ? ` · ${L.confidence}: ${conf.toFixed(2)}` : ""}
        </span>
      </div>
      <div className="markdown-body whitespace-pre-wrap">{message.content}</div>
      {message.route_info?.human_approval_required ? (
        <p className="mt-2 rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-900">
          {L.humanApproval}
        </p>
      ) : null}
      <EvidencePanel message={message} lang={lang} />
    </div>
  );
}
