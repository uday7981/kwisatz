"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE } from "@/lib/api";

type FeedEvent = {
  op: string;
  bank_id: string;
  summary: string;
  latency_ms: number;
  payload_ref?: string;
};

export function MemoryFeed({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [events, setEvents] = useState<FeedEvent[]>([]);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!open) {
      esRef.current?.close();
      esRef.current = null;
      return;
    }
    const es = new EventSource(`${API_BASE}/api/memory/feed`);
    es.addEventListener("memory", (e) => {
      try {
        const payload = JSON.parse((e as MessageEvent).data) as FeedEvent;
        setEvents((prev) => [payload, ...prev].slice(0, 200));
      } catch {
        /* noop */
      }
    });
    es.onerror = () => es.close();
    esRef.current = es;
    return () => {
      es.close();
      esRef.current = null;
    };
  }, [open]);

  if (!open) return null;
  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-surface-raised border-l border-rule shadow-xl z-50 flex flex-col">
      <div className="px-4 py-3 border-b border-rule flex items-center gap-3">
        <span className="text-xs uppercase tracking-wide text-ink-muted">Memory feed</span>
        <button onClick={onClose} className="ml-auto text-ink-muted hover:text-ink text-sm">
          close
        </button>
      </div>
      <div className="flex-1 overflow-y-auto text-sm rule-divider">
        {events.length === 0 && (
          <div className="p-4 text-ink-muted text-xs">Waiting for memory activity...</div>
        )}
        {events.map((e, i) => (
          <div key={i} className="p-3">
            <div className="text-xs text-ink-muted flex items-center gap-2">
              <span className="tabular">{e.op}</span>
              <span>·</span>
              <span className="tabular">{e.latency_ms}ms</span>
            </div>
            <div className="mt-1">{e.summary}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function MemoryFeedToggle() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === "m" && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const target = e.target as HTMLElement;
        if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") return;
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);
  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="text-xs text-ink-muted hover:text-ink inline-flex items-center gap-1.5"
        aria-label="Open memory feed (M)"
      >
        memory feed
        <span className="kbd">M</span>
      </button>
      <MemoryFeed open={open} onClose={() => setOpen(false)} />
    </>
  );
}
