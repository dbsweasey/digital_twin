from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import time
import config
from agents import Agent, Runner, RunConfig, ModelSettings, SQLiteSession
from tools import record_user_details, unknown_question, search_projects, get_project_details, list_projects_by_category
from context import SYSTEM_PROMPT

@dataclass
class Message():
    role: str
    content: str
    timestamp: str

@dataclass
class Session():
    session: SQLiteSession
    history: list[Message]
    busy: bool = False
    message_times: deque = field(default_factory=deque)
    last_active: float = field(default_factory=time.time)

class Twin():
    def __init__(self):
        self.twin = Agent(
            name="Twin",
            instructions=SYSTEM_PROMPT,
            model="gpt-5.4-mini",
            tools=[
                record_user_details,
                unknown_question,
                search_projects,
                get_project_details,
                list_projects_by_category
            ]
        )
        self.sessions: dict[str, Session] = {}

    def add_session(self, session_id: str):
        """Adds a new session with the given session_id to memory."""
        self.sessions[session_id] = Session(SQLiteSession(session_id), [])

    def purge_expired(self):
        """Evicts idle sessions (no activity within SESSION_TTL_SECONDS) from memory.
        Never evicts a session with a request currently in flight."""
        now = time.time()
        expired = [
            sid for sid, s in self.sessions.items()
            if not s.busy and now - s.last_active > config.SESSION_TTL_SECONDS
        ]
        for sid in expired:
            del self.sessions[sid]

    def reserve(self, session_id: str) -> tuple[bool, str]:
        """Attempts to claim this session for a single in-flight request, applying the
        per-session busy-lock and rolling rate limit. Returns (allowed, reason)."""
        s = self.sessions[session_id]
        if s.busy:
            return False, "Please wait for the current response before sending another message."

        now = time.time()
        while s.message_times and now - s.message_times[0] > config.SESSION_RATE_LIMIT_WINDOW_SECONDS:
            s.message_times.popleft()
        if len(s.message_times) >= config.SESSION_RATE_LIMIT_COUNT:
            return False, "You're sending messages too quickly. Please wait a bit before trying again."

        s.busy = True
        s.last_active = now
        s.message_times.append(now)
        return True, ""

    def release(self, session_id: str):
        self.sessions[session_id].busy = False

    async def completions(self, message: str, session_id: str, context, degraded: bool = False):
        print(session_id)
        print('Message:', message)
        self.sessions[session_id].history.append(Message("user", message, datetime.isoformat(datetime.now())))

        run_config = None
        if degraded:
            run_config = RunConfig(
                model=config.DEGRADED_MODEL,
                model_settings=ModelSettings(max_tokens=config.DEGRADED_MAX_TOKENS),
            )

        try:
            result = await Runner.run(
                self.twin,
                input=message,
                session=self.sessions[session_id].session,
                context=context,
                run_config=run_config,
            )
            output = result.final_output
        except Exception as e:
            print(f"Agent run failed for session {session_id}: {e}")
            output = "Sorry, I'm having trouble responding right now. Please try again in a moment."

        self.sessions[session_id].history.append(Message("twin", output, datetime.isoformat(datetime.now())))

        return output
