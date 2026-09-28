import re

from app.core.redact import redact

_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_ISO_TIMESTAMP_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b"
)
_LOG_TIMESTAMP_RE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\b",
    re.IGNORECASE,
)
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IPV6_RE = re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b")
_HEX_RE = re.compile(r"\b(?:0x)?[0-9a-fA-F]{8,}\b")

# Regex to match HTTP status codes preceded by context keywords or HTTP/
_STATUS_CODE_CONTEXT_RE = re.compile(
    r"(?i)(?:(?:http|status|code|error)\s+|http/(?:1\.[01]|2)\s+)([1-5]\d\d)\b"
)
_HTTP_VERSION_RE = re.compile(r"(?i)\bHTTP/(?:1\.[01]|2)\b")
_NUMBER_RE = re.compile(r"\d+")

# Letter-based alphabet for placeholder tokens without digits
_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def normalize_text(s: str) -> str:
    """Normalizes text so identical failures produce identical strings regardless of IDs, IPs, or times."""
    if not s:
        return ""

    # 1. Redact secrets
    s = redact(s)

    # 2. UUIDs
    s = _UUID_RE.sub("<uuid>", s)

    # 3. Timestamps
    s = _ISO_TIMESTAMP_RE.sub("<ts>", s)
    s = _LOG_TIMESTAMP_RE.sub("<ts>", s)

    # 4. IP addresses (IPv4 & IPv6)
    s = _IPV6_RE.sub("<ip>", s)
    s = _IPV4_RE.sub("<ip>", s)

    # 5. Hex strings >= 8 characters
    s = _HEX_RE.sub("<hex>", s)

    # 6. Numbers replacement:
    preserved_tokens: list[tuple[str, str]] = []

    def get_token(idx: int) -> str:
        # Convert index to letters only (no digits)
        name = "".join(_LETTERS[(idx // (26**i)) % 26] for i in range(2))
        return f"__PRESERVEDTOKEN{name}__"

    def preserve_match(val: str) -> str:
        token = get_token(len(preserved_tokens))
        preserved_tokens.append((token, val))
        return token

    # Protect status codes FIRST while HTTP/1.1 is intact
    def protect_status_code(match: re.Match) -> str:
        full = match.group(0)
        code = match.group(1)
        token = preserve_match(code)
        return full[: -len(code)] + token

    s = _STATUS_CODE_CONTEXT_RE.sub(protect_status_code, s)

    # Protect HTTP version like HTTP/1.1 SECOND
    s = _HTTP_VERSION_RE.sub(lambda m: preserve_match(m.group(0)), s)

    # Replace all remaining numbers with <n>
    s = _NUMBER_RE.sub("<n>", s)

    # Restore preserved tokens
    for token, original in preserved_tokens:
        s = s.replace(token, original)

    # 7. Collapse whitespace and strip
    s = re.sub(r"\s+", " ", s).strip()

    return s
