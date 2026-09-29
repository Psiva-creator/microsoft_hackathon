# Post-Mortem: Incident INC-0048
## Summary
Service outage affecting kafka-orders, checkout-api, web-frontend for 22 minutes.
## Symptoms
- HTTP 502 Bad Gateway under surge
- rate limit exceeded
- Error logs: upstream connect error or disconnect/reset before headers. reset reason: connection termination
## Root Cause
Identified issue in capacity_traffic affecting subsystem stability: HTTP 502 Bad Gateway under surge.
## Resolution Steps
1. Followed runbook RB-bad-deploy-rollback.
2. Investigated logs from kafka-orders and applied fix.
3. Validated health check.
