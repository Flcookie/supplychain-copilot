import type {
  ChatResponse,
  DashboardSummary,
  Lang,
  PolicyDoc,
  ReviewQueueItem,
  ScenarioItem,
  Supplier,
  ThreadState,
} from "../types/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export function fetchDashboard(): Promise<DashboardSummary> {
  return request("/api/workbench/dashboard");
}

export function fetchSuppliers(params?: {
  category?: string;
  risk_level?: string;
  status?: string;
  search?: string;
}): Promise<{ total: number; items: Supplier[] }> {
  const q = new URLSearchParams();
  if (params?.category) q.set("category", params.category);
  if (params?.risk_level) q.set("risk_level", params.risk_level);
  if (params?.status) q.set("status", params.status);
  if (params?.search) q.set("search", params.search);
  const qs = q.toString();
  return request(`/api/workbench/suppliers${qs ? `?${qs}` : ""}`);
}

export function fetchSupplier(id: string): Promise<Supplier> {
  return request(`/api/workbench/suppliers/${id}`);
}

export function fetchReviewQueue(): Promise<{
  items: ReviewQueueItem[];
  completed_count: number;
}> {
  return request("/api/workbench/review-queue");
}

export function fetchPolicies(): Promise<{ items: PolicyDoc[] }> {
  return request("/api/workbench/policies");
}

export function fetchScenarios(lang: Lang): Promise<{
  language: Lang;
  scenarios: ScenarioItem[];
}> {
  return request(`/api/scenarios?lang=${lang}`);
}

export function sendChat(body: {
  question: string;
  language: Lang;
  clarification_base_question?: string | null;
  thread_id?: string | null;
  task_type?: "chat" | "supplier_assessment" | null;
  supplier_id?: string | null;
}): Promise<ChatResponse> {
  return request("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function runSupplierAssessment(body: {
  supplier_id: string;
  language: Lang;
  question?: string | null;
  thread_id?: string | null;
}): Promise<ChatResponse> {
  return request("/api/assessment", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function fetchThreadState(threadId: string): Promise<ThreadState> {
  return request(`/api/threads/${encodeURIComponent(threadId)}`);
}

export function resumeThread(body: {
  thread_id: string;
  approved: boolean;
  note?: string | null;
  language: Lang;
}): Promise<ChatResponse> {
  return request(`/api/threads/${encodeURIComponent(body.thread_id)}/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      approved: body.approved,
      note: body.note ?? null,
      language: body.language,
    }),
  });
}
