# Post-Mortem: Incident INC-0018
## Summary
Service outage affecting orders-service for 29 minutes.
## Symptoms
- HTTP 502 Bad Gateway under surge
- rate limit exceeded
- Error logs: upstream connect error or disconnect/reset before headers. reset reason: connection termination
## Root Cause
Identified issue in capacity_traffic affecting subsystem stability: HTTP 502 Bad Gateway under surge.
## Resolution Steps
1. Followed runbook RB-bad-deploy-rollback.
2. Investigated logs from orders-service and applied fix.
3. Validated health check.
