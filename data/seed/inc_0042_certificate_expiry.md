# Post-Mortem: Incident INC-0042
## Summary
Service outage affecting inventory-service, checkout-api for 28 minutes.
## Symptoms
- TLS handshake failures
- external webhook delivery failure
- Error logs: x509: certificate has expired for domain api.payments.internal
## Root Cause
Identified issue in certificate_expiry affecting subsystem stability: TLS handshake failures.
## Resolution Steps
1. Followed runbook RB-cert-expiry.
2. Investigated logs from inventory-service and applied fix.
3. Validated health check.
