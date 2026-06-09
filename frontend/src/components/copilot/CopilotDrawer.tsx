import { useEffect, useRef, useState } from "react";
import { useCopilot } from "../../context/CopilotContext";
import { t } from "../../i18n";
import { MessageBubble } from "./EvidencePanel";

export function CopilotDrawer() {
  const {
    lang,
    setLang,
    open,
    setOpen,
    messages,
    loading,
    pageContext,
    scenarios,
    loadScenarios,
    sendMessage,
  } = useCopilot();
  const L = t(lang).copilot;
  const [input, setInput] = useState("");
  const [scenario, setScenario] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) void loadScenarios();
  }, [open, loadScenarios]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    void sendMessage(input);
    setInput("");
  };

  const onScenario = (q: string) => {
    if (!q) return;
    void sendMessage(q);
    setScenario("");
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-50 rounded-full bg-[#553c9a] px-5 py-3 text-sm font-semibold text-white shadow-lg hover:bg-[#44307a]"
      >
        {L.open}
      </button>
    );
  }

  const ctxLabel = [
    pageContext.page,
    pageContext.supplierName,
    pageContext.reviewTaskId,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <aside className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-slate-200 bg-white shadow-xl">
      <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div>
          <h2 className="font-semibold text-[#1e3a5f]">{L.title}</h2>
          {ctxLabel ? (
            <p className="text-xs text-slate-500">
              {L.context}: {ctxLabel}
            </p>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          <select
            value={lang}
            onChange={(e) => setLang(e.target.value as "en" | "zh")}
            className="rounded border border-slate-200 px-2 py-1 text-xs"
          >
            <option value="en">EN</option>
            <option value="zh">中文</option>
          </select>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="text-sm text-slate-500 hover:text-slate-800"
          >
            {L.close}
          </button>
        </div>
      </header>

      <div className="border-b border-slate-100 px-4 py-2">
        <label className="text-xs font-medium text-slate-600">{L.scenarios}</label>
        <select
          value={scenario}
          onChange={(e) => {
            const val = e.target.value;
            setScenario(val);
            onScenario(val);
          }}
          className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
        >
          <option value="">—</option>
          {scenarios.map((s) => (
            <option key={s.label} value={s.question}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} lang={lang} />
        ))}
        {loading ? (
          <p className="text-center text-sm text-slate-500">{L.analyzing}</p>
        ) : null}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={onSubmit} className="border-t border-slate-200 p-4">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={L.placeholder}
          rows={2}
          className="w-full resize-none rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-[#553c9a] focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="mt-2 w-full rounded-lg bg-[#1e3a5f] py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {L.send}
        </button>
      </form>
    </aside>
  );
}
