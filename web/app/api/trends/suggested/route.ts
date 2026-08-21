import { NextRequest, NextResponse } from "next/server";

import type { SuggestedTrendsResponse } from "@/lib/types";

const PYTHON_API = process.env.PYTHON_API_URL ?? "http://127.0.0.1:8000";

export async function GET(request: NextRequest) {
  const geo = request.nextUrl.searchParams.get("geo") ?? "";
  const limit = request.nextUrl.searchParams.get("limit") ?? "12";

  try {
    const params = new URLSearchParams({ limit });
    if (geo) params.set("geo", geo);

    const res = await fetch(`${PYTHON_API}/trends/suggested?${params.toString()}`, {
      next: { revalidate: 300 },
    });

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json(
        { error: data.detail ?? "Error al obtener trends sugeridas" },
        { status: res.status },
      );
    }

    return NextResponse.json(data as SuggestedTrendsResponse);
  } catch {
    return NextResponse.json(
      { error: "No se pudo conectar con el backend Python." },
      { status: 503 },
    );
  }
}
