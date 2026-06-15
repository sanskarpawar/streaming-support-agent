import { useEffect, useState } from "react";

interface StatusBarProps {
  title: string | null;
  customerId: number;
  onCustomerIdChange: (id: number) => void;
}

type HealthStatus = "checking" | "ok" | "error";

export function StatusBar({ title, customerId, onCustomerIdChange }: StatusBarProps) {
  const [health, setHealth] = useState<HealthStatus>("checking");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(customerId));

  useEffect(() => {
    async function check() {
      try {
        const res = await fetch("/health");
        setHealth(res.ok ? "ok" : "error");
      } catch {
        setHealth("error");
      }
    }
    check();
    const id = setInterval(check, 30_000);
    return () => clearInterval(id);
  }, []);

  // Keep draft in sync when customerId prop changes externally
  useEffect(() => {
    setDraft(String(customerId));
  }, [customerId]);

  function commitEdit() {
    const parsed = parseInt(draft, 10);
    if (!isNaN(parsed) && parsed > 0) {
      onCustomerIdChange(parsed);
    } else {
      setDraft(String(customerId));
    }
    setEditing(false);
  }

  const healthDot =
    health === "ok"
      ? "bg-emerald-400"
      : health === "error"
      ? "bg-rose-500 animate-pulse"
      : "bg-amber-400 animate-pulse";

  const healthLabel =
    health === "ok"
      ? "API online"
      : health === "error"
      ? "API offline"
      : "Connecting…";

  return (
    <header className="flex items-center justify-between px-5 py-3 border-b border-slate-800 bg-slate-950/95 backdrop-blur-sm flex-shrink-0 gap-4">
      {/* Left: brand + title */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-900/40">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="w-5 h-5 text-white"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
            />
          </svg>
        </div>

        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-100 text-sm leading-none tracking-tight">
              Streaming Support
            </span>
            <span
              className={`w-2 h-2 rounded-full flex-shrink-0 ${healthDot}`}
              title={healthLabel}
            />
          </div>
          <p className="text-xs text-slate-400 mt-0.5 truncate max-w-xs font-medium">
            {title ?? (
              <span className="text-slate-600 font-normal">
                AI-powered customer support
              </span>
            )}
          </p>
        </div>
      </div>

      {/* Right: customer ID picker */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <div className="flex items-center gap-1.5 bg-slate-800/80 border border-slate-700/60 rounded-lg px-3 py-1.5">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="w-3.5 h-3.5 text-slate-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
            />
          </svg>
          {editing ? (
            <input
              autoFocus
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onBlur={commitEdit}
              onKeyDown={(e) => {
                if (e.key === "Enter") commitEdit();
                if (e.key === "Escape") {
                  setDraft(String(customerId));
                  setEditing(false);
                }
              }}
              className="w-14 text-xs bg-transparent border-b border-indigo-500 text-slate-100 outline-none text-center pb-0.5"
            />
          ) : (
            <button
              onClick={() => {
                setDraft(String(customerId));
                setEditing(true);
              }}
              title="Click to change customer ID (starts a new conversation)"
              className="text-xs text-slate-300 hover:text-slate-100 transition-colors font-medium min-w-[2rem] text-center"
            >
              Customer #{customerId}
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
