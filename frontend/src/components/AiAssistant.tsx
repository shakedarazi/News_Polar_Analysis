"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { Send, Sparkles, AlertTriangle } from "lucide-react";
import { askAssistant } from "@/lib/api";
import { formatDate, sourceLabel } from "@/lib/format";
import type { QaSourceArticle } from "@/lib/types";

type Turn = {
  role: "user" | "assistant";
  content: string;
  sources?: QaSourceArticle[];
  isError?: boolean;
};

const EXAMPLE_QUESTIONS = [
  "כמה כתבות יש במערכת ומאילו מקורות?",
  "אילו כתבות הכי קיטוביות בתגובות שלהן?",
  "מה מדד הקיטוב הממוצע של הארץ לעומת ynet?",
];

export function AiAssistant() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  const send = async (question: string) => {
    const trimmed = question.trim();
    if (!trimmed || loading) return;

    setTurns((prev) => [...prev, { role: "user", content: trimmed }]);
    setInput("");
    setLoading(true);

    try {
      const res = await askAssistant(trimmed);
      setTurns((prev) => [
        ...prev,
        { role: "assistant", content: res.answer, sources: res.sources },
      ]);
    } catch (err) {
      setTurns((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            err instanceof Error
              ? err.message
              : "אירעה שגיאה בפנייה לעוזר. נסו שוב.",
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
      requestAnimationFrame(() => {
        listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
      });
    }
  };

  return (
    <div className="flex h-[70vh] min-h-[480px] flex-col overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-sm">
      <div ref={listRef} className="flex-1 space-y-4 overflow-y-auto p-5">
        {turns.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--purple)]/10 text-[var(--purple)]">
              <Sparkles className="h-6 w-6" aria-hidden />
            </div>
            <p className="max-w-sm text-sm text-slate-500 dark:text-slate-400">
              שאלו שאלה על הכתבות, המקורות והקיטוב שנאספו בפועל במערכת. העוזר עונה אך ורק על
              סמך הנתונים הקיימים במסד הנתונים — לא על ידע כללי.
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {EXAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => send(q)}
                  className="rounded-full border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:border-[var(--purple)] hover:text-[var(--purple)]"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {turns.map((turn, i) => (
          <div
            key={i}
            className={`flex ${turn.role === "user" ? "justify-start" : "justify-end"}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                turn.role === "user"
                  ? "bg-[var(--navy)] text-white"
                  : turn.isError
                    ? "border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950 text-red-800 dark:text-red-300"
                    : "border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200"
              }`}
            >
              {turn.isError && (
                <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold">
                  <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
                  שגיאה
                </div>
              )}
              <p className="whitespace-pre-wrap">{turn.content}</p>
              {turn.sources && turn.sources.length > 0 && (
                <div className="mt-3 space-y-1.5 border-t border-slate-200 dark:border-slate-700 pt-2">
                  <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">מבוסס על:</p>
                  {turn.sources.map((s) => (
                    <Link
                      key={s.article_id}
                      href={`/articles/${s.article_id}`}
                      className="block rounded-lg px-2 py-1 text-xs text-[var(--indigo)] hover:bg-white dark:hover:bg-slate-700 hover:underline"
                    >
                      {s.title || "ללא כותרת"} · {sourceLabel(s.source)} ·{" "}
                      {formatDate(s.first_seen_at)}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-end">
            <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-4 py-3">
              <span className="flex gap-1">
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 dark:bg-slate-600 [animation-delay:-0.3s]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 dark:bg-slate-600 [animation-delay:-0.15s]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 dark:bg-slate-600" />
              </span>
            </div>
          </div>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex items-center gap-2 border-t border-slate-200 dark:border-slate-700 p-3"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="שאלו שאלה על הכתבות והנתונים..."
          aria-label="שאלה לעוזר ה-AI"
          className="flex-1 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-4 py-2.5 text-sm outline-none focus:border-[var(--purple)]"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="btn-primary flex h-10 w-10 shrink-0 items-center justify-center rounded-xl disabled:opacity-40"
          aria-label="שלח שאלה"
        >
          <Send className="h-4 w-4 -scale-x-100" aria-hidden />
        </button>
      </form>
    </div>
  );
}
