"use client";

import { AnimatePresence, motion } from "framer-motion";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

type Toast = {
  id: number;
  title: string;
  detail?: string;
  tone: "signal" | "insight" | "risk" | "muted";
};

type Ctx = { push: (t: Omit<Toast, "id">) => void };

const ToastCtx = createContext<Ctx>({ push: () => {} });

export function useToast() {
  return useContext(ToastCtx);
}

const TONE_STYLES: Record<Toast["tone"], string> = {
  signal: "border-signal/40 bg-signal/5 text-ink",
  insight: "border-insight/40 bg-insight/5 text-ink",
  risk: "border-risk/40 bg-risk/5 text-ink",
  muted: "border-rule bg-surface-raised text-ink",
};

const TONE_DOT: Record<Toast["tone"], string> = {
  signal: "bg-signal",
  insight: "bg-insight",
  risk: "bg-risk",
  muted: "bg-ink-muted",
};

export function ToasterProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const idRef = useRef(0);

  const push = useCallback((t: Omit<Toast, "id">) => {
    const id = ++idRef.current;
    setToasts((prev) => [...prev, { ...t, id }]);
    // Auto-dismiss after 4s
    setTimeout(() => {
      setToasts((prev) => prev.filter((x) => x.id !== id));
    }, 4000);
  }, []);

  const value = useMemo(() => ({ push }), [push]);

  return (
    <ToastCtx.Provider value={value}>
      {children}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 w-[320px]">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              layout
              initial={{ opacity: 0, y: 12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, x: 20, transition: { duration: 0.2 } }}
              transition={{ duration: 0.35, ease: [0.2, 0.8, 0.2, 1] }}
              className={`border rounded-lg px-4 py-3 shadow-sm ${TONE_STYLES[t.tone]}`}
            >
              <div className="flex items-start gap-2.5">
                <span className={`mt-1.5 inline-block w-1.5 h-1.5 rounded-full shrink-0 ${TONE_DOT[t.tone]}`} />
                <div className="flex-1">
                  <div className="text-sm font-medium leading-snug">{t.title}</div>
                  {t.detail && (
                    <div className="text-xs text-ink-muted mt-1 leading-relaxed">{t.detail}</div>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastCtx.Provider>
  );
}

/** Listen to the memory feed SSE and toast key retain/reflect events. */
export function MemoryFeedToaster({ apiBase }: { apiBase: string }) {
  const { push } = useToast();
  useEffect(() => {
    const es = new EventSource(`${apiBase}/api/memory/feed`);
    es.addEventListener("memory", (e) => {
      try {
        const payload = JSON.parse((e as MessageEvent).data) as {
          op: string;
          summary: string;
          latency_ms: number;
        };
        // Only toast interesting operations, not every recall.
        if (payload.op === "retain" && payload.summary.startsWith("retained pitch")) {
          push({ tone: "signal", title: "Pitch retained", detail: payload.summary.replace(/^retained pitch /, "") });
        } else if (payload.op === "retain" && payload.summary.startsWith("retained outcome")) {
          push({ tone: "signal", title: "Outcome recorded", detail: payload.summary.replace(/^retained outcome /, "") + " — memory will use this next week" });
        } else if (payload.op === "reflect" && payload.summary.startsWith("prioritise ok")) {
          const m = payload.summary.match(/\((\d+) adjustments\)/);
          const n = m ? Number(m[1]) : 0;
          if (n > 0) {
            push({ tone: "insight", title: `Memory reranked ${n} brand${n === 1 ? "" : "s"}`, detail: `${(payload.latency_ms / 1000).toFixed(1)}s reflect` });
          }
        } else if (payload.op === "reflect" && payload.summary.startsWith("beliefs ok")) {
          push({ tone: "insight", title: "Beliefs consolidated", detail: payload.summary });
        }
      } catch {
        // ignore
      }
    });
    es.onerror = () => es.close();
    return () => es.close();
  }, [apiBase, push]);
  return null;
}
