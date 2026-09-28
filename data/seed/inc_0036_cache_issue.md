# Post-Mortem: Incident INC-0036
## Summary
Service outage affecting postgres-primary, kafka-orders, web-frontend for 30 minutes.
## Symptoms
- HTTP 500 and 503 errors on endpoints.
- Error logs: Connection failed to 10.0.12.225:8000 with status 503.
## Root Cause
Identified issue in cache_issue affecting subsystem stability.
## Resolution Steps
1. Investigated logs from postgres-primary.
2. Restarted failed components.
3. Validated health check.
