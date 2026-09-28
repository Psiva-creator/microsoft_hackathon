from app.core.redact import redact


def test_redact_aws_key():
    text = "Error accessing S3 with key AKIAIOSFODNN7EXAMPLE and secret."
    assert redact(text) == "Error accessing S3 with key <redacted> and secret."


def test_redact_slack_token():
    text = "Notification sent using token xoxb-1234567890-abcdef."
    assert redact(text) == "Notification sent using token <redacted>."


def test_redact_github_token():
    text = "Cloning repo with token ghp_1234567890abcdefghijklmnopqrstuvwxyz12."
    assert redact(text) == "Cloning repo with token <redacted>."


def test_redact_jwt():
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    text = f"User session token: {jwt}"
    assert redact(text) == "User session token: <redacted>"


def test_redact_bearer():
    text = "Authorization: Bearer super-secret-token-value-here"
    assert redact(text) == "Authorization: Bearer <redacted>"


def test_redact_private_key():
    key = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA0Y1+abcdef...\n"
        "-----END RSA PRIVATE KEY-----"
    )
    assert redact(key) == "<redacted>"


def test_redact_key_value_password():
    text = "Connecting with password=supersecret and token:mytoken123"
    assert redact(text) == "Connecting with password=<redacted> and token=<redacted>"


def test_redact_pii():
    text = "Contact admin at devops@company.com or +1 (555) 234-5678 for assistance."
    assert redact(text) == "Contact admin at <redacted> or <redacted> for assistance."
