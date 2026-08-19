import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  sendChat,
  fetchScenarios,
  fetchThreadState,
  resumeThread,
  runSupplierAssessment,
} from "../api/client";
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
  paused: boolean;
  loadScenarios: () => Promise<void>;
  /** Ask AI; results stay on page unless openDrawer is true. */
  ask: (question: string, options?: AskOptions) => Promise<ChatMessage | null>;
  /** @deprecated Prefer ask() — opens drawer automatically. */
  openWithQuestion: (question: string, prefix?: string) => void;
  sendMessage: (question: string, options?: AskOptions) => Promise<ChatMessage | null>;
  resumeApproval: (approved: boolean, note?: string) => Promise<ChatMessage | null>;
  clearClarification: () => void;
}

const CopilotContext = createContext<CopilotContextValue | null>(null);
const THREAD_STORAGE_KEY = "scc.copilot.thread_id";

function readStoredThreadId(): string | null {
  try {
    return localStorage.getItem(THREAD_STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeStoredThreadId(id: string | null) {
  try {
    if (id) localStorage.setItem(THREAD_STORAGE_KEY, id);
    else localStorage.removeItem(THREAD_STORAGE_KEY);
  } catch {
    /* ignore quota / private mode */
  }
}

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
    paused: Boolean(res.paused),
    interrupt: res.interrupt ?? undefined,
    approvalDecision: res.approval_decision ?? undefined,
    proposedAction: res.proposed_action ?? undefined,
    taskPlan: res.task_plan ?? undefined,
    supplierId: res.supplier_id ?? undefined,
  };
}

function pausedMessageFromThread(
  threadId: string,
  snap: Awaited<ReturnType<typeof fetchThreadState>>,
  lang: Lang,
): ChatMessage {
  const values = snap.values || {};
  const interrupt = snap.interrupt || undefined;
  const answer =
    (typeof values.answer === "string" && values.answer) ||
    (typeof interrupt?.draft_preview === "string" && interrupt.draft_preview) ||
    (typeof interrupt?.message === "string" && interrupt.message) ||
    "";
  const supplierId =
    (typeof values.supplier_id === "string" && values.supplier_id) ||
    (typeof interrupt?.supplier_id === "string" && interrupt.supplier_id) ||
    undefined;
  return {
    id: nextId(),
    role: "assistant",
    content: answer,
    lang,
    intent: typeof values.intent === "string" ? values.intent : "supplier_assessment",
    route_info: {
      intent: typeof values.intent === "string" ? values.intent : "supplier_assessment",
      human_approval_required: true,
      paused: true,
      task_step: "awaiting_approval",
      supplier_id: supplierId,
      proposed_action:
        typeof values.proposed_action === "string"
          ? values.proposed_action
          : typeof interrupt?.proposed_action === "string"
            ? interrupt.proposed_action
            : null,
      review_status: typeof values.review_status === "string" ? values.review_status : null,
    },
    evidence: (values.evidence as Record<string, unknown>) || {},
    citations: (values.citations as Record<string, unknown>[]) || [],
    threadId,
    reviewStatus: typeof values.review_status === "string" ? values.review_status : null,
    paused: true,
    interrupt,
    proposedAction:
      typeof values.proposed_action === "string"
        ? values.proposed_action
        : typeof interrupt?.proposed_action === "string"
          ? interrupt.proposed_action
          : undefined,
    supplierId,
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
  const [threadId, setThreadId] = useState<string | null>(() => readStoredThreadId());
  const [restored, setRestored] = useState(false);

  const paused = messages.some((m) => m.role === "assistant" && m.paused);

  useEffect(() => {
    writeStoredThreadId(threadId);
  }, [threadId]);

  useEffect(() => {
    if (restored) return;
    const saved = threadId || readStoredThreadId();
    if (!saved) {
      setRestored(true);
      return;
    }
    let cancelled = false;
    void fetchThreadState(saved)
      .then((snap) => {
        if (cancelled) return;
        setThreadId(saved);
        if (snap.paused || snap.next?.includes("approval")) {
          setMessages([pausedMessageFromThread(saved, snap, lang)]);
          setOpen(true);
        }
      })
      .catch(() => {
        writeStoredThreadId(null);
        if (!cancelled) setThreadId(null);
      })
      .finally(() => {
        if (!cancelled) setRestored(true);
      });
    return () => {
      cancelled = true;
    };
  }, [lang, restored, threadId]);

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

  const resumeApproval = useCallback(
    async (approved: boolean, note?: string): Promise<ChatMessage | null> => {
      if (!threadId || loading) return null;
      setLoading(true);
      try {
        const res = await resumeThread({
          thread_id: threadId,
          approved,
          note: note?.trim() || null,
          language: lang,
        });
        const assistant = toAssistantMessage(res, lang);
        setMessages((prev) => {
          const next = [...prev];
          for (let i = next.length - 1; i >= 0; i -= 1) {
            if (next[i].role === "assistant" && next[i].paused) {
              next[i] = assistant;
              return next;
            }
          }
          return [...next, assistant];
        });
        return assistant;
      } finally {
        setLoading(false);
      }
    },
    [lang, loading, threadId],
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
      paused,
      loadScenarios,
      ask,
      openWithQuestion,
      sendMessage,
      resumeApproval,
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
      paused,
      loadScenarios,
      ask,
      openWithQuestion,
      sendMessage,
      resumeApproval,
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
