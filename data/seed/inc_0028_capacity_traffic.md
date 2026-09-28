# Post-Mortem: Incident INC-0028
## Summary
Service outage affecting kafka-orders, redis-cache, notification-worker for 50 minutes.
## Symptoms
- HTTP 500 and 503 errors on endpoints.
- Error logs: Connection failed to 10.0.9.36:6379 with status 503.
## Root Cause
Identified issue in capacity_traffic affecting subsystem stability.
## Resolution Steps
1. Investigated logs from kafka-orders.
2. Restarted failed components.
3. Validated health check.
