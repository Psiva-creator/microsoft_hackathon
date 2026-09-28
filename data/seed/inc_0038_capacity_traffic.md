# Post-Mortem: Incident INC-0038
## Summary
Service outage affecting auth-service for 50 minutes.
## Symptoms
- HTTP 500 and 503 errors on endpoints.
- Error logs: Connection failed to 10.0.5.169:9092 with status 503.
## Root Cause
Identified issue in capacity_traffic affecting subsystem stability.
## Resolution Steps
1. Investigated logs from auth-service.
2. Restarted failed components.
3. Validated health check.
