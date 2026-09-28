# Post-Mortem: Incident INC-0060
## Summary
Service outage affecting orders-service, auth-service, inventory-service for 30 minutes.
## Symptoms
- HTTP 500 and 503 errors on endpoints.
- Error logs: Connection failed to 10.0.12.226:5432 with status 503.
## Root Cause
Identified issue in connection_pool affecting subsystem stability.
## Resolution Steps
1. Investigated logs from orders-service.
2. Restarted failed components.
3. Validated health check.
