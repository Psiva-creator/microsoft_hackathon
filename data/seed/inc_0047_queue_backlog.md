# Post-Mortem: Incident INC-0047
## Summary
Service outage affecting orders-service for 42 minutes.
## Symptoms
- HTTP 500 and 503 errors on endpoints.
- Error logs: Connection failed to 10.0.18.115:6379 with status 503.
## Root Cause
Identified issue in queue_backlog affecting subsystem stability.
## Resolution Steps
1. Investigated logs from orders-service.
2. Restarted failed components.
3. Validated health check.
