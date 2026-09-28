# Post-Mortem: Incident INC-0042
## Summary
Service outage affecting orders-service, notification-worker, web-frontend for 17 minutes.
## Symptoms
- HTTP 500 and 503 errors on endpoints.
- Error logs: Connection failed to 10.0.2.59:5432 with status 503.
## Root Cause
Identified issue in certificate_expiry affecting subsystem stability.
## Resolution Steps
1. Investigated logs from orders-service.
2. Restarted failed components.
3. Validated health check.
