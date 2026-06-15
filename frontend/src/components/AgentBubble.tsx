import type { ChatMessage } from "../types";

interface AgentBubbleProps {
  message: ChatMessage;
}

const AGENT_COLORS: Record<string, string> = {
  CatalogAgent: "bg-violet-500/20 text-violet-300 border-violet-500/30",
  SubscriptionAgent: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  RentalHistoryAgent: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
  KnowledgeAgent: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  HumanHandoffAgent: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  TriageAgent: "bg-slate-500/20 text-slate-300 border-slate-500/30",
};

function agentColor(name: string): string {
  return AGENT_COLORS[name] ?? "bg-slate-500/20 text-slate-300 border-slate-500/30";
}

function ConfidencePill({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 80
      ? "text-emerald-400"
      : pct >= 60
      ? "text-amber-400"
      : "text-rose-400";
  return (
    <span className={`text-xs font-medium ${color}`}>{pct}% confidence</span>
  );
}

function TypingDots() {
  return (
    <span className="inline-flex gap-1 items-center">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </span>
  );
}

export function AgentBubble({ message }: AgentBubbleProps) {
  const { content, streaming, meta } = message;

  return (
    <div className="flex justify-start px-4 py-1">
      <div className="max-w-[80%] space-y-2">
        {/* Agent label */}
        {meta?.selected_agent && (
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${agentColor(
                meta.selected_agent
              )}`}
            >
              {meta.selected_agent.replace("Agent", "")}
            </span>
            {meta.confidence > 0 && (
              <ConfidencePill value={meta.confidence} />
            )}
            {meta.guardrail_triggered && (
              <span
                title="Guardrail was triggered"
                className="text-xs text-amber-400 flex items-center gap-1"
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
                    d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
                  />
                </svg>
                Guardrail
              </span>
            )}
          </div>
        )}

        {/* Message bubble */}
        <div className="bg-slate-800 border border-slate-700/60 text-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed shadow-lg">
          {content ? (
            <p className="whitespace-pre-wrap">{content}</p>
          ) : streaming ? (
            <TypingDots />
          ) : null}
          {streaming && content && (
            <span className="inline-block w-0.5 h-3.5 bg-indigo-400 ml-0.5 animate-pulse align-middle" />
          )}
        </div>

        {/* Tools used */}
        {meta && meta.tools_used.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-1">
            {meta.tools_used.map((tool) => (
              <span
                key={tool}
                className="text-xs bg-slate-700/60 text-slate-400 border border-slate-600/50 rounded px-2 py-0.5 font-mono"
              >
                {tool.includes("-") ? tool.split("-").pop() : tool}
              </span>
            ))}
          </div>
        )}

        {/* Citations */}
        {meta && meta.citations.length > 0 && (
          <div className="px-1 space-y-1">
            {meta.citations.map((c, i) => (
              <p key={i} className="text-xs text-slate-500 italic">
                [{i + 1}] {c}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
