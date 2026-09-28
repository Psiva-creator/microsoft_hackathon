import re

# Compiled regex patterns for redaction
_AWS_KEY_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_SLACK_TOKEN_RE = re.compile(r"\bxox[baprs]-[0-9a-zA-Z-]+\b")
_GITHUB_TOKEN_RE = re.compile(r"\bgh[pousr]_[0-9a-zA-Z]{36,}\b")
_JWT_RE = re.compile(r"\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b")
_BEARER_RE = re.compile(r"\bBearer\s+[a-zA-Z0-9_\-\.]{12,}\b", re.IGNORECASE)
_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN[ A-Z0-9_-]+PRIVATE KEY-----[\s\S]*?-----END[ A-Z0-9_-]+PRIVATE KEY-----"
)
_KEY_VALUE_SECRET_RE = re.compile(
    r"\b(password|passwd|secret|api_key|token)\s*[:=]\s*(?!<redacted>)[^\s,;\"'\}]+",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_PHONE_RE = re.compile(r"(?:\+\d{1,3}[-.\s]*)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")


def redact(s: str) -> str:
    """Redacts secrets and PII from text before storage or sending to LLM."""
    if not s:
        return s

    # 1. Private keys
    s = _PRIVATE_KEY_RE.sub("<redacted>", s)
    # 2. Specific API tokens
    s = _AWS_KEY_RE.sub("<redacted>", s)
    s = _SLACK_TOKEN_RE.sub("<redacted>", s)
    s = _GITHUB_TOKEN_RE.sub("<redacted>", s)
    s = _JWT_RE.sub("<redacted>", s)
    s = _BEARER_RE.sub("Bearer <redacted>", s)
    # 3. PII: email and phone
    s = _EMAIL_RE.sub("<redacted>", s)
    s = _PHONE_RE.sub("<redacted>", s)
    # 4. Key-value secrets (e.g. password=secret123)
    s = _KEY_VALUE_SECRET_RE.sub(r"\1=<redacted>", s)

    return s
