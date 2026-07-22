import { NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export async function PATCH() {
  const res = await fetch(`${API_BASE}/api/alerts/read-all`, { method: "PATCH" });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
