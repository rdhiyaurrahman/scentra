"use client";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "scentra_token";
const USER_KEY = "scentra_user";

export type Role = "cs" | "owner";

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
}

export interface Source {
  type: string;
  label: string;
}

export interface SuggestedReply {
  id: number;
  reply_text: string;
  knowledge_sources: Source[];
  needs_verification: boolean;
  verification_reason: string | null;
  copied_at: string | null;
}

export interface Classification {
  intent: string;
  priority: string;
  all_intents: string[];
  rule_version: string;
  corrected_by: number | null;
}

export interface ConversationSummary {
  id: number;
  marketplace_code: "shopee" | "tiktok" | "lazada";
  customer_name: string;
  external_reference: string | null;
  status: string;
  priority: string;
  intent: string;
  assigned_user_id: number | null;
  assigned_user_name: string | null;
  updated_at: string;
  created_at: string;
  last_message: string;
  needs_verification: boolean;
}

export interface ConversationMessage {
  id: number;
  sender_type: "customer" | "internal_note" | "cs_action";
  message_text: string;
  captured_at: string;
  marketplace_message_time: string | null;
  source: string;
  author_name: string | null;
  classification: Classification | null;
  suggested_reply: SuggestedReply | null;
}

export interface ConversationDetail extends ConversationSummary {
  product_hint: string | null;
  messages: ConversationMessage[];
  events: {
    id: number;
    event_type: string;
    detail: string;
    author_name: string | null;
    created_at: string;
  }[];
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function getUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as User) : null;
}

