"use client";

import { useState, useRef, useEffect, useCallback, Suspense, type KeyboardEvent } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Bot, User, Trash2, ChevronDown, X } from "lucide-react";
import { cn, href } from "@/lib/utils";
import { VoiceInput } from "@/components/VoiceInput";
import { useChat, type ChatMessage } from "@/hooks/useChat";

/* -------------------------------------------------------------------------- */
/*  Constants                                                                  */
/* -------------------------------------------------------------------------- */

const SUGGESTIONS = [
  "What's interesting today?",
  "Why NVDA not AMD?",
  "How did last week go?",
  "Build me a momentum strategy",
];

const CITATION_ICONS: Record<string, string> = {
  "Quant Engine": "\u{1F4CA}",
  "Sentiment Agent": "\u{1F4AC}",
  "Technical Agent": "\u{1F4C8}",
  "Risk Model": "\u{1F6E1}\u{FE0F}",
  "Execution Model": "\u{26A1}",
  "Execution Log": "\u{1F4CB}",
  "Factor Library": "\u{1F9EA}",
  "Backtest Engine": "\u{2699}\u{FE0F}",
  "Portfolio Tracker": "\u{1F4BC}",
  System: "\u{2139}\u{FE0F}",
};

/* -------------------------------------------------------------------------- */
/*  Typing Indicator                                                           */
/* -------------------------------------------------------------------------- */

function TypingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      className="flex items-start gap-3 px-4"
    >
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-500/10 text-violet-400">
        <Bot className="h-4 w-4" />
      </div>
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 px-4 py-3 backdrop-blur-sm">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-zinc-400">Researching</span>
          <div className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <motion.span
                key={i}
                className="block h-1.5 w-1.5 rounded-full bg-violet-400"
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{
                  duration: 1.2,
                  repeat: Infinity,
                  delay: i * 0.2,
                }}
              />
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Citation Badge                                                             */
/* -------------------------------------------------------------------------- */

function CitationBadge({ label }: { label: string }) {
  const [expanded, setExpanded] = useState(false);
  const icon = CITATION_ICONS[label] || "\u{1F50D}";

  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-all",
          "border-zinc-700 bg-zinc-800/80 text-zinc-300 hover:border-violet-500/50 hover:bg-violet-500/10 hover:text-violet-300"
        )}
      >
        <span>{icon}</span>
        <span>{label}</span>
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="absolute bottom-full left-0 z-50 mb-2 w-56 rounded-lg border border-zinc-700 bg-zinc-900 p-3 shadow-xl"
          >
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-zinc-200">
                {icon} {label}
              </p>
              <button
                type="button"
                onClick={() => setExpanded(false)}
                className="text-zinc-500 hover:text-zinc-300"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
            <p className="mt-1.5 text-xs leading-relaxed text-zinc-400">
              Data source verified. This claim is backed by the {label} pipeline
              with high confidence.
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Action Button                                                              */
/* -------------------------------------------------------------------------- */

function ActionButton({ label, onAction }: { label: string; onAction: (action: string) => void }) {
  return (
    <button
      type="button"
      onClick={() => onAction(label)}
      className={cn(
        "rounded-lg border border-violet-500/30 px-3 py-1.5 text-xs font-medium text-violet-300 transition-all",
        "hover:border-violet-500 hover:bg-violet-500/10 hover:text-violet-200",
        "active:bg-violet-500/20"
      )}
    >
      {label}
    </button>
  );
}

/* -------------------------------------------------------------------------- */
/*  Inline Metric Pill                                                         */
/* -------------------------------------------------------------------------- */

function renderContentWithMetrics(content: string) {
  // Parse markdown-style bold and detect metric patterns
  const lines = content.split("\n");

  return lines.map((line, lineIdx) => {
    if (!line.trim()) {
      return <br key={lineIdx} />;
    }

    // Detect numbered list items
    const listMatch = line.match(/^(\d+)\.\s+(.+)/);
    if (listMatch) {
      return (
        <div key={lineIdx} className="flex gap-2 py-0.5">
          <span className="shrink-0 font-mono text-xs text-violet-400/60">
            {listMatch[1]}.
          </span>
          <span>{parseInline(listMatch[2])}</span>
        </div>
      );
    }

    return (
      <p key={lineIdx} className="py-0.5">
        {parseInline(line)}
      </p>
    );
  });
}

function parseInline(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  // Split on bold markers and metric patterns
  const regex = /(\*\*[^*]+\*\*)|([+-]?\d+\.?\d*%\s*(?:win|avg|return|move|edge|hit rate|slippage))|([+-]?\d+\.?\d*x\s*(?:edge|ATR))/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    // Text before match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    if (match[1]) {
      // Bold text
      parts.push(
        <strong key={match.index} className="font-semibold text-zinc-100">
          {match[1].slice(2, -2)}
        </strong>
      );
    } else if (match[2] || match[3]) {
      // Metric pill
      const metric = match[2] || match[3];
      const isPositive = metric.startsWith("+") || !metric.startsWith("-");
      parts.push(
        <span
          key={match.index}
          className={cn(
            "mx-0.5 inline-flex rounded-md px-1.5 py-0.5 font-mono text-xs font-medium",
            isPositive
              ? "bg-emerald-500/10 text-emerald-400"
              : "bg-red-500/10 text-red-400"
          )}
        >
          {metric}
        </span>
      );
    }

    lastIndex = match.index + match[0].length;
  }

  // Remaining text
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? parts : [text];
}

