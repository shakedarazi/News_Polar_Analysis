"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Menu, X } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";
import { NotificationBell } from "./NotificationBell";

// Destinations only. Three of these used to be hash links into sections of the
// home page ("סקירת מגמות", "השוואת אתרים", "מקורות"), which read as separate
// areas of the site but were not: from /articles they threw the reader back to
// the dashboard, and `active` below could never match them, so the nav claimed
// you were on the home page while the content came from a section of it. The
// home page carries its own ordering; wayfinding inside one page belongs to
// that page.
const links = [
  { href: "/", label: "דף הבית" },
  { href: "/articles", label: "כתבות" },
  { href: "/events", label: "ציר זמן אירועים" },
  { href: "/assistant", label: "עוזר AI" },
  { href: "/about", label: "אודות" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 bg-[var(--navy)] text-white shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--purple)]/20 text-[var(--purple-light)]">
              <BarChart3 className="h-6 w-6" />
            </div>
            <div>
              <div className="text-lg font-bold leading-tight">Trust</div>
              <div className="text-xs text-white/50">ניתוח מגמות בכתבות חדשות</div>
            </div>
          </Link>

          <nav className="hidden items-center gap-1 md:flex" aria-label="ניווט ראשי">
            {links.map(({ href, label }) => {
              const active = href === "/" ? pathname === "/" : pathname === href;
              return (
                <Link
                  key={href}
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={`relative px-3 py-2 text-sm font-medium transition ${
                    active ? "text-white" : "text-white/60 hover:text-white"
                  }`}
                >
                  {label}
                  {active && (
                    <span className="absolute inset-x-2 -bottom-[17px] h-0.5 rounded-full bg-[var(--purple-light)]" />
                  )}
                </Link>
              );
            })}
          </nav>

          <div className="flex items-center gap-1">
            <NotificationBell />
            <div className="hidden md:block">
              <ThemeToggle />
            </div>
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              className="rounded-lg p-2 text-white/80 hover:bg-white/10 md:hidden"
              aria-label={open ? "סגור תפריט" : "פתח תפריט"}
              aria-expanded={open}
            >
              {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>

        {open && (
          <nav className="border-t border-white/10 px-4 py-2 md:hidden" aria-label="ניווט נייד">
            {links.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className="block rounded-lg px-3 py-2.5 text-sm font-medium text-white/80 hover:bg-white/10"
              >
                {label}
              </Link>
            ))}
            <div className="mt-1 flex items-center justify-between border-t border-white/10 px-3 pt-2">
              <span className="text-sm font-medium text-white/80">מצב תצוגה</span>
              <ThemeToggle />
            </div>
          </nav>
        )}
      </header>

      <main>{children}</main>

      <footer className="border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 py-6 text-center text-sm text-slate-500 dark:text-slate-400">
        Trust · ניתוח דטרמיניסטי של כתבות ותגובות קהל מהנתונים הקיימים במערכת
      </footer>
    </div>
  );
}
