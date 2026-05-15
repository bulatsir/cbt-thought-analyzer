import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.groq_client import GroqClient
from app.rate_limit import InMemoryRateLimiter
from app.schemas import AnalyzeRequest, AnalyzeResponse

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY env var is required")
    app.state.groq = GroqClient(api_key=api_key)
    app.state.rate_limiter = InMemoryRateLimiter(
        max_per_minute=int(os.environ.get("RATE_LIMIT_PER_MINUTE", "30"))
    )
    logger.info("Backend ready")
    yield
    await app.state.groq.close()


app = FastAPI(title="CBT Thought Analyzer Backend", lifespan=lifespan)

allowed_origins = [
    o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Device-Id"],
)


def get_groq(request: Request) -> GroqClient:
    return request.app.state.groq


async def rate_limit(
    request: Request,
    x_device_id: str = Header(..., alias="X-Device-Id", min_length=1, max_length=128),
) -> str:
    limiter: InMemoryRateLimiter = request.app.state.rate_limiter
    if not await limiter.allow(x_device_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    return x_device_id


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    body: AnalyzeRequest,
    groq: GroqClient = Depends(get_groq),
    _: str = Depends(rate_limit),
) -> AnalyzeResponse:
    return await groq.analyze(body)
