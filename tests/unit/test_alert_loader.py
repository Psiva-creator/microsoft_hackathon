from app.ingestion.loaders import load_alert_payload


def test_load_alert_payload_datadog():
    datadog_payload = {
        "title": "checkout-api connection timeout",
        "service": "checkout-api",
        "priority": "P1",
        "text": "HikariPool-1 connection request timed out after 30000ms",
        "tags": {"env": "prod", "service": "checkout-api"},
    }
    doc = load_alert_payload(datadog_payload, source_id="alert-101")
    assert doc.source_type == "alert"
    assert doc.source_id == "alert-101"
    assert "HikariPool-1" in doc.text
    assert doc.metadata["service"] == "checkout-api"
    assert doc.metadata["severity"] == "P1"


def test_load_alert_payload_prometheus():
    prom_payload = {
        "alertname": "PaymentsGatewayDown",
        "service": "payments-gateway",
        "severity": "critical",
        "description": "payments-gateway ingress returned 502 for > 5m",
    }
    doc = load_alert_payload(prom_payload)
    assert doc.source_type == "alert"
    assert "PaymentsGatewayDown" in doc.text
    assert doc.metadata["severity"] == "critical"
