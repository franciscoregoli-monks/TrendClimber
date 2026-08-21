import { NextRequest, NextResponse } from "next/server";

import type { AnalyzeRequest, AnalyzeResponse } from "@/lib/types";

const PYTHON_API = process.env.PYTHON_API_URL ?? "http://127.0.0.1:8000";

export async function POST(request: NextRequest) {
  let body: AnalyzeRequest;

  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "JSON inválido" }, { status: 400 });
  }

  if (!body.title?.trim() || !body.description?.trim()) {
    return NextResponse.json(
      { error: "Título y descripción son obligatorios" },
      { status: 400 },
    );
  }

  try {
    const res = await fetch(`${PYTHON_API}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json(
        { error: data.detail ?? data.error ?? "Error del servidor Python" },
        { status: res.status },
      );
    }

    return NextResponse.json(data as AnalyzeResponse);
  } catch {
    return NextResponse.json(
      {
        error:
          "No se pudo conectar con el backend Python. Ejecuta: uvicorn server.main:app --reload --port 8000",
      },
      { status: 503 },
    );
  }
}
