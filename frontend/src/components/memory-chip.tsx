import { clsx } from "clsx";

type Tone = "signal" | "insight" | "ink-muted";
export function MemoryChip({
  label,
  tone = "signal",
  onClick,
}: {
  label: string;
  tone?: Tone;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        "px-2 py-1 rounded-full text-xs border tabular",
        tone === "signal" && "border-signal/30 text-signal bg-signal/5",
        tone === "insight" && "border-insight/30 text-insight bg-insight/5",
        tone === "ink-muted" && "border-rule text-ink-muted bg-transparent",
        onClick ? "cursor-pointer hover:brightness-110" : "cursor-default",
      )}
    >
      {label}
    </button>
  );
}
