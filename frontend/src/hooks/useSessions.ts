import { useCallback, useEffect, useRef, useState } from "react";
import type { SessionCreate, SessionPatch, SessionSummary, SessionOut } from "../types";

export interface UseSessionsReturn {
  sessions: SessionSummary[];
  loading: boolean;
  error: string | null;
  fetchSessions: () => Promise<void>;
  createSession: () => Promise<SessionSummary | null>;
  deleteSession: (id: string) => Promise<void>;
  patchSession: (id: string, patch: SessionPatch) => Promise<SessionSummary | null>;
}

export function useSessions(customerId: number): UseSessionsReturn {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Keep customerId in a ref so fetchSessions callback is stable
  const customerIdRef = useRef(customerId);
  useEffect(() => {
    customerIdRef.current = customerId;
  }, [customerId]);

  const fetchSessions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `/agent/sessions?customer_id=${customerIdRef.current}`
      );
      if (!res.ok) throw new Error(`Failed to load sessions: ${res.status}`);
      const data: SessionSummary[] = await res.json();
      setSessions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-fetch whenever customerId changes
  useEffect(() => {
    fetchSessions();
  }, [customerId, fetchSessions]);

  const createSession = useCallback(async (): Promise<SessionSummary | null> => {
    try {
      const body: SessionCreate = { customer_id: customerIdRef.current };
      const res = await fetch("/agent/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`Failed to create session: ${res.status}`);
      // POST returns full SessionOut; we store as SessionSummary (same shape minus messages)
      const created: SessionOut = await res.json();
      const summary: SessionSummary = {
        id: created.id,
        customer_id: created.customer_id,
        title: created.title,
        status: created.status,
        created_at: created.created_at,
        updated_at: created.updated_at,
      };
      setSessions((prev) => [summary, ...prev]);
      return summary;
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      return null;
    }
  }, []);

  const deleteSession = useCallback(async (id: string): Promise<void> => {
    // Optimistically remove from UI
    setSessions((prev) => prev.filter((s) => s.id !== id));
    try {
      const res = await fetch(`/agent/sessions/${id}`, { method: "DELETE" });
      if (!res.ok) {
        // Rollback on failure
        await fetchSessions();
        throw new Error(`Failed to delete session: ${res.status}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [fetchSessions]);

  const patchSession = useCallback(
    async (id: string, patch: SessionPatch): Promise<SessionSummary | null> => {
      // Optimistically update title in state
      if (patch.title !== undefined) {
        setSessions((prev) =>
          prev.map((s) => (s.id === id ? { ...s, title: patch.title ?? s.title } : s))
        );
      }
      try {
        const res = await fetch(`/agent/sessions/${id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(patch),
        });
        if (!res.ok) throw new Error(`Failed to update session: ${res.status}`);
        const updated: SessionSummary = await res.json();
        setSessions((prev) => prev.map((s) => (s.id === id ? updated : s)));
        return updated;
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        await fetchSessions(); // rollback
        return null;
      }
    },
    [fetchSessions]
  );

  return { sessions, loading, error, fetchSessions, createSession, deleteSession, patchSession };
}
