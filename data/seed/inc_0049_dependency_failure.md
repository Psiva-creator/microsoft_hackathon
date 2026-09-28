# Post-Mortem: Incident INC-0049
## Summary
Service outage affecting auth-service, checkout-api for 20 minutes.
## Symptoms
- HTTP 500 and 503 errors on endpoints.
- Error logs: Connection failed to 10.0.18.215:5432 with status 503.
## Root Cause
Identified issue in dependency_failure affecting subsystem stability.
## Resolution Steps
1. Investigated logs from auth-service.
2. Restarted failed components.
3. Validated health check.
