"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useState,
} from "react";

type Theme = "light" | "dark";

type ThemeContextValue = {
  theme: Theme;
  toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

// useLayoutEffect is a no-op (with a warning) during SSR; fall back to
// useEffect there since this component only ever runs its effects client-side.
const useIsomorphicLayoutEffect = typeof window !== "undefined" ? useLayoutEffect : useEffect;

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  // Always start from the same value the server rendered ("light"), so the
  // client's first render matches and React doesn't flag a hydration
  // mismatch. The real theme — already applied to <html> by the anti-flash
  // script in layout.tsx — is read synchronously below, before the browser
  // paints, so there's no visible flash.
  const [theme, setTheme] = useState<Theme>("light");
  const [ready, setReady] = useState(false);

  useIsomorphicLayoutEffect(() => {
    const attr = document.documentElement.getAttribute("data-theme");
    setTheme(attr === "dark" ? "dark" : "light");
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return; // don't stomp the pre-set attribute before we've read it back
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme, ready]);

  useEffect(() => {
    // Keep following the system preference only until the user picks explicitly.
    if (localStorage.getItem("theme")) return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = (e: MediaQueryListEvent) => setTheme(e.matches ? "dark" : "light");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => {
      const next: Theme = prev === "dark" ? "light" : "dark";
      localStorage.setItem("theme", next);
      return next;
    });
  }, []);

  return <ThemeContext.Provider value={{ theme, toggleTheme }}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider");
  return ctx;
}
