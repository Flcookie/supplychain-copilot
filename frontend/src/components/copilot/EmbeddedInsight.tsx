import { useState } from "react";
import { t } from "../../i18n";
import type { ChatMessage, Lang } from "../../types/api";
import { EvidencePanel } from "./EvidencePanel";
import { HitlBar } from "./HitlBar";

export function EmbeddedInsight({
  title,
  loading,
  message,
  lang,
  emptyHint,
  onOpenAssistant,
  onClarifyReply,
  variant = "section",
  showDebug = false,
}: {
  title?: string;
  loading?: boolean;
  message: ChatMessage | null;
  lang: Lang;
  emptyHint?: string;
  onOpenAssistant?: () => void;
  onClarifyReply?: (reply: string) => void;
  variant?: "section" | "inline";
  showDebug?: boolean;
}) {
  const L = t(lang).copilot;
  const [clarifyText, setClarifyText] = useState("");

  if (!loading && !message && !emptyHint) return null;

  const needsClarification = Boolean(message?.clarificationRequired);

  const body = (
    <div className={variant === "inline" ? "insight-inline" : "panel panel-pad"}>
      {loading ? (
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          {L.analyzing}
        </p>
      ) : message ? (
        <>
          <div className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</div>
          {needsClarification && onClarifyReply ? (
            <form
              className="mt-3 flex flex-wrap gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                const reply = clarifyText.trim();
                if (!reply) return;
                setClarifyText("");
                onClarifyReply(reply);
              }}
            >
              <input
                type="text"
                className="field min-w-[12rem] flex-1 text-sm"
                value={clarifyText}
                placeholder={L.clarifyPlaceholder}
                onChange={(e) => setClarifyText(e.target.value)}
              />
              <button type="submit" className="btn btn-sm btn-primary">
                {L.send}
              </button>
            </form>
          ) : null}
          {message.paused ? <HitlBar message={message} /> : null}
          {message.route_info?.human_approval_required && !message.paused && !message.approvalDecision ? (
            <p
              className="mt-3 border px-2 py-1 text-xs"
              style={{
                borderColor: "var(--warn)",
                color: "var(--warn)",
                background: "#f5efe3",
              }}
            >
              {L.humanApproval}
            </p>
          ) : null}
          <EvidencePanel message={message} lang={lang} showDebug={showDebug} />
        </>
      ) : (
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          {emptyHint}
        </p>
      )}
    </div>
  );

  if (variant === "inline") {
    return body;
  }

  return (
    <section className="page-section">
      <div className="page-section-head">
        <h2 className="panel-title">{title}</h2>
        {onOpenAssistant ? (
          <button type="button" className="btn btn-sm btn-ghost" onClick={onOpenAssistant}>
            {L.openAssistant}
          </button>
        ) : null}
      </div>
      {body}
    </section>
  );
}
