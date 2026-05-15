# CBT Backend

FastAPI-прокси к Groq API. Хранит ключ на сервере, делает rate-limit по `X-Device-Id`.

## Эндпоинты

- `GET  /health` — readiness/liveness
- `POST /analyze` — `{thought, situation?, emotions?, language?}` → `{distortions: [...]}`
- Защищён `X-Device-Id` хедером (rate-limit 30/мин).

Swagger UI: `/docs`. OpenAPI: `/openapi.json` (нужен для генерации iOS-клиента).

## Локальный запуск

```bash
cp .env.example .env
# вписать GROQ_API_KEY
docker compose up
```

Бэк на `http://localhost:8000`.

Без Docker:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GROQ_API_KEY=...
uvicorn app.main:app --reload
```

## Деплой

См. `../deploy/` — k8s-манифесты.
