import re
from typing import Any

from app.core.redact import redact

# UUIDs: standard 8-4-4-4-12 hex UUIDs, optionally enclosed in braces
_UUID_RE = re.compile(
    r"(?:\{[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}|\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b)"
)

# Timestamps:
# 1. ISO-8601 & Go/Nginx timestamps (e.g., 2026-09-28T14:30:00Z, 2026/09/28 14:30:00)
_ISO_TIMESTAMP_RE = re.compile(
    r"\b\d{4}[-/]\d{2}[-/]\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b"
)

# 2. Common Log Format (e.g., 28/Sep/2026:14:30:00 +0000)
_CLF_TIMESTAMP_RE = re.compile(
    r"\b\d{1,2}/(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/\d{4}:\d{2}:\d{2}:\d{2}(?:\s+[+-]\d{4})?\b",
    re.IGNORECASE,
)

# 3. RFC 2822 / HTTP format (e.g., Mon, 28 Sep 2026 14:30:00 GMT)
_RFC2822_TIMESTAMP_RE = re.compile(
    r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s+\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\s+\d{2}:\d{2}:\d{2}(?:\s+(?:[+-]\d{4}|GMT|UTC))?\b",
    re.IGNORECASE,
)

# 4. Standard syslog/application log timestamps (e.g., Sep 28 14:30:00, Sep  4 14:30:00.123, Sep 28 2026 14:30:00)
_LOG_TIMESTAMP_RE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+(?:\d{4}\s+)?\d{2}:\d{2}:\d{2}(?:\.\d+)?\b",
    re.IGNORECASE,
)

# 5. Labeled epoch timestamps (e.g., timestamp=1727541000, @timestamp: 1727541000123)
_EPOCH_TIMESTAMP_RE = re.compile(
    r"(?i)\b(?:timestamp|time|ts|epoch|@timestamp)\s*[:=]\s*(?:1[6-9]\d{8}(?:\.\d+)?|1[6-9]\d{11})\b"
)

# IP Addresses:
# IPv4 addresses
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# IPv6 addresses (bracketed socket format, full uncompressed, compressed with ::, and IPv4-mapped)
_IPV6_BRACKETED_RE = re.compile(r"\[[0-9a-fA-F:]+\]")
_IPV6_LOOPBACK_PORT_RE = re.compile(r"(?<![0-9a-zA-Z:])(?:::1)(?::\d+)")
_IPV6_RE = re.compile(
    r"(?<![0-9a-zA-Z:])(?:"
    r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}"
    r"|(?:[0-9a-fA-F]{1,4}:){1,7}:"
    r"|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}"
    r"|(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}"
    r"|(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}"
    r"|(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}"
    r"|(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}"
    r"|[0-9a-fA-F]{1,4}:(?::[0-9a-fA-F]{1,4}){1,6}"
    r"|:(?:(?::[0-9a-fA-F]{1,4}){1,7}|:)"
    r"|fe80:(?::[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]+"
    r"|::(?:ffff(?::0{1,4})?:)?(?:(?:\d{1,3}\.){3}\d{1,3})"
    r"|(?:[0-9a-fA-F]{1,4}:){1,4}:(?:(?:\d{1,3}\.){3}\d{1,3})"
    r")(?![0-9a-zA-Z:])"
)

# Hex strings: memory pointers (0x...) or hex identifiers >= 8 characters with at least one hex letter
_HEX_RE = re.compile(
    r"\b(?:0x[0-9a-fA-F]+|(?=[0-9a-fA-F]{8,}\b)[0-9a-fA-F]*[a-fA-F][0-9a-fA-F]*)\b"
)

# HTTP Reason phrases
_HTTP_REASON_PHRASES = (
    r"Continue|Switching Protocols|Processing|Early Hints|"
    r"OK|Created|Accepted|Non-Authoritative Information|No Content|Reset Content|Partial Content|"
    r"Multiple Choices|Moved Permanently|Found|See Other|Not Modified|Use Proxy|Temporary Redirect|Permanent Redirect|"
    r"Bad Request|Unauthorized|Payment Required|Forbidden|Not Found|Method (?:Not )?Allowed|Not Acceptable|"
    r"Proxy Authentication Required|Request Timeout|Conflict|Gone|Length Required|Precondition Failed|"
    r"Payload Too Large|URI Too Long|Unsupported Media Type|Range Not Satisfiable|Expectation Failed|"
    r"I'm a teapot|Misdirected Request|Unprocessable Entity|Locked|Failed Dependency|Too Early|"
    r"Upgrade Required|Precondition Required|Too Many Requests|Request Header Fields Too Large|Unavailable For Legal Reasons|"
    r"Internal Server Error|Not Implemented|Bad Gateway|Service Unavailable|Gateway Timeout|HTTP Version Not Supported"
)

# HTTP status codes preceded by context keywords, HTTP version, or common response verbs
_STATUS_CODE_CONTEXT_RE = re.compile(
    r"(?i)(?:"
    r'(?:["\']?(?:http|status(?:_code|code)?|code|error|returned|received|got)["\']?\s*[:=]?\s*)'
    r'|(?:\bHTTP/(?:[123](?:\.\d+)?)(?:["\'\s])+\s*)'
    r")([1-5]\d\d)\b"
)

