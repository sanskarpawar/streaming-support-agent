import { useEffect, useRef } from "react";
import type { ChatMessage } from "../types";
import { AgentBubble } from "./AgentBubble";
import { UserBubble } from "./UserBubble";

const SUGGESTION_CHIPS = [
  "What films are available?",
  "Check my subscription",
  "View my rental history",
  "I need help with billing",
];

interface MessageListProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  activeAgent: string | null;
  onSuggestion: (text: string) => void;
}

export function MessageList({
  messages,
  isStreaming,
  activeAgent,
  onSuggestion,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-5 px-6 text-center select-none">
        {/* Icon */}
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-600/30 to-violet-600/20 border border-indigo-500/30 flex items-center justify-center shadow-xl shadow-indigo-900/20">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="w-8 h-8 text-indigo-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
            />
          </svg>
        </div>

        {/* Headline */}
        <div>
          <p className="text-slate-200 font-semibold text-xl tracking-tight">
            How can I help you today?
          </p>
          <p className="text-slate-500 text-sm mt-1.5 max-w-xs leading-relaxed">
            Ask about your subscription, film catalog, rental history, or any streaming support question.
          </p>
        </div>

        {/* Clickable suggestion chips */}
        <div className="flex flex-wrap gap-2 justify-center">
          {SUGGESTION_CHIPS.map((hint) => (
            <button
              key={hint}
              onClick={() => onSuggestion(hint)}
              className="text-sm bg-slate-800/80 hover:bg-slate-700 border border-slate-700 hover:border-indigo-500/50 rounded-full px-4 py-2 text-slate-300 hover:text-slate-100 transition-all duration-150 cursor-pointer"
            >
              {hint}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto scrollbar-thin py-4 space-y-2">
      {messages.map((msg) =>
        msg.role === "user" ? (
          <UserBubble key={msg.id} content={msg.content} />
        ) : (
          <AgentBubble key={msg.id} message={msg} />
        )
      )}

      {/* "Routing to..." status during the LLM wait, before agent_selected arrives */}
      {isStreaming && !activeAgent && (
        <div className="flex justify-start px-5 py-1">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <svg
              className="w-3.5 h-3.5 animate-spin"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v8H4z"
              />
            </svg>
            <span className="italic">Processing your request…</span>
          </div>
        </div>
      )}

      {isStreaming && activeAgent && (
        <div className="flex justify-start px-5 py-1">
          <span className="text-xs text-indigo-400 italic animate-pulse font-medium">
            Routing to {activeAgent}…
          </span>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
