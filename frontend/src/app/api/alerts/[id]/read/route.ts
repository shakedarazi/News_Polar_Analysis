import { NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export async function PATCH(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const res = await fetch(`${API_BASE}/api/alerts/${encodeURIComponent(id)}/read`, {
    method: "PATCH",
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
