import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { sendChat, fetchScenarios, runSupplierAssessment } from "../api/client";
import type {
  ChatMessage,
  ChatResponse,
  Lang,
  PageContext,
  ScenarioItem,
} from "../types/api";

export interface AskOptions {
  /** Open the global assistant drawer (default: false — show inline on page). */
  openDrawer?: boolean;
  /** Reset pending clarification from a prior drawer session (default: false). */
  fresh?: boolean;
  /** Merge into page context for this request only (avoids stale React state). */
  contextOverride?: Partial<PageContext>;
  /** Force multi-step supplier assessment task via /api/assessment. */
  assessment?: boolean;
  supplierId?: string;
}

interface CopilotContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  open: boolean;
  setOpen: (open: boolean) => void;
  messages: ChatMessage[];
  loading: boolean;
  clarificationBase: string | null;
  pageContext: PageContext;
  setPageContext: (ctx: PageContext | ((prev: PageContext) => PageContext)) => void;
  scenarios: ScenarioItem[];
  threadId: string | null;
  loadScenarios: () => Promise<void>;
  /** Ask AI; results stay on page unless openDrawer is true. */
  ask: (question: string, options?: AskOptions) => Promise<ChatMessage | null>;
  /** @deprecated Prefer ask() — opens drawer automatically. */
  openWithQuestion: (question: string, prefix?: string) => void;
  sendMessage: (question: string, options?: AskOptions) => Promise<ChatMessage | null>;
  clearClarification: () => void;
}

const CopilotContext = createContext<CopilotContextValue | null>(null);

function buildContextPrefix(ctx: PageContext): string {
  const parts: string[] = [];
  if (ctx.page) parts.push(`Current page: ${ctx.page}`);
  if (ctx.supplierId) {
    parts.push(
      ctx.supplierName
        ? `Supplier context: ${ctx.supplierId} ${ctx.supplierName}`
        : `Supplier context: ${ctx.supplierId}`,
    );
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

function toAssistantMessage(res: ChatResponse, lang: Lang): ChatMessage {
  return {
    id: nextId(),
    role: "assistant",
    content: res.answer,
    lang,
    intent: res.intent,
    clarificationRequired: res.clarification_required,
    route_info: res.route_info,
    evidence: res.evidence,
    citations: res.citations,
    sources: res.sources,
    threadId: res.thread_id ?? undefined,
    reviewStatus: res.review_status,
  };
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
  const [threadId, setThreadId] = useState<string | null>(null);

  const loadScenarios = useCallback(async () => {
    const data = await fetchScenarios(lang);
    setScenarios(data.scenarios);
  }, [lang]);

  const sendMessage = useCallback(
    async (rawQuestion: string, options?: AskOptions): Promise<ChatMessage | null> => {
      const question = rawQuestion.trim();
      if (!question || loading) return null;

      const openDrawer = options?.openDrawer ?? false;
      const fresh = options?.fresh ?? false;
      if (openDrawer) setOpen(true);
      if (fresh) {
        setClarificationBase(null);
        setThreadId(null);
      }

      const ctx = options?.contextOverride
        ? { ...pageContext, ...options.contextOverride }
        : pageContext;
      const prefix = buildContextPrefix(ctx);
      const fullQuestion = prefix ? `${prefix}${question}` : question;
      const supplierId = options?.supplierId || ctx.supplierId;

      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: "user", content: question, lang },
      ]);
      setLoading(true);

      try {
        const pendingClarification = fresh ? null : clarificationBase;
        const baseForApi = pendingClarification
          ? pendingClarification.startsWith("[Context:")
            ? pendingClarification
            : `${prefix}${pendingClarification}`
          : null;

        const res =
          options?.assessment && supplierId
            ? await runSupplierAssessment({
                supplier_id: supplierId,
                language: lang,
                question: pendingClarification ? question : fullQuestion,
                thread_id: fresh ? null : threadId,
              })
            : await sendChat({
                question: pendingClarification ? question : fullQuestion,
                language: lang,
                clarification_base_question: baseForApi,
                thread_id: fresh ? null : threadId,
                supplier_id: supplierId || null,
              });

        if (res.thread_id) setThreadId(res.thread_id);

        if (res.clarification_required) {
          setClarificationBase(fullQuestion);
        } else {
          setClarificationBase(null);
        }

        const assistant = toAssistantMessage(res, lang);
        setMessages((prev) => [...prev, assistant]);
        return assistant;
      } finally {
        setLoading(false);
      }
    },
    [clarificationBase, lang, loading, pageContext, threadId],
  );

  const ask = sendMessage;

  const openWithQuestion = useCallback(
    (question: string, prefix?: string) => {
      if (prefix) {
        setPageContext((p) => ({ ...p, extraPrefix: prefix }));
      }
      void sendMessage(question, { openDrawer: true });
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
      threadId,
      loadScenarios,
      ask,
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
      threadId,
      loadScenarios,
      ask,
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