/* -------------------------------------------------------------------------- */
/*  ChatMessage Component                                                      */
/* -------------------------------------------------------------------------- */

function ChatMessageBubble({
  message,
  onAction,
}: {
  message: ChatMessage;
  onAction: (action: string) => void;
}) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, x: isUser ? 24 : -24 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, ease: [0, 0, 0.2, 1] }}
      className={cn("flex gap-3 px-4", isUser ? "flex-row-reverse" : "flex-row")}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
          isUser
            ? "bg-violet-500/10 text-violet-400"
            : "bg-violet-500/10 text-violet-400"
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Bubble */}
      <div
        className={cn(
          "group relative max-w-2xl rounded-xl border px-4 py-3 transition-shadow hover:shadow-lg hover:shadow-black/20",
          isUser
            ? "border-violet-500/20 bg-violet-500/10"
            : "border-zinc-800 bg-zinc-900/50 backdrop-blur-sm"
        )}
      >
        {/* Label */}
        <p
          className={cn(
            "mb-1.5 text-xs font-semibold tracking-wide",
            isUser ? "text-right text-violet-400" : "text-violet-400"
          )}
        >
          {isUser ? "You" : "\u{1F916} Research Director"}
        </p>

        {/* Content */}
        <div className="text-sm leading-relaxed text-zinc-300">
          {isUser ? message.content : renderContentWithMetrics(message.content)}
        </div>

        {/* Citations */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {message.citations.map((citation) => (
              <CitationBadge key={citation} label={citation} />
            ))}
          </div>
        )}

        {/* Actions */}
        {!isUser && message.actions && message.actions.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2 border-t border-zinc-800/50 pt-3">
            {message.actions.map((action) => (
              <ActionButton key={action} label={action} onAction={onAction} />
            ))}
          </div>
        )}

        {/* Timestamp */}
        <p
          className={cn(
            "mt-2 text-[10px] text-zinc-600 opacity-0 transition-opacity group-hover:opacity-100",
            isUser && "text-right"
          )}
        >
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      </div>
    </motion.div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Suggestion Chips                                                           */
/* -------------------------------------------------------------------------- */

function SuggestionChips({
  onSelect,
  visible,
}: {
  onSelect: (suggestion: string) => void;
  visible: boolean;
}) {
  if (!visible) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      transition={{ duration: 0.25 }}
      className="flex flex-wrap gap-2 px-4 pb-2"
    >
      {SUGGESTIONS.map((suggestion) => (
        <button
          key={suggestion}
          type="button"
          onClick={() => onSelect(suggestion)}
          className={cn(
            "rounded-full border border-zinc-800 bg-zinc-900/50 px-3.5 py-1.5 text-xs font-medium text-zinc-400 transition-all",
            "hover:border-violet-500/40 hover:bg-violet-500/5 hover:text-violet-300",
            "active:bg-violet-500/10"
          )}
        >
          {suggestion}
        </button>
      ))}
    </motion.div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Scroll-to-Bottom Button                                                    */
/* -------------------------------------------------------------------------- */

function ScrollToBottomButton({ onClick, visible }: { onClick: () => void; visible: boolean }) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.button
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.8 }}
          type="button"
          onClick={onClick}
          className={cn(
            "absolute bottom-2 left-1/2 z-10 -translate-x-1/2 rounded-full",
            "border border-zinc-700 bg-zinc-900/90 p-2 shadow-lg backdrop-blur-sm",
            "text-zinc-400 hover:border-violet-500/50 hover:text-violet-300 transition-colors"
          )}
        >
          <ChevronDown className="h-4 w-4" />
        </motion.button>
      )}
    </AnimatePresence>
  );
}

/* -------------------------------------------------------------------------- */
/*  Main Page                                                                  */
/* -------------------------------------------------------------------------- */

export default function ChatPage() {
  return (
    <Suspense>
      <ChatPageInner />
    </Suspense>
  );
}

