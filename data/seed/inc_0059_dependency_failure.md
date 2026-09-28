# Post-Mortem: Incident INC-0059
## Summary
Service outage affecting inventory-service, kafka-orders, postgres-primary for 19 minutes.
## Symptoms
- HTTP 500 and 503 errors on endpoints.
- Error logs: Connection failed to 10.0.1.118:5432 with status 503.
## Root Cause
Identified issue in dependency_failure affecting subsystem stability.
## Resolution Steps
1. Investigated logs from inventory-service.
2. Restarted failed components.
3. Validated health check.
