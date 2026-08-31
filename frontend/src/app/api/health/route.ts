import { NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

// Cheap wake-up so opening עוזר AI can spin Render out of sleep before the
// user submits a question (the ask path also hits OpenAI and is much slower).
export async function GET() {
  try {
    const res = await fetch(`${API_BASE}/api/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(20_000),
    });
    const data = await res.json().catch(() => ({ status: "error" }));
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ status: "unreachable" }, { status: 504 });
  }
}
