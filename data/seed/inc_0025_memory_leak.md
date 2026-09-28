# Post-Mortem: Incident INC-0025
## Summary
Service outage affecting checkout-api, payments-gateway, orders-service for 55 minutes.
## Symptoms
- HTTP 500 and 503 errors on endpoints.
- Error logs: Connection failed to 10.0.15.98:8000 with status 503.
## Root Cause
Identified issue in memory_leak affecting subsystem stability.
## Resolution Steps
1. Investigated logs from checkout-api.
2. Restarted failed components.
3. Validated health check.
