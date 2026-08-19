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
    scenarios,
    loadScenarios,
    sendMessage,
    paused,
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
    void sendMessage(input, { openDrawer: true });
    setInput("");
  };

  const onScenario = (q: string) => {
    if (!q) return;
    void sendMessage(q, { openDrawer: true });
    setScenario("");
  };

  return (
    <>
      {!open ? (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="btn btn-fab btn-ghost fixed bottom-6 right-6 z-40 shadow-md"
          title={L.openAssistantHint}
        >
          {L.open}
        </button>
      ) : null}

      {open ? (
        <button
          type="button"
          aria-label={L.close}
          className="fixed inset-0 z-40 bg-black/20"
          onClick={() => setOpen(false)}
        />
      ) : null}

      <aside
        className={`fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l shadow-xl transition-transform duration-200 ${
          open ? "translate-x-0" : "translate-x-full pointer-events-none"
        }`}
        style={{ background: "var(--surface)", borderColor: "var(--line-strong)" }}
        aria-hidden={!open}
      >
        <header
          className="flex items-center justify-between border-b px-5 py-4"
          style={{ borderColor: "var(--line)" }}
        >
          <div>
            <h2 className="font-serif text-xl font-normal">{L.title}</h2>
            <p className="text-xs" style={{ color: "var(--muted)" }}>
              {paused ? L.pausedBanner : L.drawerHint}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={lang}
              onChange={(e) => setLang(e.target.value as "en" | "zh")}
              className="field w-auto py-1 text-xs"
            >
              <option value="en">EN</option>
              <option value="zh">中文</option>
            </select>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="btn btn-ghost py-1"
            >
              {L.close}
            </button>
          </div>
        </header>

        <div className="border-b px-5 py-3" style={{ borderColor: "var(--line)" }}>
          <label className="panel-title">{L.scenarios}</label>
          <select
            value={scenario}
            onChange={(e) => {
              const val = e.target.value;
              setScenario(val);
              onScenario(val);
            }}
            className="field mt-1"
          >
            <option value="">—</option>
            {scenarios.map((s) => (
              <option key={s.label} value={s.question}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
          {messages.length === 0 && !loading ? (
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              {L.drawerEmpty}
            </p>
          ) : null}
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} lang={lang} />
          ))}
          {loading ? (
            <p className="text-center text-sm" style={{ color: "var(--muted)" }}>
              {L.analyzing}
            </p>
          ) : null}
          <div ref={bottomRef} />
        </div>

        <form
          onSubmit={onSubmit}
          className="border-t p-5"
          style={{ borderColor: "var(--line)", background: "var(--paper)" }}
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={paused ? L.pausedHitl : L.placeholder}
            rows={2}
            className="field resize-none"
            disabled={paused || loading}
          />
          <button
            type="submit"
            disabled={loading || paused || !input.trim()}
            className="btn btn-primary btn-block mt-2"
          >
            {L.send}
          </button>
        </form>
      </aside>
    </>
  );
}
