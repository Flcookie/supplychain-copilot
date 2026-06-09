export type Lang = "en" | "zh";

export interface RouteInfo {
  intent?: string | null;
  confidence?: number | null;
  ambiguity_type?: string | null;
  human_approval_required?: boolean | null;
  reason?: string | null;
  fallback_mode?: string | null;
  kpi_parse?: Record<string, unknown> | null;
}

export interface ChatResponse {
  answer: string;
  intent: string;
  route_info: RouteInfo;
  evidence: Record<string, unknown>;
  citations: Record<string, unknown>[];
  sources: Record<string, unknown>[];
  clarification_required: boolean;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  lang: Lang;
  intent?: string;
  route_info?: RouteInfo;
  evidence?: Record<string, unknown>;
  citations?: Record<string, unknown>[];
  sources?: Record<string, unknown>[];
}

export interface ScenarioItem {
  label: string;
  question: string;
}

export interface DashboardSummary {
  active_suppliers: number;
  at_risk_suppliers: number;
  reviews_due_this_month: number;
  open_qualifications: number;
  greeting: string;
  period_label: string;
  yarn_kpi_snapshot: Record<string, number>;
  risk_alerts: RiskAlert[];
}

export interface RiskAlert {
  supplier_id: string;
  severity: "high" | "medium" | "low";
  message: string;
  ask_ai_question: string;
}

export interface Supplier {
  id: string;
  name: string;
  category: string;
  country: string;
  rating: string;
  otd_rate: number;
  defect_rate: number;
  risk_level: string;
  status: string;
  contract_expiry: string;
  last_review: string;
  kpi_trend?: {
    otd?: number[];
    defect?: number[];
    months?: string[];
  };
}

export interface ReviewQueueItem {
  supplier_id: string;
  supplier_name?: string | null;
  category?: string | null;
  country?: string | null;
  priority: string;
  reason: string;
  due_date: string;
  status: string;
}

export interface PolicyDoc {
  id: string;
  title: string;
  category: string;
  last_updated: string;
  scope: string;
  quick_question: string;
}

export interface PageContext {
  page: string;
  supplierId?: string;
  supplierName?: string;
  reviewTaskId?: string;
  extraPrefix?: string;
}
