import { NextRequest, NextResponse } from "next/server";

import type { BrandStrategyRequest, BrandStrategyResponse } from "@/lib/types";

const PYTHON_API = process.env.PYTHON_API_URL ?? "http://127.0.0.1:8000";

export async function POST(request: NextRequest) {
  let body: BrandStrategyRequest;

  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "JSON inválido" }, { status: 400 });
  }

  if (!body.brand?.brandName?.trim() || !body.brand?.sector?.trim()) {
    return NextResponse.json(
      { error: "Nombre y sector de marca son obligatorios" },
      { status: 400 },
    );
  }

  if (!body.analyze?.stage) {
    return NextResponse.json(
      { error: "Se requiere un análisis de trend previo" },
      { status: 400 },
    );
  }

  try {
    const res = await fetch(`${PYTHON_API}/brand-strategy`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json(
        { error: data.detail ?? "Error del servidor Python" },
        { status: res.status },
      );
    }

    return NextResponse.json(data as BrandStrategyResponse);
  } catch {
    return NextResponse.json(
      { error: "No se pudo conectar con el backend Python." },
      { status: 503 },
    );
  }
}
