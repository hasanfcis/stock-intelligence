"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/catalysts", label: "Catalyst feed" },
  { href: "/history", label: "History" },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <nav className="w-56 shrink-0 border-r border-border px-3 py-6">
      <div className="px-3 pb-6">
        <div className="text-sm font-medium text-ink">Stock Intelligence</div>
        <div className="text-xs text-muted mt-0.5">Personal research terminal</div>
      </div>
      <div className="flex flex-col gap-0.5">
        {LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`nav-link ${pathname === link.href ? "active" : ""}`}
          >
            {link.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
