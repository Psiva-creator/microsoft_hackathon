# Post-Mortem: Incident INC-0023
## Summary
Service outage affecting checkout-api, orders-service for 55 minutes.
## Symptoms
- HTTP 500 and 503 errors on endpoints.
- Error logs: Connection failed to 10.0.13.72:9092 with status 503.
## Root Cause
Identified issue in disk_full affecting subsystem stability.
## Resolution Steps
1. Investigated logs from checkout-api.
2. Restarted failed components.
3. Validated health check.
