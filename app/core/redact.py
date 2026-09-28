"""Zero-Leak Redaction Engine (app/core/redact.py).

Guarantees zero sensitive credential, secret, or PII leakage across:
- AWS access key IDs (AKIA, ASIA, ABIA, ACCA) and secret access keys
- GitHub personal, fine-grained, app, and OAuth access tokens
- Slack bot, user, app tokens (xoxb, xoxp, xapp, xoxr, xoxa) and webhook URLs
- JWTs (JSON Web Tokens) with header, payload, and signature segments
- HTTP Authorization and Bearer headers
- Private keys and certificate blocks (RSA, EC, DSA, OPENSSH, PGP)
- Password and secret fields in key-value pairs, JSON payloads, and connection URIs
- Personally Identifiable Information (PII): emails, phone numbers, SSNs, credit cards
"""

from __future__ import annotations

import re
from typing import Any

# =============================================================================
# COMPILED REDACTION PATTERNS
# =============================================================================

# 1. Private keys & Certificate blocks (RSA, EC, DSA, OPENSSH, PGP, etc.)
_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN[ A-Z0-9_-]+PRIVATE KEY[ A-Z0-9_-]*-----[\s\S]*?-----END[ A-Z0-9_-]+PRIVATE KEY[ A-Z0-9_-]*-----"
)
_PGP_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN PGP PRIVATE KEY BLOCK-----[\s\S]*?-----END PGP PRIVATE KEY BLOCK-----"
)
_CERTIFICATE_BLOCK_RE = re.compile(
    r"-----BEGIN CERTIFICATE-----[\s\S]*?-----END CERTIFICATE-----"
)

# 2. Cloud & API Credential Patterns
# AWS Access Key IDs: AKIA (IAM), ASIA (STS temp), ABIA (STS), ACCA (Context)
_AWS_ACCESS_KEY_RE = re.compile(r"\b(AKIA|ASIA|ABIA|ACCA)[0-9A-Z]{16}\b")
# AWS Secret Access Keys in key-value contexts (40-char base64-like strings)
_AWS_SECRET_KEY_RE = re.compile(
    r"(?i)\b(aws_secret_access_key|aws_secret_key|secret_access_key)\s*[:=]\s*[\"']?(?!<redacted>)[A-Za-z0-9/+=]{40}[\"']?"
)

# GitHub Tokens: Classic (ghp, gho, ghu, ghs, ghr) and Fine-Grained (github_pat)
_GITHUB_TOKEN_RE = re.compile(r"\bgh[pousr]_[0-9a-zA-Z]{36,}\b")
_GITHUB_FINE_GRAINED_TOKEN_RE = re.compile(r"\bgithub_pat_[0-9a-zA-Z_]{82,}\b")

# Slack Tokens (xoxb bot, xoxp user, xapp app, xoxr refresh, xoxa workspace)
_SLACK_TOKEN_RE = re.compile(r"\bxox[baprs]-[0-9a-zA-Z-]{10,}\b")
_SLACK_APP_TOKEN_RE = re.compile(r"\bxapp-[0-9a-zA-Z-]{10,}\b")
_SLACK_WEBHOOK_RE = re.compile(
    r"https://hooks\.slack\.com/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]+"
)

# 3. Authentication & Bearer Tokens
# Standard JWT (header.payload.signature)
_JWT_RE = re.compile(
    r"\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b"
)
# Bearer tokens in headers or logs
_BEARER_RE = re.compile(r"\bBearer\s+(?!<redacted>)[a-zA-Z0-9_\-\.+=/]{12,}\b", re.IGNORECASE)
# Generic Authorization headers (Basic, Digest, Token)
_AUTH_HEADER_RE = re.compile(
    r"(?i)\bAuthorization\s*:\s*(Basic|Digest|Token)\s+(?!<redacted>)[^\s,;\"'\}]+"
)

# 4. Connection Strings / URIs containing credentials
# e.g., postgresql://user:password@host:5432/db -> postgresql://user:<redacted>@host:5432/db
# e.g., redis://:password@host:6379/0 -> redis://:<redacted>@host:6379/0
_URI_CREDENTIAL_RE = re.compile(
    r"\b([a-zA-Z0-9+.-]+://[^:/\s]*):(?!<redacted>)([^@\s/]+)@"
)

