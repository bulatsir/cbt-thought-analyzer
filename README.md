# CBT Thought Analyzer

Detect cognitive distortions in automatic thoughts using LLM — without an API key in the client bundle. A small web + backend stack to record what happened, how you feel, and the thoughts running through your head; the backend returns the distortions it sees with short explanations.

A native SwiftUI iOS client lives in a separate repository.

## Stack

- **Frontend** — React 18 + TypeScript + Vite + Tailwind v4
- **Backend** — FastAPI (Python 3.12) + httpx async client + pydantic
- **LLM** — Llama 3.3 70B via [OpenRouter](https://openrouter.ai) with provider preference `[groq, sambanova-turbo]` (fallbacks enabled)
- **Auth/limits** — anonymous `X-Device-Id` (UUID in localStorage / UserDefaults), in-memory sliding-window rate limiter (30/min)
- **Deployment** — Docker image on a private k8s lab (Hetzner), GitOps via Gitea + ArgoCD, TLS via Cloudflare edge

Public endpoint: `https://api-abc.bulsir.com` — Swagger at `/docs`.

## Distortion detection

The system prompt is anchored to a fixed list of 18 cognitive distortions (in `backend/app/prompts.py`), so the model can't invent its own categories. The `name` field of every returned distortion is the canonical Russian name from that list. The `explanation` field is in Russian or English, depending on the `language` parameter in the request.

Server-side guardrails:

- Gibberish input (`"asdf"`, `"zzz"`, …) → empty distortions array
- LLM-emitted names not in the canonical list are dropped and logged as WARN

Request:

```bash
curl -X POST https://api-abc.bulsir.com/analyze \
  -H 'Content-Type: application/json' \
  -H 'X-Device-Id: 11111111-1111-1111-1111-111111111111' \
  -d '{
    "thought": "everything is lost",
    "situation": "got fired",
    "emotions": "panic",
    "language": "en"
  }'
```

Response:

```json
{
  "distortions": [
    {
      "name": "Катастрофизация",
      "explanation": "The thought exaggerates the consequences of being fired..."
    },
    {
      "name": "Чёрно-белое мышление",
      "explanation": "The thought frames the situation in absolute terms..."
    }
  ]
}
```

Average latency ~1 s, cost ≈ $0.00004 per call.

## Layout (web)

The form mirrors the **C → A → B** order of CBT but uses neutral labels for the user:

```
┌─────────────────────┬─────────────────────┐
│  Feelings           │  Situation          │
│  (textarea)         │  (textarea)         │
├─────────────────────┴─────────────────────┤
│  Thoughts                                 │
│  (list of inputs, inline distortion tags) │
└───────────────────────────────────────────┘
```

Analysis triggers automatically on every thought after a ~1.5 s debounce — no "Analyze" button.

## Local development

### Frontend

```bash
npm install
cp .env.example .env   # edit VITE_API_URL if you don't want to hit the public backend
npm run dev            # → http://localhost:5173
```

Or via Docker:

```bash
docker compose up
```

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # put OPENROUTER_API_KEY here
uvicorn app.main:app --reload --port 8000
```

Or via Docker:

```bash
cd backend
docker compose up
```

### Endpoints

- `POST /analyze` — detect distortions in one thought (language: `ru` / `en`, default `ru`)
- `POST /downward-arrow` — conversational technique (in iOS v1 this is currently hidden; backend still serves it)
- `POST /socratic` — conversational technique (same as above)
- `GET /health` — `{"ok": true}`
- `GET /docs` — Swagger UI

Pydantic schemas in `backend/app/schemas.py`, prompts in `backend/app/prompts.py`.

## Architecture notes

- The Groq API key is **never** in the client bundle — frontend talks only to `api-abc.bulsir.com`
- Class names `GroqClient` / file `groq_client.py` are kept for diff hygiene even though the upstream is now OpenRouter
- The 18-distortion list lives in one place (`backend/app/prompts.py:DISTORTIONS`). Clients (web, iOS) map this to localized display names
- All conversational state for the techniques is sent on every request — backend is stateless. Persistence (entry history) is local to each client

## iOS client

Native SwiftUI app — separate repository. Same backend, same distortion canon. Adds:

- Tabbed interface: Analyze / Saved / Settings
- Local persistence of entries in `Documents/entries.json` (ISO-8601 dates)
- RU/EN language toggle that drives both UI and backend `language` parameter
- Share-as-JSON export
- Designed strictly to Apple HIG — system fonts, semantic colors, sensory feedback, no UIKit

## Roadmap

- Localize the web frontend (currently Russian only)
- Backend persistence (Postgres) so history can sync across devices
- Apple Sign In (iOS) / email magic link (web)
- StoreKit / Stripe subscription for higher rate limits and history retention
- Export as PDF for working with a therapist

## License

Personal project. No license declared yet.
