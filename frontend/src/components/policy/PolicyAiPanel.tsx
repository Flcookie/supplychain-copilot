import { useCopilot } from "../../context/CopilotContext";
import { t } from "../../i18n";
import type { PolicyDoc } from "../../types/api";
import { AiPrimaryButton } from "../shared/UiBits";

const QUICK_PROMPTS = [
  "What ESG documents are required for yarn suppliers from China?",
  "What is the process for C-rated suppliers?",
  "What monitoring applies to strategic yarn suppliers?",
];

export function PolicyAiPanel({
  docs,
  onAsk,
  loading,
}: {
  docs: PolicyDoc[];
  onAsk: (q: string) => void;
  loading: boolean;
}) {
  const { lang, setOpen, messages } = useCopilot();
  const L = t(lang).policy;

  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");

  return (
    <div className="sticky top-4 space-y-4 rounded-xl border-2 border-[#553c9a]/30 bg-gradient-to-b from-purple-50 to-white p-4 shadow-sm">
      <div>
        <h2 className="flex items-center gap-2 font-semibold text-[#553c9a]">
          <span aria-hidden>🤖</span> {L.aiPanelTitle}
        </h2>
        <p className="mt-1 text-xs text-slate-600">{L.aiPanelDesc}</p>
      </div>

      <AiPrimaryButton
        label={L.aiPanelCta}
        sublabel={L.aiPanelCtaSub}
        disabled={loading}
        onClick={() => setOpen(true)}
      />

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          {L.suggestedQuestions}
        </p>
        <ul className="space-y-2">
          {QUICK_PROMPTS.map((q) => (
            <li key={q}>
              <button
                type="button"
                disabled={loading}
                onClick={() => onAsk(q)}
                className="w-full rounded-lg border border-purple-200 bg-white px-3 py-2 text-left text-xs text-slate-700 hover:border-[#553c9a] hover:bg-purple-50 disabled:opacity-50"
              >
                {q}
              </button>
            </li>
          ))}
        </ul>
      </div>

      {docs.length > 0 ? (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            {L.fromDocuments}
          </p>
          <ul className="max-h-40 space-y-1 overflow-y-auto">
            {docs.slice(0, 4).map((d) => (
              <li key={d.id}>
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => onAsk(d.quick_question)}
                  className="w-full truncate text-left text-xs text-[#553c9a] underline hover:text-[#44307a]"
                >
                  {d.title}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {lastAssistant ? (
        <div className="rounded-lg border border-slate-200 bg-white p-3">
          <p className="mb-1 text-xs font-semibold text-slate-500">{L.lastAnswer}</p>
          <p className="line-clamp-4 text-xs text-slate-700 whitespace-pre-wrap">
            {lastAssistant.content.slice(0, 280)}
            {lastAssistant.content.length > 280 ? "…" : ""}
          </p>
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="mt-2 text-xs font-medium text-[#553c9a] underline"
          >
            {L.openFullCopilot}
          </button>
        </div>
      ) : (
        <p className="rounded-lg border border-dashed border-purple-200 px-3 py-4 text-center text-xs text-slate-500">
          {L.aiPanelEmpty}
        </p>
      )}
    </div>
  );
}
