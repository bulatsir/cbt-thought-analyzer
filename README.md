# CBT Thought Analyzer — backend

FastAPI service that detects cognitive distortions in automatic thoughts using an LLM. Built to back a native iOS client (separate repository).

## Stack

FastAPI · httpx async · pydantic · Llama 3.3 70B via [OpenRouter](https://openrouter.ai) (providers `[groq, sambanova-turbo]`, fallbacks on) · in-memory rate limiter keyed by `X-Device-Id` (30 req/min). Docker image, k8s-friendly.

## API

`POST /analyze` — pick up to 3 cognitive distortions from a fixed list of 18 and explain why each one fits the thought. Returns everything in the requested language.

```bash
curl -X POST http://localhost:8000/analyze \
  -H 'Content-Type: application/json' \
  -H 'X-Device-Id: 11111111-1111-1111-1111-111111111111' \
  -d '{"thought":"everything is lost","situation":"got fired","emotions":"panic","language":"en"}'
```

```json
{
  "distortions": [
    { "name": "Catastrophizing",        "explanation": "The thought exaggerates the consequences of being fired..." },
    { "name": "All-or-Nothing Thinking", "explanation": "The thought frames the situation in absolute terms..." }
  ]
}
```

- `language` — `"ru"` (default) or `"en"`; both `name` and `explanation` come back in that language
- Names are picked from a fixed list in `backend/app/prompts.py` — non-canonical replies from the model are dropped server-side
- Gibberish input (`"asdf"`, `"zzz"`, …) → empty `distortions` array
- Other endpoints: `GET /health`, `POST /downward-arrow`, `POST /socratic`, Swagger at `/docs`

## Run locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo OPENROUTER_API_KEY=sk-or-... > .env
uvicorn app.main:app --reload --port 8000
```

or `docker compose up` in the same directory.

## Layout

```
backend/app/
├── main.py         # endpoints, lifespan
├── schemas.py      # request/response pydantic models
├── prompts.py      # system prompt builders + canonical lists
├── groq_client.py  # OpenRouter wrapper (name kept for diff hygiene)
└── rate_limit.py   # in-memory sliding window
```
