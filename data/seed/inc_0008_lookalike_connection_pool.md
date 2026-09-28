# Post-Mortem: INC-0008 - orders-service connection starvation from unclosed session
## Summary
Incident INC-0008 affecting orders-service, postgres-primary.
## Symptoms
- HTTP 503 errors on checkout
- HikariPool saturation
- Logs: ActiveConnectionsExhausted: Pool max size 50 reached in OrderRepository.getConnection()
## Root Cause
Root cause identified as connection_pool: orders-service connection starvation from unclosed session.
## Resolution Steps
1. Consulted runbook RB-db-pool-exhaustion.
2. Restarted impacted pods in orders-service.
