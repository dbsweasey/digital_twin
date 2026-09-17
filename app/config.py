from dotenv import load_dotenv
import os

load_dotenv(override=True)

PUSHOVER_USER = os.getenv('PUSHOVER_USER')
PUSHOVER_TOKEN = os.getenv('PUSHOVER_TOKEN')

# --- Rate limiting ---

# Per-session: how many messages a single chat session may send in a rolling window,
# and whether a session may have more than one message "in flight" at once.
SESSION_RATE_LIMIT_COUNT = 10
SESSION_RATE_LIMIT_WINDOW_SECONDS = 5 * 60

# Per-IP and global limits (slowapi format: "<count>/<period>"), a safety net against
# a flood of requests regardless of session/cookie churn.
IP_RATE_LIMIT = "20/5minutes"
GLOBAL_RATE_LIMIT = "60/minute"

# Reject any single message longer than this (protects against oversized-prompt cost spikes).
MAX_MESSAGE_LENGTH = 2000

# Daily request budget. Past DAILY_SOFT_CAP, responses degrade (shorter, optionally a
# cheaper model) instead of shutting off, so real visitors can keep chatting on a busy day.
# Past DAILY_HARD_CAP, the twin stops calling the model entirely until the next day.
DAILY_SOFT_CAP = 200
DAILY_HARD_CAP = 600

# Degraded-mode settings, used once DAILY_SOFT_CAP is exceeded.
DEGRADED_MAX_TOKENS = 400
DEGRADED_MODEL = None  # e.g. "gpt-5.4-nano"; None keeps the primary model, just shorter replies

# --- Session lifecycle ---

# Idle sessions (no messages sent) older than this are purged from memory.
SESSION_TTL_SECONDS = 60 * 60

# Hard ceiling on concurrently-tracked sessions, as a safety valve against a burst of
# session creation outrunning the TTL purge (e.g. many uncookied requests in a short window).
MAX_ACTIVE_SESSIONS = 5000

# --- Session cookie ---

# The frontend and backend are on different domains (e.g. davidbsweasey.ai vs an
# onrender.com URL), so the cookie needs SameSite=None + Secure to survive cross-site
# fetch/XHR calls. Override via env vars for local http:// dev if needed.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "none")