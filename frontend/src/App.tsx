import { useCallback, useEffect, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import { ChatWindow } from "./components/ChatWindow";
import { SessionSidebar } from "./components/SessionSidebar";
import { StatusBar } from "./components/StatusBar";
import { useChat } from "./hooks/useChat";
import { useSessions } from "./hooks/useSessions";

const STORAGE_KEYS = {
  conversationId: "ssa_conversation_id",
  customerId: "ssa_customer_id",
};

function getStoredConversationId(): string {
  return localStorage.getItem(STORAGE_KEYS.conversationId) ?? uuidv4();
}

function getStoredCustomerId(): number {
  const raw = localStorage.getItem(STORAGE_KEYS.customerId);
  const parsed = raw ? parseInt(raw, 10) : NaN;
  return isNaN(parsed) ? 1 : parsed;
}

export default function App() {
  const [conversationId, setConversationId] = useState<string>(
    getStoredConversationId
  );
  const [customerId, setCustomerId] = useState<number>(getStoredCustomerId);

  // Persist to localStorage
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.conversationId, conversationId);
  }, [conversationId]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.customerId, String(customerId));
  }, [customerId]);

  const chat = useChat({ conversationId, customerId });
  const sessionsMgr = useSessions(customerId);

  // Restore chat history when conversation changes
  useEffect(() => {
    chat.loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  // After each completed turn, refresh the session list so titles update
  useEffect(() => {
    if (!chat.isStreaming) {
      sessionsMgr.fetchSessions();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chat.isStreaming]);

  const handleNewConversation = useCallback(async () => {
    const created = await sessionsMgr.createSession();
    if (created) {
      setConversationId(created.id);
    } else {
      // Fallback: generate locally if POST failed
      setConversationId(uuidv4());
    }
  }, [sessionsMgr]);

  const handleSelectSession = useCallback(
    (id: string) => {
      if (id !== conversationId) {
        setConversationId(id);
      }
    },
    [conversationId]
  );

  const handleDeleteSession = useCallback(
    async (id: string) => {
      await sessionsMgr.deleteSession(id);
      if (id === conversationId) {
        // Switch to the most recent remaining session, or create a new one
        const remaining = sessionsMgr.sessions.filter((s) => s.id !== id);
        if (remaining.length > 0) {
          setConversationId(remaining[0].id);
        } else {
          const created = await sessionsMgr.createSession();
          setConversationId(created?.id ?? uuidv4());
        }
      }
    },
    [conversationId, sessionsMgr]
  );

  // When customer ID changes, reset to a fresh conversation
  const handleCustomerIdChange = useCallback(
    async (newId: number) => {
      setCustomerId(newId);
      const created = await sessionsMgr.createSession();
      setConversationId(created?.id ?? uuidv4());
    },
    [sessionsMgr]
  );

  return (
    <div className="h-screen flex flex-col bg-slate-950 overflow-hidden">
      <StatusBar
        title={chat.sessionTitle}
        customerId={customerId}
        onCustomerIdChange={handleCustomerIdChange}
      />

      {/* Body: sidebar + chat panel */}
      <div className="flex-1 flex flex-row min-h-0">
        <SessionSidebar
          sessions={{
            ...sessionsMgr,
            deleteSession: handleDeleteSession,
          }}
          activeId={conversationId}
          onSelect={handleSelectSession}
          onNew={handleNewConversation}
        />

        <ChatWindow chat={chat} />
      </div>
    </div>
  );
}