# HTTP status codes followed by standard HTTP reason phrase (e.g. 502 Bad Gateway)
_STATUS_CODE_PHRASE_RE = re.compile(rf"(?i)\b([1-5]\d\d)(?=\s+(?:{_HTTP_REASON_PHRASES})\b)")

# HTTP protocol versions (e.g. HTTP/1.0, HTTP/1.1, HTTP/2, HTTP/2.0, HTTP/3)
_HTTP_VERSION_RE = re.compile(r"(?i)\bHTTP/(?:[123](?:\.\d+)?)\b")

_NUMBER_RE = re.compile(r"\d+")

_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _idx_to_alpha(idx: int) -> str:
    res = []
    n = idx
    while True:
        res.append(_LETTERS[n % 26])
        n = n // 26
        if n == 0:
            break
    return "".join(res)


def normalize_text(s: str) -> str:
    """Normalizes text so identical failures produce identical strings regardless of IDs, IPs, or times.

    Applies the following standardization steps in order:
    1. Secret redaction (AWS, GitHub, Slack tokens, JWTs, credentials, PII)
    2. UUID abstraction -> <uuid>
    3. Timestamp abstraction (ISO-8601, CLF, RFC 2822, Syslog, Epoch) -> <ts>
    4. IP address abstraction (IPv4 and IPv6 compressed/uncompressed/bracketed) -> <ip>
    5. Hex strings and memory addresses (0x... or 8+ char hex) -> <hex>
    6. Number abstraction -> <n>, strictly preserving standard HTTP status codes
       (e.g., HTTP/1.1 502, status: 500, 502 Bad Gateway) and HTTP versions (HTTP/1.1, HTTP/2)
    7. Whitespace collapse and trimming
    """
    if not s:
        return ""

    # 1. Redact secrets
    s = redact(s)

    # 2. UUIDs (standard or braced)
    s = _UUID_RE.sub("<uuid>", s)

    # 3. Timestamps
    s = _ISO_TIMESTAMP_RE.sub("<ts>", s)
    s = _CLF_TIMESTAMP_RE.sub("<ts>", s)
    s = _RFC2822_TIMESTAMP_RE.sub("<ts>", s)
    s = _LOG_TIMESTAMP_RE.sub("<ts>", s)

    def _replace_epoch(m: re.Match) -> str:
        full = m.group(0)
        delim = "=" if "=" in full else ":"
        prefix = full.split(delim, 1)[0]
        return f"{prefix}{delim}<ts>"

    s = _EPOCH_TIMESTAMP_RE.sub(_replace_epoch, s)

    # 4. IP addresses (IPv6 bracketed, loopback port, general IPv6, IPv4)
    s = _IPV6_BRACKETED_RE.sub("<ip>", s)
    s = _IPV6_LOOPBACK_PORT_RE.sub(lambda m: "<ip>" + m.group(0)[3:], s)
    s = _IPV6_RE.sub("<ip>", s)
    s = _IPV4_RE.sub("<ip>", s)

    # 5. Hex strings >= 8 characters or 0x pointers
    s = _HEX_RE.sub("<hex>", s)

    # 6. Numbers replacement with HTTP status code and version preservation
    preserved_tokens: list[tuple[str, str]] = []

    def preserve_match(val: str) -> str:
        token = f"__PRESERVEDTOKEN{_idx_to_alpha(len(preserved_tokens))}__"
        preserved_tokens.append((token, val))
        return token

    # Protect status codes with preceding context keywords/HTTP versions
    def protect_status_code_context(match: re.Match) -> str:
        full = match.group(0)
        code = match.group(1)
        token = preserve_match(code)
        return full[: -len(code)] + token

    s = _STATUS_CODE_CONTEXT_RE.sub(protect_status_code_context, s)

    # Protect status codes followed by standard HTTP reason phrases (e.g. 502 Bad Gateway)
    def protect_status_code_phrase(match: re.Match) -> str:
        code = match.group(1)
        token = preserve_match(code)
        return token

    s = _STATUS_CODE_PHRASE_RE.sub(protect_status_code_phrase, s)

    # Protect HTTP version like HTTP/1.1, HTTP/2
    s = _HTTP_VERSION_RE.sub(lambda m: preserve_match(m.group(0)), s)

    # Replace all remaining numbers with <n>
    s = _NUMBER_RE.sub("<n>", s)

    # Restore preserved tokens
    for token, original in preserved_tokens:
        s = s.replace(token, original)

    # 7. Collapse whitespace and strip
    s = re.sub(r"\s+", " ", s).strip()

    return s


def normalize_dict(data: Any) -> Any:
    """Recursively normalizes all string values within dictionaries and lists."""
    if isinstance(data, str):
        return normalize_text(data)
    elif isinstance(data, dict):
        return {k: normalize_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [normalize_dict(item) for item in data]
    return data