function ChatPageInner() {
  const { messages, send, clear, loading } = useChat();
  const [input, setInput] = useState("");
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const searchParams = useSearchParams();
  const router = useRouter();
  const autoSentRef = useRef(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-send from query param (e.g. ?q=Analyze+D05.SI)
  useEffect(() => {
    const q = searchParams.get("q");
    if (q && !autoSentRef.current && messages.length === 0) {
      autoSentRef.current = true;
      send(q);
    }
  }, [searchParams, messages.length, send]);

  // Auto-focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Track scroll position for scroll-to-bottom button
  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;
    setShowScrollBtn(distanceFromBottom > 100);
  }, []);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;
    setInput("");
    send(trimmed);
    // Reset textarea height
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
    }
  }, [input, loading, send]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const handleSuggestion = useCallback(
    (suggestion: string) => {
      if (loading) return;
      send(suggestion);
    },
    [loading, send]
  );

  const handleAction = useCallback(
    (action: string) => {
      if (loading) return;

      // Route "Run backtest on X" to the backtest page
      const backtestMatch = action.match(/^Run backtest on\s+(.+)$/i);
      if (backtestMatch) {
        const ticker = backtestMatch[1].trim();
        router.push(href(`/backtest?ticker=${encodeURIComponent(ticker)}`));
        return;
      }

      // Route "Compare X with peers" to chat with comparison query
      const compareMatch = action.match(/^Compare\s+(.+?)\s+with peers$/i);
      if (compareMatch) {
        send(`Compare ${compareMatch[1]} with its sector peers — which has the best risk-adjusted returns?`);
        return;
      }

      // Route "Add X to watchlist" — confirm in chat
      const watchlistMatch = action.match(/^Add\s+(.+?)\s+to watchlist$/i);
      if (watchlistMatch) {
        send(`Add ${watchlistMatch[1]} to my watchlist. What key levels should I monitor?`);
        return;
      }

      // Default: send as chat message
      send(action);
    },
    [loading, send, router]
  );

  // Auto-resize textarea
  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setInput(e.target.value);
      const target = e.target;
      target.style.height = "auto";
      target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
    },
    []
  );

  const showSuggestions =
    messages.length === 0 ||
    (messages.length > 0 && messages[messages.length - 1].role === "assistant" && !loading);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="shrink-0 border-b border-zinc-800 px-4 sm:px-6 py-3 sm:py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-zinc-50">Research Chat</h1>
            <p className="text-xs text-zinc-500">Talk to your research analyst</p>
          </div>
          {messages.length > 0 && (
            <motion.button
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              type="button"
              onClick={clear}
              className={cn(
                "flex items-center gap-1.5 rounded-lg border border-zinc-800 px-3 py-1.5 text-xs font-medium text-zinc-500 transition-all",
                "hover:border-red-500/30 hover:bg-red-500/5 hover:text-red-400"
              )}
            >
              <Trash2 className="h-3 w-3" />
              Clear
            </motion.button>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="relative flex-1 overflow-y-auto"
      >
        {messages.length === 0 ? (
          /* Empty State */
          <div className="flex h-full flex-col items-center justify-center px-4">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="text-center"
            >
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-zinc-800 bg-zinc-900/50">
                <Bot className="h-7 w-7 text-violet-400" />
              </div>
              <h2 className="text-lg font-semibold text-zinc-200">
                Research Director
              </h2>
              <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-zinc-500">
                I analyze markets using quantitative signals, sentiment data, and
                technical indicators. Every claim is backed by computation. Ask me
                anything.
              </p>
            </motion.div>
          </div>
        ) : (
          /* Message List */
          <div className="space-y-4 py-4">
            <AnimatePresence initial={false}>
              {messages.map((msg) => (
                <ChatMessageBubble
                  key={msg.id}
                  message={msg}
                  onAction={handleAction}
                />
              ))}
            </AnimatePresence>

            {/* Typing Indicator */}
            <AnimatePresence>{loading && <TypingIndicator />}</AnimatePresence>

            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Scroll to bottom */}
        <ScrollToBottomButton onClick={scrollToBottom} visible={showScrollBtn} />
      </div>

      {/* Input Area */}
      <div className="shrink-0 border-t border-zinc-800 bg-zinc-950/80 px-4 pb-4 pt-3 backdrop-blur-sm">
        {/* Suggestions */}
        <AnimatePresence>
          <SuggestionChips onSelect={handleSuggestion} visible={showSuggestions} />
        </AnimatePresence>

        {/* Input Row */}
        <div className="flex items-end gap-2 sm:gap-3 px-0 sm:px-4">
          <div className="relative flex-1">
            <textarea
              ref={inputRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Ask me anything about the market..."
              rows={1}
              disabled={loading}
              className={cn(
                "w-full resize-none rounded-xl border border-zinc-800 bg-zinc-900/50 px-4 py-3 pr-4 text-sm text-zinc-200",
                "placeholder:text-zinc-600 focus:border-violet-500/50 focus:outline-none focus:ring-1 focus:ring-violet-500/25",
                "disabled:cursor-not-allowed disabled:opacity-50",
                "backdrop-blur-sm transition-colors"
              )}
            />
          </div>
          <VoiceInput
            onInterim={(text) => setInput(text)}
            onFinal={(text) => setInput(text)}
            size="md"
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className={cn(
              "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl transition-all",
              input.trim() && !loading
                ? "bg-violet-500 text-white shadow-lg shadow-violet-500/20 hover:bg-violet-400 active:bg-violet-600"
                : "border border-zinc-800 bg-zinc-900/50 text-zinc-600"
            )}
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
