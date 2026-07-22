"use client";

import { useEffect, useRef, useState } from "react";

const FLASH_DURATION_MS = 1000;

/**
 * Wraps a card's already-rendered content (children) with a brief highlight
 * when `value` changes — used by StatsCard to visually flag live updates
 * (see LiveIndicator) without needing StatsCard itself to be a client
 * component (its `icon` prop is a component reference, which can't cross
 * the server->client boundary as a prop — only as already-rendered children).
 */
export function FlashCard({ value, children }: { value: string; children: React.ReactNode }) {
  const [flash, setFlash] = useState(false);
  const prevValue = useRef(value);

  useEffect(() => {
    if (prevValue.current === value) return;
    prevValue.current = value;
    setFlash(true);
    const t = window.setTimeout(() => setFlash(false), FLASH_DURATION_MS);
    return () => window.clearTimeout(t);
  }, [value]);

  return (
    <div
      className={`card card-hover flex items-start justify-between gap-4 p-5 transition-shadow duration-500 ${
        flash ? "ring-2 ring-[var(--purple)]" : ""
      }`}
    >
      {children}
    </div>
  );
}
