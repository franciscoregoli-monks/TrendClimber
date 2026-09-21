# TrendClimber

Detecta en qué fase está una tendencia antes de que se masifique — keywords con IA + Google Trends.

El desarrollo activo vive en [franciscoregoli-monks/TrendClimber](https://github.com/franciscoregoli-monks/TrendClimber). `main` es la línea de producto. El repo original de Isabella queda como `upstream` histórico y no recibe cambios.

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
