import { useCallback, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import type {
  AgentResponse,
  ChatMessage,
  SSEAgentSelected,
  SessionOut,
} from "../types";

export interface UseChatOptions {
  conversationId: string;
  customerId: number;
}

export interface UseChatReturn {
  messages: ChatMessage[];
  isStreaming: boolean;
  /** Which agent was selected (shown during streaming) */
  activeAgent: string | null;
  error: string | null;
  sessionTitle: string | null;
  sendMessage: (text: string) => Promise<void>;
  loadHistory: () => Promise<void>;
  clearError: () => void;
}

export function useChat({
  conversationId,
  customerId,
}: UseChatOptions): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionTitle, setSessionTitle] = useState<string | null>(null);

  /** ref to the in-progress assistant message id so we can update it by id */
  const streamingIdRef = useRef<string | null>(null);
  /** tracks whether a "done" SSE event was successfully received */
  const doneReceivedRef = useRef(false);

  const loadHistory = useCallback(async () => {
    try {
      const res = await fetch(`/agent/sessions/${conversationId}`);
      if (!res.ok) return; // 404 = no session yet, that's fine
      const session: SessionOut = await res.json();

      if (session.title) setSessionTitle(session.title);

      const loaded: ChatMessage[] = session.messages.map((m) => ({
        id: String(m.id),
        role: m.role,
        content: m.content,
        meta:
          m.role === "assistant" && m.agent_used
            ? {
                selected_agent: m.agent_used,
                intent: m.intent ?? "",
                confidence: 0,
                tools_used: m.tools_used ?? [],
                citations: [],
                guardrail_triggered: false,
                safe: true,
              }
            : undefined,
      }));
      setMessages(loaded);
    } catch {
      // silently ignore — history is best-effort
    }
  }, [conversationId]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (isStreaming) return;
      setError(null);
      doneReceivedRef.current = false;

      // Append the user message immediately
      const userMsg: ChatMessage = {
        id: uuidv4(),
        role: "user",
        content: text,
      };
      setMessages((prev) => [...prev, userMsg]);

      // Placeholder assistant message that will be filled by SSE chunks
      const assistantId = uuidv4();
      streamingIdRef.current = assistantId;
      const placeholderMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        streaming: true,
      };
      setMessages((prev) => [...prev, placeholderMsg]);
      setIsStreaming(true);
      setActiveAgent(null);

      try {
        const res = await fetch("/agent/respond/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            customer_id: customerId,
            conversation_id: conversationId,
            message: text,
          }),
        });

        if (!res.ok || !res.body) {
          throw new Error(`Server error: ${res.status} ${res.statusText}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          // Normalize both \r\n (Windows/sse_starlette) and \r to plain \n
          // so that SSE frame splitting on "\n\n" works regardless of server OS
          const normalized = buffer.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
          const parts = normalized.split("\n\n");
          // Keep the last incomplete frame in the buffer (already normalized)
          buffer = parts.pop() ?? "";

          for (const part of parts) {
            const lines = part.split("\n");
            let eventName = "message";
            let dataStr = "";

            for (const line of lines) {
              if (line.startsWith("event: ")) {
                eventName = line.slice(7).trim();
              } else if (line.startsWith("data: ")) {
                // Append (handles multi-line data fields per SSE spec)
                dataStr += (dataStr ? "\n" : "") + line.slice(6);
              }
            }

            if (!dataStr) continue;

            if (eventName === "agent_selected") {
              const payload: SSEAgentSelected = JSON.parse(dataStr);
              setActiveAgent(payload.selected_agent);
            } else if (eventName === "answer_chunk") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        content: m.content + (m.content ? " " : "") + dataStr,
                      }
                    : m
                )
              );
            } else if (eventName === "done") {
              doneReceivedRef.current = true;
              const full: AgentResponse = JSON.parse(dataStr);
              if (full.session_title) setSessionTitle(full.session_title);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        content: full.answer,
                        streaming: false,
                        meta: {
                          selected_agent: full.selected_agent,
                          intent: full.intent,
                          confidence: full.confidence,
                          tools_used: full.tools_used,
                          citations: full.citations,
                          guardrail_triggered:
                            full.guardrail_result.guardrail_triggered,
                          safe: full.guardrail_result.safe,
                        },
                      }
                    : m
                )
              );
            } else if (eventName === "error") {
              const payload = JSON.parse(dataStr);
              throw new Error(payload.detail ?? "Unknown server error");
            }
          }
        }

        // Fallback: if the "done" event was never received (e.g. proxy buffered
        // all chunks into a single read that our parser missed), sync from DB.
        if (!doneReceivedRef.current) {
          await loadHistory();
        }
      } catch (err) {
        console.error("[useChat] SSE error:", err);
        const msg = err instanceof Error ? err.message : String(err);
        setError(msg);
        // Try to recover via DB rather than silently removing the placeholder
        await loadHistory();
      } finally {
        setIsStreaming(false);
        setActiveAgent(null);
        streamingIdRef.current = null;
      }
    },
    [conversationId, customerId, isStreaming, loadHistory]
  );

  return {
    messages,
    isStreaming,
    activeAgent,
    error,
    sessionTitle,
    sendMessage,
    loadHistory,
    clearError: () => setError(null),
  };
}
