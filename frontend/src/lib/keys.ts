"use client";

import { useEffect } from "react";

type Handler = (e: KeyboardEvent) => void;

const IGNORE_TAGS = new Set(["INPUT", "TEXTAREA", "SELECT"]);

function isEditable(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (IGNORE_TAGS.has(target.tagName)) return true;
  if (target.isContentEditable) return true;
  return false;
}

/**
 * Bind a keyboard shortcut. Skips when focus is in an input/textarea/select
 * or when a modifier key is held (so cmd+K etc. remain free for the browser).
 */
export function useKey(keys: string[] | string, handler: Handler, deps: unknown[] = []) {
  const list = Array.isArray(keys) ? keys : [keys];
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (isEditable(e.target)) return;
      if (!list.includes(e.key)) return;
      handler(e);
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}
