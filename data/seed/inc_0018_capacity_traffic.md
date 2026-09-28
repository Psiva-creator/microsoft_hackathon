# Post-Mortem: Incident INC-0018
## Summary
Service outage affecting notification-worker, inventory-service for 36 minutes.
## Symptoms
- HTTP 500 and 503 errors on endpoints.
- Error logs: Connection failed to 10.0.6.179:9092 with status 503.
## Root Cause
Identified issue in capacity_traffic affecting subsystem stability.
## Resolution Steps
1. Investigated logs from notification-worker.
2. Restarted failed components.
3. Validated health check.
