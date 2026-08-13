# CBT Backend

FastAPI-прокси к OpenRouter (Claude Sonnet 5). Хранит ключ на сервере, делает rate-limit по `X-Device-Id`.

(`GroqClient` и переменная `GROQ_API_KEY` — историческое наименование со времён Groq; фактически ходит в OpenRouter.)

## Эндпоинты

- `GET  /health` — readiness/liveness
- `POST /analyze` — `{thought, situation?, emotions?, language?}` → `{distortions: [...]}`
- `POST /beliefs` — `{entries: [...] (минимум 10), language?}` → `{beliefs: [{belief, area, evidence}], summary}`
- `POST /transcribe` — multipart `file` + `language` → `{text}`
- `POST /suggest`, `POST /review` — остались от выпиленной вкладки «Голоса», клиента сейчас нет
- Всё защищено `X-Device-Id` хедером (rate-limit 30/мин).

Swagger UI: `/docs`. OpenAPI: `/openapi.json` (нужен для генерации iOS-клиента).

## Локальный запуск

```bash
cp .env.example .env
# вписать ключ OpenRouter (переменная исторически зовётся GROQ_API_KEY)
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
