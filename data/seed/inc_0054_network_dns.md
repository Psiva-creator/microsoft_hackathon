# Post-Mortem: Incident INC-0054
## Summary
Service outage affecting postgres-primary, checkout-api, inventory-service for 42 minutes.
## Symptoms
- CoreDNS lookup failures
- service discovery timeouts
- Error logs: dial tcp: lookup postgres-primary on 10.96.0.10:53: no such host
## Root Cause
Identified issue in network_dns affecting subsystem stability: CoreDNS lookup failures.
## Resolution Steps
1. Followed runbook RB-dns-resolution-failure.
2. Investigated logs from postgres-primary and applied fix.
3. Validated health check.
