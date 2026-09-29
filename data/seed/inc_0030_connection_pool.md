# Post-Mortem: Incident INC-0030
## Summary
Service outage affecting inventory-service, postgres-primary, orders-service for 60 minutes.
## Symptoms
- HTTP 503 errors on checkout
- HikariPool saturation
- Error logs: HikariPool-1 - Connection is not available, request timed out after 30000ms
## Root Cause
Identified issue in connection_pool affecting subsystem stability: HTTP 503 errors on checkout.
## Resolution Steps
1. Followed runbook RB-db-pool-exhaustion.
2. Investigated logs from inventory-service and applied fix.
3. Validated health check.
