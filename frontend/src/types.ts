// ── Backend schema types (mirroring app/schemas/response.py) ─────────────────

export interface AgentRequest {
  customer_id: number;
  conversation_id: string;
  message: string;
}

export interface GuardrailResult {
  safe: boolean;
  guardrail_triggered: boolean;
  issues: string[];
  revised_answer: string;
}

export interface AgentResponse {
  conversation_id: string;
  session_title: string | null;
  intent: string;
  selected_agent: string;
  answer: string;
  confidence: number;
  tools_used: string[];
  citations: string[];
  next_action: string;
  guardrail_result: GuardrailResult;
}

export interface MessageOut {
  id: number;
  role: "user" | "assistant";
  content: string;
  agent_used: string | null;
  intent: string | null;
  tools_used: string[] | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface SessionOut {
  id: string;
  customer_id: number;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  messages: MessageOut[];
}

// ── UI-level message shapes ───────────────────────────────────────────────────

export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  /** Only present on assistant messages after streaming completes */
  meta?: {
    selected_agent: string;
    intent: string;
    confidence: number;
    tools_used: string[];
    citations: string[];
    guardrail_triggered: boolean;
    safe: boolean;
  };
  /** True while SSE answer_chunk events are still arriving */
  streaming?: boolean;
}

// ── SSE event payloads ────────────────────────────────────────────────────────

export interface SSEAgentSelected {
  selected_agent: string;
  intent: string;
}

export interface SSEGuardrail {
  safe: boolean;
  triggered: boolean;
}

// ── Session management types (mirrors new backend schemas) ───────────────────

export interface SessionSummary {
  id: string;
  customer_id: number;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface SessionCreate {
  customer_id: number;
  title?: string;
}

export interface SessionPatch {
  title?: string;
  status?: string;
}
