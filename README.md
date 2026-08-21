# TrendClimber

Detecta en qué fase está una tendencia antes de que se masifique — keywords con IA + Google Trends.

## Run

```bash
# Backend
uvicorn server.main:app --reload --port 8000

# Frontend
cd web && npm install && npm run dev
```

App: http://localhost:3000

## Env

Copia `.env.example` a `.env` y configura `GOOGLE_API_KEY` y credenciales de BigQuery si aplica.
