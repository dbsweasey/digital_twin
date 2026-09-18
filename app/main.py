from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import uuid
import json

import config
from context import AppContext
from twin_agent import Twin
from budget import DailyBudget

@asynccontextmanager
async def lifespan(app: FastAPI):
    with open("context/projects.json", "r") as f:
        data = json.load(f)
    projects = data["projects"]
    app.state.app_context = AppContext(
        projects=projects,
        projects_by_id={p["id"]: p for p in projects}
    )

    yield

app = FastAPI(lifespan=lifespan)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

origins = [
    "http://localhost:5173",
    "https://davidbsweasey.ai",
    "https://davidbsweasey.com",
    "https://personal-webpage-git-dev-dbsweaseys-projects.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

class Message(BaseModel):
    message: str

twin = Twin()
daily_budget = DailyBudget(soft_cap=config.DAILY_SOFT_CAP, hard_cap=config.DAILY_HARD_CAP)

@app.get("/healthz")
def healthz():
    """Dedicated health-check endpoint. Deliberately touches no session state, so
    infra health pings can't leak sessions into memory."""
    return {"status": "ok"}

@app.get("/api/")
def init(request: Request, response: Response):
    """Initializes sessions and returns the current session history. If no session exists, a new one is created."""
    session_id = request.cookies.get("session_id")
    if session_id is None or session_id not in twin.sessions:
        twin.purge_expired()
        if len(twin.sessions) >= config.MAX_ACTIVE_SESSIONS:
            raise HTTPException(status_code=503, detail="Too many active sessions right now. Please try again shortly.")
        session_id = str(uuid.uuid4())
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=config.COOKIE_SECURE,
            samesite=config.COOKIE_SAMESITE,
        )
        twin.add_session(session_id)
    return {"status": "running", "history": twin.sessions[session_id].history}

@app.post("/api/chat")
@limiter.limit(config.IP_RATE_LIMIT)
@limiter.limit(config.GLOBAL_RATE_LIMIT, key_func=lambda request: "global")
async def chat(request: Request, message: Message):
    session_id = request.cookies.get("session_id")
    if session_id is None or session_id not in twin.sessions:
        raise HTTPException(status_code=400, detail="No active session. Call GET /api/ first.")

    if len(message.message) > config.MAX_MESSAGE_LENGTH:
        raise HTTPException(status_code=400, detail=f"Message too long (max {config.MAX_MESSAGE_LENGTH} characters).")

    allowed, reason = twin.reserve(session_id)
    if not allowed:
        raise HTTPException(status_code=429, detail=reason)

    try:
        budget_state = daily_budget.record()
        if budget_state == "hard":
            raise HTTPException(status_code=503, detail="The digital twin has hit its daily limit. Please check back tomorrow!")
        response = await twin.completions(
            message.message,
            session_id,
            request.app.state.app_context,
            degraded=(budget_state == "soft"),
        )
    finally:
        twin.release(session_id)

    return {"message": response}
