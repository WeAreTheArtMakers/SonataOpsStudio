'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const links = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/kpis', label: 'KPIs' },
  { href: '/anomalies', label: 'Anomalies' },
  { href: '/listen', label: 'Listen' },
  { href: '/copilot', label: 'Copilot' },
  { href: '/briefs', label: 'Briefs' },
  { href: '/admin', label: 'Admin' }
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-ink/70 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <Link href="/dashboard" className="text-sm font-semibold tracking-[0.2em] uppercase text-mint">
          SonataOps Studio
        </Link>
        <nav className="flex flex-wrap gap-2">
          {links.map((link) => {
            const active = pathname?.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-xl px-3 py-1.5 text-xs uppercase tracking-[0.16em] transition ${
                  active ? 'bg-mint/30 text-sand' : 'bg-white/5 text-sand/80 hover:bg-white/10'
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
