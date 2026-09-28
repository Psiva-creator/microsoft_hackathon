# Post-Mortem: Incident INC-0026
## Summary
Service outage affecting auth-service, orders-service, postgres-primary for 35 minutes.
## Symptoms
- HTTP 500 and 503 errors on endpoints.
- Error logs: Connection failed to 10.0.8.211:5432 with status 503.
## Root Cause
Identified issue in cache_issue affecting subsystem stability.
## Resolution Steps
1. Investigated logs from auth-service.
2. Restarted failed components.
3. Validated health check.
