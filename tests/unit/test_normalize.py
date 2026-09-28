from app.core.normalize import normalize_dict, normalize_text


def test_normalize_ip_and_numbers():
    t1 = "Connection refused to 10.0.3.7:5432 after 30001ms"
    t2 = "Connection refused to 10.0.9.2:5432 after 29877ms"
    assert normalize_text(t1) == "Connection refused to <ip>:<n> after <n>ms"
    assert normalize_text(t2) == "Connection refused to <ip>:<n> after <n>ms"
    assert normalize_text(t1) == normalize_text(t2)


def test_normalize_ipv6_addresses():
    # Full IPv6
    assert (
        normalize_text("Connected to 2001:0db8:85a3:0000:0000:8a2e:0370:7334 on port 443")
        == "Connected to <ip> on port <n>"
    )
    # Compressed IPv6 loopback
    assert normalize_text("Listening on ::1:8080") == "Listening on <ip>:<n>"
    # Compressed link-local
    assert normalize_text("Ping to fe80::1 failed") == "Ping to <ip> failed"
    # Mixed compressed
    assert normalize_text("Route via 2001:db8::1 metric 10") == "Route via <ip> metric <n>"


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


def test_normalize_http_status_with_colons_equals_and_json():
    # Colons and equals formatting
    assert normalize_text("status: 500 server error") == "status: 500 server error"
    assert normalize_text("status=500") == "status=500"
    assert normalize_text("status_code: 502") == "status_code: 502"
    assert normalize_text("status_code=502") == "status_code=502"
    assert normalize_text("statusCode: 503") == "statusCode: 503"
    assert normalize_text("code: 404") == "code: 404"
    assert normalize_text("code=404") == "code=404"
    assert normalize_text("error: 504") == "error: 504"
    assert normalize_text('{"status": 500, "error": "Internal Error"}') == '{"status": 500, "error": "Internal Error"}'


def test_normalize_http_versions_and_access_logs():
    # Various HTTP protocol versions
    assert normalize_text("HTTP/1.0 404 Not Found") == "HTTP/1.0 404 Not Found"
    assert normalize_text("HTTP/2 503 Service Unavailable") == "HTTP/2 503 Service Unavailable"
    assert normalize_text("HTTP/2.0 500 Internal Server Error") == "HTTP/2.0 500 Internal Server Error"
    assert normalize_text("HTTP/3 504 Gateway Timeout") == "HTTP/3 504 Gateway Timeout"

    # Web server access log format: "GET /checkout HTTP/1.1" 502 1450
    access_log = '10.0.1.25 - - [28/Sep/2026:14:30:00 +0000] "GET /checkout HTTP/1.1" 502 1450'
    assert normalize_text(access_log) == '<ip> - - [<ts>] "GET /checkout HTTP/1.1" 502 <n>'


def test_normalize_standalone_http_reason_phrases():
    # Reason phrases without explicit 'http' prefix
    assert normalize_text("Upstream returned 502 Bad Gateway") == "Upstream returned 502 Bad Gateway"
    assert normalize_text("Gateway yielded 504 Gateway Timeout") == "Gateway yielded 504 Gateway Timeout"
    assert normalize_text("Service returned 503 Service Unavailable") == "Service returned 503 Service Unavailable"
    assert normalize_text("Endpoint responded with 404 Not Found") == "Endpoint responded with 404 Not Found"
    assert normalize_text("Auth failed with 401 Unauthorized") == "Auth failed with 401 Unauthorized"
    assert normalize_text("Client error 400 Bad Request") == "Client error 400 Bad Request"
    assert normalize_text("Rate limited 429 Too Many Requests") == "Rate limited 429 Too Many Requests"


def test_non_status_numbers_abstracted():
    assert normalize_text("Query took 503 ms") == "Query took <n> ms"
    assert normalize_text("Total 500 records found") == "Total <n> records found"
    assert normalize_text("Worker PID 502 killed") == "Worker PID <n> killed"
    assert normalize_text("Listening on port 5000") == "Listening on port <n>"
    assert normalize_text("Processed 100 items out of 250") == "Processed <n> items out of <n>"


def test_normalize_uuid_and_hex():
    text = "Failed task c3b91a27-0402-466d-a11d-2856d302a901 at memory address 0xdeadbeef1234"
    assert normalize_text(text) == "Failed task <uuid> at memory address <hex>"

    # UUID with braces
    braced = "Error in {c3b91a27-0402-466d-a11d-2856d302a901} context"
    assert normalize_text(braced) == "Error in <uuid> context"


def test_normalize_timestamps_all_formats():
    # ISO-8601
    assert (
        normalize_text("Incident started at 2026-09-28T14:30:00Z on host-1")
        == "Incident started at <ts> on host-<n>"
    )
    assert (
        normalize_text("Started at 2026-09-28 14:30:00.123456+05:30")
        == "Started at <ts>"
    )

    # Go / Nginx slash dates
    assert normalize_text("2026/09/28 14:30:00 [error] failed") == "<ts> [error] failed"

    # Common Log Format
    assert normalize_text("28/Sep/2026:14:30:00 +0000 GET /index") == "<ts> GET /index"

    # RFC 2822
    assert normalize_text("Date: Mon, 28 Sep 2026 14:30:00 GMT") == "Date: <ts>"

    # Syslog
    assert normalize_text("Sep 28 14:30:00 host app: error") == "<ts> host app: error"
    assert normalize_text("Sep  4 14:30:00.500 host app: timeout") == "<ts> host app: timeout"

    # Epoch timestamp labeled
    assert normalize_text("event timestamp=1727541000 occurred") == "event timestamp=<ts> occurred"
    assert normalize_text("log ts: 1727541000.123 error") == "log ts:<ts> error"


def test_normalize_redaction_integration():
    # Secrets scrubbed before normalization
    raw = "Request failed for key AKIAIOSFODNN7EXAMPLE at 2026-09-28T14:30:00Z with status 500"
    assert normalize_text(raw) == "Request failed for key <redacted> at <ts> with status 500"


def test_normalize_dict():
    payload = {
        "event": "alert",
        "timestamp": "2026-09-28T14:30:00Z",
        "message": "Connection refused to 10.0.3.7:5432 after 30001ms",
        "details": {
            "error": "status: 502 Bad Gateway",
            "host": "host-12",
        },
        "logs": [
            "HTTP/1.1 502 Bad Gateway",
            "took 502 ms to fail",
        ],
    }

    normalized = normalize_dict(payload)
    assert normalized["timestamp"] == "<ts>"
    assert normalized["message"] == "Connection refused to <ip>:<n> after <n>ms"
    assert normalized["details"]["error"] == "status: 502 Bad Gateway"
    assert normalized["details"]["host"] == "host-<n>"
    assert normalized["logs"][0] == "HTTP/1.1 502 Bad Gateway"
    assert normalized["logs"][1] == "took <n> ms to fail"
