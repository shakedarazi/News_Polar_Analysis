import { NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

// Server-side proxy so the political bias meter (client component) can
// trigger generation same-origin, regardless of which port `next dev`
// happens to run on.
export async function POST(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const res = await fetch(`${API_BASE}/api/articles/${encodeURIComponent(id)}/bias/generate`, {
    method: "POST",
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
