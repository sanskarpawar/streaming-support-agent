import type { UseChatReturn } from "../hooks/useChat";
import { InputBar } from "./InputBar";
import { MessageList } from "./MessageList";

interface ChatWindowProps {
  chat: UseChatReturn;
}

export function ChatWindow({ chat }: ChatWindowProps) {
  const {
    messages,
    isStreaming,
    activeAgent,
    error,
    sendMessage,
    clearError,
  } = chat;

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Error banner */}
      {error && (
        <div className="mx-4 mt-3 flex items-start gap-3 bg-rose-950/60 border border-rose-500/40 rounded-xl px-4 py-3">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="text-sm text-rose-300 flex-1">{error}</p>
          <button
            onClick={clearError}
            className="text-rose-400 hover:text-rose-200 text-lg leading-none"
          >
            ×
          </button>
        </div>
      )}

      <MessageList
        messages={messages}
        isStreaming={isStreaming}
        activeAgent={activeAgent}
        onSuggestion={sendMessage}
      />

      <InputBar onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}
