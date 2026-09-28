from app.core.normalize import normalize_text


def test_normalize_ip_and_numbers():
    t1 = "Connection refused to 10.0.3.7:5432 after 30001ms"
    t2 = "Connection refused to 10.0.9.2:5432 after 29877ms"
    assert normalize_text(t1) == "Connection refused to <ip>:<n> after <n>ms"
    assert normalize_text(t2) == "Connection refused to <ip>:<n> after <n>ms"
    assert normalize_text(t1) == normalize_text(t2)


def test_normalize_http_status_codes():
    t1 = "Request returned HTTP 503 response"
    t2 = "Database query took 503 ms to complete"
    assert normalize_text(t1) == "Request returned HTTP 503 response"
    assert normalize_text(t2) == "Database query took <n> ms to complete"


def test_normalize_status_prefixes():
    assert normalize_text("status 500 internal server error") == "status 500 internal server error"
    assert normalize_text("HTTP/1.1 502 Bad Gateway") == "HTTP/1.1 502 Bad Gateway"
    assert normalize_text("code 404 not found") == "code 404 not found"
    assert normalize_text("error 504 gateway timeout") == "error 504 gateway timeout"


def test_normalize_uuid_and_hex():
    text = "Failed task c3b91a27-0402-466d-a11d-2856d302a901 at memory address 0xdeadbeef1234"
    assert normalize_text(text) == "Failed task <uuid> at memory address <hex>"


def test_normalize_iso_timestamp():
    text = "Incident started at 2026-09-28T14:30:00Z on host-1"
    assert normalize_text(text) == "Incident started at <ts> on host-<n>"
