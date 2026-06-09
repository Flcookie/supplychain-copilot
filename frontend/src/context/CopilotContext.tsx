import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { sendChat, fetchScenarios } from "../api/client";
import type {
  ChatMessage,
  Lang,
  PageContext,
  ScenarioItem,
} from "../types/api";

interface CopilotContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  open: boolean;
  setOpen: (open: boolean) => void;
  messages: ChatMessage[];
  loading: boolean;
  clarificationBase: string | null;
  pageContext: PageContext;
  setPageContext: (ctx: PageContext) => void;
  scenarios: ScenarioItem[];
  loadScenarios: () => Promise<void>;
  openWithQuestion: (question: string, prefix?: string) => void;
  sendMessage: (question: string) => Promise<void>;
  clearClarification: () => void;
}

const CopilotContext = createContext<CopilotContextValue | null>(null);

function buildContextPrefix(ctx: PageContext): string {
  const parts: string[] = [];
  if (ctx.page) parts.push(`Current page: ${ctx.page}`);
  if (ctx.supplierId && ctx.supplierName) {
    parts.push(`Supplier context: ${ctx.supplierId} ${ctx.supplierName}`);
  }
  if (ctx.reviewTaskId) {
    parts.push(`Focus on risk review for ${ctx.reviewTaskId}`);
  }
  if (ctx.extraPrefix) parts.push(ctx.extraPrefix);
  if (!parts.length) return "";
  return `[Context: ${parts.join(" · ")}]\n`;
}

let msgCounter = 0;
function nextId() {
  msgCounter += 1;
  return `msg-${msgCounter}`;
}

export function CopilotProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>("en");
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [clarificationBase, setClarificationBase] = useState<string | null>(
    null,
  );
  const [pageContext, setPageContext] = useState<PageContext>({ page: "home" });
  const [scenarios, setScenarios] = useState<ScenarioItem[]>([]);

  const loadScenarios = useCallback(async () => {
    const data = await fetchScenarios(lang);
    setScenarios(data.scenarios);
  }, [lang]);

  const sendMessage = useCallback(
    async (rawQuestion: string) => {
      const question = rawQuestion.trim();
      if (!question || loading) return;

      const prefix = buildContextPrefix(pageContext);
      const fullQuestion = prefix ? `${prefix}${question}` : question;

      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: "user", content: question, lang },
      ]);
      setLoading(true);

      try {
        const baseForApi = clarificationBase
          ? clarificationBase.startsWith("[Context:")
            ? clarificationBase
            : `${prefix}${clarificationBase}`
          : null;

        const res = await sendChat({
          question: clarificationBase ? question : fullQuestion,
          language: lang,
          clarification_base_question: baseForApi,
        });

        if (res.clarification_required) {
          setClarificationBase(fullQuestion);
        } else {
          setClarificationBase(null);
        }

        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: "assistant",
            content: res.answer,
            lang,
            intent: res.intent,
            route_info: res.route_info,
            evidence: res.evidence,
            citations: res.citations,
            sources: res.sources,
          },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [clarificationBase, lang, loading, pageContext],
  );

  const openWithQuestion = useCallback(
    (question: string, prefix?: string) => {
      setOpen(true);
      if (prefix) {
        setPageContext((p) => ({ ...p, extraPrefix: prefix }));
      }
      void sendMessage(question);
    },
    [sendMessage],
  );

  const value = useMemo(
    () => ({
      lang,
      setLang,
      open,
      setOpen,
      messages,
      loading,
      clarificationBase,
      pageContext,
      setPageContext,
      scenarios,
      loadScenarios,
      openWithQuestion,
      sendMessage,
      clearClarification: () => setClarificationBase(null),
    }),
    [
      lang,
      open,
      messages,
      loading,
      clarificationBase,
      pageContext,
      scenarios,
      loadScenarios,
      openWithQuestion,
      sendMessage,
    ],
  );

  return (
    <CopilotContext.Provider value={value}>{children}</CopilotContext.Provider>
  );
}

export function useCopilot() {
  const ctx = useContext(CopilotContext);
  if (!ctx) throw new Error("useCopilot must be used within CopilotProvider");
  return ctx;
}
