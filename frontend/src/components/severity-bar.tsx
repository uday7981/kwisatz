export function SeverityBar({ value }: { value: number }) {
  const filled = Math.max(0, Math.min(6, Math.round(value * 6)));
  return (
    <span aria-label={`severity ${value.toFixed(2)}`} className="inline-flex gap-[2px]">
      {Array.from({ length: 6 }).map((_, i) => (
        <span
          key={i}
          className={`w-1.5 h-3 rounded-sm ${i < filled ? "bg-risk" : "bg-rule"}`}
        />
      ))}
    </span>
  );
}