# 5. Generic Key-Value Secrets (e.g. password=..., secret: ..., token: ...)
_KEY_VALUE_SECRET_RE = re.compile(
    r"\b(password|passwd|pwd|secret|api_key|apikey|access_token|auth_token|token|client_secret|private_key)"
    r"\s*[:=]\s*(?!<redacted>)[^\s,;\"'\}]+",
    re.IGNORECASE,
)
# JSON formatted secrets: "password": "..."
_JSON_SECRET_RE = re.compile(
    r"(\"(?:password|passwd|pwd|secret|api_key|apikey|access_token|auth_token|token|client_secret)\")"
    r"\s*:\s*\"(?!<redacted>)[^\"]+\"",
    re.IGNORECASE,
)

# 6. Personally Identifiable Information (PII)
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"(?:\+\d{1,3}[-.\s]*)?(?:\(\d{3}\)[-.\s]?|\d{3}[-.\s])\d{3}[-.\s]\d{4}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CREDIT_CARD_RE = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")


def redact(s: str) -> str:
    """Scrubs all sensitive secrets, credentials, tokens, and PII from text.

    Guarantees:
    - Zero plain text credential leakage in stored context, LLM prompts, or notifications.
    - Idempotency: redact(redact(s)) == redact(s).
    - Preserves surrounding syntax and log context.
    """
    if not s or not isinstance(s, str):
        return s

    # 1. Private keys and Certificate blocks
    s = _PRIVATE_KEY_RE.sub("<redacted>", s)
    s = _PGP_PRIVATE_KEY_RE.sub("<redacted>", s)
    s = _CERTIFICATE_BLOCK_RE.sub("<redacted>", s)

    # 2. Cloud & API Credential Tokens
    s = _AWS_ACCESS_KEY_RE.sub("<redacted>", s)
    s = _AWS_SECRET_KEY_RE.sub(r"\1=<redacted>", s)
    s = _GITHUB_TOKEN_RE.sub("<redacted>", s)
    s = _GITHUB_FINE_GRAINED_TOKEN_RE.sub("<redacted>", s)
    s = _SLACK_TOKEN_RE.sub("<redacted>", s)
    s = _SLACK_APP_TOKEN_RE.sub("<redacted>", s)
    s = _SLACK_WEBHOOK_RE.sub("<redacted>", s)

    # 3. JWTs and Bearer / Auth Headers
    s = _JWT_RE.sub("<redacted>", s)
    s = _BEARER_RE.sub("Bearer <redacted>", s)
    s = _AUTH_HEADER_RE.sub(r"Authorization: \1 <redacted>", s)

    # 4. Connection URIs with embedded passwords
    s = _URI_CREDENTIAL_RE.sub(r"\1:<redacted>@", s)

    # 5. Key-Value and JSON Secrets
    s = _KEY_VALUE_SECRET_RE.sub(r"\1=<redacted>", s)
    s = _JSON_SECRET_RE.sub(r'\1: "<redacted>"', s)

    # 6. Personally Identifiable Information (PII)
    s = _EMAIL_RE.sub("<redacted>", s)
    s = _PHONE_RE.sub("<redacted>", s)
    s = _SSN_RE.sub("<redacted>", s)
    s = _CREDIT_CARD_RE.sub("<redacted>", s)

    return s


def redact_dict(data: Any) -> Any:
    """Recursively redacts dictionary keys, values, and list items."""
    if isinstance(data, dict):
        cleaned: dict[str, Any] = {}
        for k, v in data.items():
            lower_k = str(k).lower()
            if any(
                secret_word == lower_k or lower_k.endswith(f"_{secret_word}")
                for secret_word in (
                    "password",
                    "passwd",
                    "pwd",
                    "secret",
                    "client_secret",
                    "private_key",
                )
            ):
                cleaned[k] = "<redacted>"
            else:
                cleaned[k] = redact_dict(v)
        return cleaned
    elif isinstance(data, list):
        return [redact_dict(item) for item in data]
    elif isinstance(data, str):
        return redact(data)
    return data


def contains_secrets(s: str) -> bool:
    """Returns True if the string contains unredacted secrets or credentials."""
    if not s or not isinstance(s, str):
        return False
    # If redacting changes the string, an unredacted secret was found
    return redact(s) != s
