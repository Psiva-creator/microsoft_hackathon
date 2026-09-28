# Post-Mortem: Incident INC-0015
## Summary
Service outage affecting checkout-api, web-frontend, inventory-service for 58 minutes.
## Symptoms
- HTTP 500 and 503 errors on endpoints.
- Error logs: Connection failed to 10.0.8.36:5432 with status 503.
## Root Cause
Identified issue in memory_leak affecting subsystem stability.
## Resolution Steps
1. Investigated logs from checkout-api.
2. Restarted failed components.
3. Validated health check.