export function clearSession() {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
  });

  if (res.status === 401 && typeof window !== "undefined") {
    clearSession();
    window.location.href = "/login";
    throw new ApiError("Sesi berakhir.", 401);
  }
  if (!res.ok) {
    let detail = `Permintaan gagal (${res.status}).`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail[0]?.msg ?? detail;
    } catch {
      /* biarkan pesan bawaan */
    }
    throw new ApiError(detail, res.status);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export const api = {
  async login(email: string, password: string) {
    const res = await fetch(`${BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(body.detail ?? "Email atau password salah.", res.status);
    }
    const data = (await res.json()) as { access_token: string; user: User };
    window.localStorage.setItem(TOKEN_KEY, data.access_token);
    window.localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    return data.user;
  },

  users: () => request<User[]>("/api/users"),

  dashboard: () =>
    request<{
      totals: Record<string, number>;
      by_marketplace: Record<string, number>;
      by_intent: Record<string, number>;
      by_status: Record<string, number>;
      high_priority_queue: ConversationSummary[];
      disclaimer: string;
    }>("/api/dashboard"),

  conversations: (params: Record<string, string | number | boolean | undefined>) => {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== "" && v !== false) q.set(k, String(v));
    }
    const qs = q.toString();
    return request<ConversationSummary[]>(`/api/conversations${qs ? `?${qs}` : ""}`);
  },

  conversation: (id: number) => request<ConversationDetail>(`/api/conversations/${id}`),

  checkDuplicate: (marketplace_code: string, external_reference: string) =>
    request<{
      found: boolean;
      conversation_id?: number;
      customer_name?: string;
      status?: string;
    }>(
      `/api/conversations/duplicate?marketplace_code=${encodeURIComponent(
        marketplace_code,
      )}&external_reference=${encodeURIComponent(external_reference)}`,
    ),

  createConversation: (body: Record<string, unknown>) =>
    request<ConversationSummary & { merged_into_existing: boolean }>("/api/conversations", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  addMessage: (id: number, message_text: string) =>
    request(`/api/conversations/${id}/messages`, {
      method: "POST",
      body: JSON.stringify({ message_text }),
    }),

  patchConversation: (id: number, body: Record<string, unknown>) =>
    request(`/api/conversations/${id}`, { method: "PATCH", body: JSON.stringify(body) }),

  correctIntent: (messageId: number, intent: string) =>
    request(`/api/messages/${messageId}/classification`, {
      method: "PATCH",
      body: JSON.stringify({ intent }),
    }),

  editReply: (replyId: number, reply_text: string) =>
    request(`/api/replies/${replyId}`, { method: "PATCH", body: JSON.stringify({ reply_text }) }),

  markCopied: (replyId: number) => request(`/api/replies/${replyId}/copy`, { method: "POST" }),

  addNote: (id: number, note_text: string) =>
    request(`/api/conversations/${id}/notes`, {
      method: "POST",
      body: JSON.stringify({ note_text }),
    }),

  addAction: (id: number, action_text: string) =>
    request(`/api/conversations/${id}/actions`, {
      method: "POST",
      body: JSON.stringify({ action_text }),
    }),

  knowledge: () =>
    request<{
      faqs: { id: number; question: string; answer: string; keywords: string[] }[];
      products: {
        id: number;
        name: string;
        aliases: string[];
        variants: {
          id: number;
          variant_name: string;
          sku: string;
          quantity: number | null;
          stock_updated_at: string | null;
          is_stale: boolean;
        }[];
      }[];
      shipping_rules: {
        marketplace_code: string;
        rule_text: string | null;
        cutoff_time: string | null;
        updated_at: string;
      }[];
      escalation_rules: { condition: string; action: string }[];
      marketplaces: { code: string; name: string }[];
    }>("/api/knowledge"),
};

/* ---------------------------------------------------------------------------
   Masalah 2 — profitabilitas produk
   Nilai uang berupa bilangan bulat rupiah. Field bernilai null berarti
   "belum diketahui", bukan nol.
--------------------------------------------------------------------------- */

export interface ProfitBucket {
  key: string;
  label: string;
  transactions: number;
  complete_transactions: number;
  incomplete_transactions: number;
  complete: boolean;
  units_sold: number;
  units_returned: number;
  gross_sales: number;
  returned_amount: number;
  net_sales: number;
  net_sales_complete: number;
  commission: number;
  voucher: number;
  shipping: number;
  cogs: number;
  profit: number;
  margin_pct: number | null;
  missing_reasons: string[];
}

export interface ProfitReport {
  period: { start: string | null; end: string | null; marketplace: string | null };
  overall: ProfitBucket;
  by_product: ProfitBucket[];
  by_marketplace: ProfitBucket[];
  data_complete: boolean;
  note: string;
}

export interface ProfitTransaction {
  id: number;
  external_id: string;
  marketplace_code: string;
  product_label: string;
  sku: string;
  order_date: string;
  quantity: number;
  returned_quantity: number;
  gross_sales: number;
  returned_amount: number;
  net_sales: number;
  commission: number | null;
  voucher: number | null;
  shipping: number | null;
  cogs: number | null;
  profit: number | null;
  margin_pct: number | null;
  complete: boolean;
  missing: string[];
}

export interface CostSettings {
  product_costs: {
    variant_id: number;
    sku: string;
    product_name: string;
    variant_name: string;
    unit_cost: number | null;
    updated_at: string | null;
  }[];
  marketplace_fees: {
    marketplace_code: string;
    commission_bp: number | null;
    service_fee_bp: number | null;
    updated_at: string | null;
  }[];
}

function profitQuery(params: Record<string, string | number | boolean | undefined>) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "" && v !== false) q.set(k, String(v));
  }
  const qs = q.toString();
  return qs ? `?${qs}` : "";
}

export const profitApi = {
  report: (params: { start?: string; marketplace?: string }) =>
    request<ProfitReport>(`/api/profit/report${profitQuery(params)}`),

  transactions: (params: {
    start?: string;
    marketplace?: string;
    sku?: string;
    only_incomplete?: boolean;
  }) => request<ProfitTransaction[]>(`/api/profit/transactions${profitQuery(params)}`),

  costSettings: () => request<CostSettings>("/api/profit/cost-settings"),

  async importCsv(file: File) {
    const form = new FormData();
    form.append("file", file);
    const token = getToken();
    const res = await fetch(`${BASE}/api/profit/transactions/import`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new ApiError(body.detail ?? "Impor gagal.", res.status);
    return body as { saved: number; failed: number; errors: string[] };
  },
};
