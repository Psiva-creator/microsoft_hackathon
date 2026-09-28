# Post-Mortem: Incident INC-0058
## Summary
Service outage affecting orders-service, postgres-primary for 57 minutes.
## Symptoms
- HTTP 500 and 503 errors on endpoints.
- Error logs: Connection failed to 10.0.9.102:6379 with status 503.
## Root Cause
Identified issue in capacity_traffic affecting subsystem stability.
## Resolution Steps
1. Investigated logs from orders-service.
2. Restarted failed components.
3. Validated health check.
