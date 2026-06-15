import { useEffect, useRef, useState } from "react";
import type { SessionPatch, SessionSummary } from "../types";
import type { UseSessionsReturn } from "../hooks/useSessions";

interface SessionSidebarProps {
  sessions: UseSessionsReturn;
  activeId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

interface SessionItemProps {
  session: SessionSummary;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onRename: (patch: SessionPatch) => void;
}

function SessionItem({
  session,
  isActive,
  onSelect,
  onDelete,
  onRename,
}: SessionItemProps) {
  const [hovering, setHovering] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(session.title ?? "");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.select();
  }, [editing]);

  function commitRename() {
    const trimmed = draft.trim();
    if (trimmed && trimmed !== session.title) {
      onRename({ title: trimmed });
    }
    setEditing(false);
  }

  const displayTitle = session.title ?? `Session ${session.id.slice(0, 8)}`;

  return (
    <div
      className={`group relative flex items-start gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-colors ${
        isActive
          ? "bg-indigo-600/20 border border-indigo-500/40"
          : "hover:bg-slate-800/60 border border-transparent"
      }`}
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
      onClick={() => !editing && onSelect()}
    >
      {/* Session icon */}
      <div
        className={`flex-shrink-0 w-1.5 h-1.5 rounded-full mt-1.5 ${
          isActive ? "bg-indigo-400" : "bg-slate-600"
        }`}
      />

      <div className="flex-1 min-w-0">
        {editing ? (
          <input
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commitRename}
            onKeyDown={(e) => {
              if (e.key === "Enter") commitRename();
              if (e.key === "Escape") {
                setDraft(session.title ?? "");
                setEditing(false);
              }
            }}
            onClick={(e) => e.stopPropagation()}
            className="w-full text-xs bg-slate-700 border border-indigo-500 rounded px-1.5 py-0.5 text-slate-100 outline-none"
          />
        ) : (
          <p
            className={`text-xs font-medium truncate leading-snug ${
              isActive ? "text-slate-100" : "text-slate-300"
            }`}
            onDoubleClick={(e) => {
              e.stopPropagation();
              setDraft(session.title ?? "");
              setEditing(true);
            }}
            title="Double-click to rename"
          >
            {displayTitle}
          </p>
        )}
        <p className="text-[10px] text-slate-600 mt-0.5">
          {relativeTime(session.updated_at)}
        </p>
      </div>

      {/* Delete button — shown on hover, not while editing */}
      {hovering && !editing && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          title="Delete session"
          className="flex-shrink-0 w-5 h-5 flex items-center justify-center rounded text-slate-500 hover:text-rose-400 hover:bg-rose-400/10 transition-colors"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="w-3 h-3"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
        </button>
      )}
    </div>
  );
}

export function SessionSidebar({
  sessions,
  activeId,
  onSelect,
  onNew,
}: SessionSidebarProps) {
  const { sessions: list, loading, fetchSessions, deleteSession, patchSession } = sessions;

  return (
    <aside className="w-60 flex-shrink-0 flex flex-col border-r border-slate-800 bg-slate-950/80 overflow-hidden">
      {/* Header */}
      <div className="px-3 pt-3 pb-2 flex-shrink-0">
        <button
          onClick={onNew}
          className="w-full flex items-center justify-center gap-2 text-xs font-medium text-slate-300 hover:text-slate-100 bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-indigo-500/50 rounded-lg px-3 py-2 transition-all duration-150"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="w-3.5 h-3.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          New conversation
        </button>
      </div>

      {/* Section label + refresh */}
      <div className="flex items-center justify-between px-3 py-1.5 flex-shrink-0">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-600">
          Conversations
        </span>
        <button
          onClick={fetchSessions}
          title="Refresh sessions"
          className="text-slate-600 hover:text-slate-400 transition-colors"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className={`w-3 h-3 ${loading ? "animate-spin" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
        </button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto scrollbar-thin px-2 pb-2 space-y-0.5">
        {loading && list.length === 0 && (
          <p className="text-xs text-slate-600 text-center py-6">Loading…</p>
        )}

        {!loading && list.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 gap-2 text-center px-2">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="w-8 h-8 text-slate-700"
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
            <p className="text-xs text-slate-600">No conversations yet.</p>
            <p className="text-[10px] text-slate-700">
              Click "New conversation" to start.
            </p>
          </div>
        )}

        {list.map((session) => (
          <SessionItem
            key={session.id}
            session={session}
            isActive={session.id === activeId}
            onSelect={() => onSelect(session.id)}
            onDelete={() => deleteSession(session.id)}
            onRename={(patch) => patchSession(session.id, patch)}
          />
        ))}
      </div>
    </aside>
  );
}
