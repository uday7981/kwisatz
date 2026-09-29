"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { MemoryFeedToggle } from "@/components/memory-feed";

export function TopBar() {
  const { data } = useQuery({ queryKey: ["week"], queryFn: api.week });
  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 30_000,
  });

  const memOn = Boolean(data?.memory_available);
  const memoryUnreachable = health && !health.hindsight_reachable;

  return (
    <header className="border-b border-rule bg-surface-raised px-6 py-2.5 flex items-center gap-4 text-sm">
      <div className="flex items-center gap-2">
        <span
          className={`inline-block w-2 h-2 rounded-full ${memOn && !memoryUnreachable ? "bg-signal" : "bg-ink-muted"}`}
          title={memoryUnreachable ? "Memory unreachable" : memOn ? "Memory on" : "Memory off"}
        />
        <span className="text-ink-muted text-xs">
          {memoryUnreachable ? "memory offline" : memOn ? "memory live" : "memory idle"}
        </span>
      </div>
      <div className="ml-auto">
        <MemoryFeedToggle />
      </div>
    </header>
  );
}
