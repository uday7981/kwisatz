"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "This week" },
  { href: "/learned", label: "Beliefs" },
  { href: "/analytics", label: "Analytics" },
  // { href: "/learning", label: "Learning" }, // hidden for demo — eval showed no lift on last run
  // { href: "/outreach", label: "Outreach" }, // hidden — redundant with dossier outcome buttons
];

export function NavRail() {
  const path = usePathname();
  return (
    <nav className="w-48 shrink-0 border-r border-rule px-4 py-6 flex flex-col gap-0.5">
      <div className="px-2 pb-6 mb-2">
        <div className="font-display text-lg font-semibold leading-tight">Underdog</div>
        <div className="text-[11px] text-ink-muted mt-0.5">Lanternfish Growth</div>
      </div>
      {links.map((l) => {
        const active = path === l.href;
        return (
          <Link
            key={l.href}
            href={l.href}
            className={`px-2 py-1.5 rounded text-sm transition-colors ${
              active
                ? "text-signal font-medium"
                : "text-ink-muted hover:text-ink"
            }`}
          >
            {l.label}
          </Link>
        );
      })}
    </nav>
  );
}
