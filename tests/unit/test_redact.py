from app.core.redact import contains_secrets, redact, redact_dict


def test_redact_aws_key():
    text = "Error accessing S3 with key AKIAIOSFODNN7EXAMPLE and secret."
    assert redact(text) == "Error accessing S3 with key <redacted> and secret."


def test_redact_aws_sts_and_secret_access_key():
    text = "STS key ASIAIOSFODNN7EXAMPLE with aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    redacted = redact(text)
    assert "ASIAIOSFODNN7EXAMPLE" not in redacted
    assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in redacted
    assert "<redacted>" in redacted
    assert "aws_secret_access_key=<redacted>" in redacted


def test_redact_slack_token():
    text = "Notification sent using token xoxb-1234567890-abcdef."
    assert redact(text) == "Notification sent using token <redacted>."


def test_redact_slack_app_token_and_webhook():
    webhook_url = "https://" + "hooks.slack" + ".com/services/T00000000/B00000000/" + ("X" * 24)
    app_token = "xapp-" + "1-A0123456789-abcdef123456"
    text = f"App socket {app_token} and webhook {webhook_url}"
    redacted = redact(text)
    assert app_token not in redacted
    assert "hooks.slack" not in redacted
    assert "<redacted>" in redacted


def test_redact_github_token():
    dummy_ghp = "ghp_" + "1234567890abcdefghijklmnopqrstuvwxyz12"
    text = f"Cloning repo with token {dummy_ghp}."
    assert redact(text) == "Cloning repo with token <redacted>."


def test_redact_github_fine_grained_pat():
    dummy_pat = "github_pat_" + "11AAAAAAA0123456789abcdefghijklmnopqrstuvwxyz_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    text = f"Accessing repo with {dummy_pat}"
    redacted = redact(text)
    assert "github_pat_" not in redacted
    assert "<redacted>" in redacted


def test_redact_jwt():
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    text = f"User session token: {jwt}"
    assert redact(text) == "User session token: <redacted>"


def test_redact_bearer():
    text = "Authorization: Bearer super-secret-token-value-here"
    assert redact(text) == "Authorization: Bearer <redacted>"


def test_redact_auth_header_basic():
    text = "Authorization: Basic dXNlcjpzdXBlcnNlY3JldA=="
    assert redact(text) == "Authorization: Basic <redacted>"


def test_redact_private_key():
    key = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA0Y1+abcdef...\n"
        "-----END RSA PRIVATE KEY-----"
    )
    assert redact(key) == "<redacted>"


def test_redact_openssh_and_pgp_keys():
    ssh_key = (
        "-----BEGIN OPENSSH PRIVATE KEY-----\n"
        "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAA...\n"
        "-----END OPENSSH PRIVATE KEY-----"
    )
    pgp_key = (
        "-----BEGIN PGP PRIVATE KEY BLOCK-----\n"
        "Version: BCPG v1.58\n"
        "...\n"
        "-----END PGP PRIVATE KEY BLOCK-----"
    )
    assert redact(ssh_key) == "<redacted>"
    assert redact(pgp_key) == "<redacted>"


def test_redact_key_value_password():
    text = "Connecting with password=supersecret and token:mytoken123"
    assert redact(text) == "Connecting with password=<redacted> and token=<redacted>"


def test_redact_json_secret():
    json_text = '{"username": "admin", "password": "SuperSecretPassword123!", "api_key": "ak_test_456"}'
    redacted = redact(json_text)
    assert "SuperSecretPassword123!" not in redacted
    assert "ak_test_456" not in redacted
    assert '"password": "<redacted>"' in redacted
    assert '"api_key": "<redacted>"' in redacted
    assert '"username": "admin"' in redacted


def test_redact_connection_uri():
    db_uri = "Connecting to postgresql://dbuser:MySecretPassword99@postgres.internal.net:5432/orders_db"
    redis_uri = "Cache at redis://:secretpass123@redis-cluster:6379/0"
    assert redact(db_uri) == "Connecting to postgresql://dbuser:<redacted>@postgres.internal.net:5432/orders_db"
    assert redact(redis_uri) == "Cache at redis://:<redacted>@redis-cluster:6379/0"


def test_redact_pii():
    text = "Contact admin at devops@company.com or +1 (555) 234-5678 for assistance."
    assert redact(text) == "Contact admin at <redacted> or <redacted> for assistance."


def test_redact_idempotency():
    text = (
        "Alert: AKIAIOSFODNN7EXAMPLE failed with password=mypass "
        "and email user@test.com on postgresql://usr:pwd@host/db"
    )
    pass1 = redact(text)
    pass2 = redact(pass1)
    assert pass1 == pass2
    assert "<<" not in pass2
    assert "<redacted>" in pass2


def test_redact_dict():
    structured_log = {
        "event": "login_attempt",
        "user": "sre_engineer",
        "password": "ClearTextPassword!",
        "headers": {
            "Authorization": "Bearer my-jwt-token-abcdef123456",
            "X-User-Email": "sre@company.com",
        },
        "tags": ["prod", "auth"],
    }
    cleaned = redact_dict(structured_log)
    assert cleaned["user"] == "sre_engineer"
    assert cleaned["password"] == "<redacted>"
    assert cleaned["headers"]["Authorization"] == "Bearer <redacted>"
    assert cleaned["headers"]["X-User-Email"] == "<redacted>"
    assert cleaned["tags"] == ["prod", "auth"]


def test_contains_secrets():
    assert contains_secrets("Nothing to hide here, standard service log.") is False
    assert contains_secrets("AWS key AKIAIOSFODNN7EXAMPLE leaked") is True
    assert contains_secrets("password=supersecret") is True
    assert contains_secrets("Already clean: password=<redacted>") is False
