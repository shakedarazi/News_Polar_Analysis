import { NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const ASK_TIMEOUT_MS = 45_000;

// Allow the Render cold-start + OpenAI round-trip; Hobby still caps lower.
export const maxDuration = 60;

// Server-side proxy so the browser only ever talks same-origin (no CORS
// dependency on whatever port `next dev` happens to run on).
export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON" }, { status: 400 });
  }

  try {
    const res = await fetch(`${API_BASE}/api/ai/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(ASK_TIMEOUT_MS),
    });
    const data = await res.json().catch(() => null);
    if (data === null) {
      return NextResponse.json(
        { detail: "השרת החזיר תשובה לא תקינה. נסו שוב." },
        { status: 502 },
      );
    }
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    const timedOut =
      err instanceof Error && (err.name === "TimeoutError" || err.name === "AbortError");
    return NextResponse.json(
      {
        detail: timedOut
          ? "הבקשה לקחה יותר מדי זמן. נסו שוב בעוד רגע — השרת לפעמים נרדם אחרי חוסר פעילות."
          : "לא ניתן להתחבר לשרת ה-AI.",
      },
      { status: 504 },
    );
  }
}
