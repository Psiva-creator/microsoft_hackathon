# Post-Mortem: Incident INC-0041
## Summary
Service outage affecting orders-service for 52 minutes.
## Symptoms
- HTTP 500 and 503 errors on endpoints.
- Error logs: Connection failed to 10.0.3.87:5432 with status 503.
## Root Cause
Identified issue in bad_deploy affecting subsystem stability.
## Resolution Steps
1. Investigated logs from orders-service.
2. Restarted failed components.
3. Validated health check.
