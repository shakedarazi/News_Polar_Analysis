import { NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

// Server-side proxy so the notification bell (client component) can fetch
// same-origin, regardless of which port `next dev` happens to run on.
export async function GET(request: Request) {
  const { search } = new URL(request.url);
  const res = await fetch(`${API_BASE}/api/alerts${search}`, { cache: "no-store" });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
