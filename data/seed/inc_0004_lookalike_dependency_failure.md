# Post-Mortem: INC-0004 - payments-gateway crash on startup after third-party bank sandbox API down
## Summary
Incident INC-0004 affecting payments-gateway.
## Symptoms
- third-party vendor API timeouts
- upstream 500 responses
- Logs: CircuitBreakerOpenException: Downstream service orders-service circuit breaker tripped
## Root Cause
Root cause identified as dependency_failure: payments-gateway crash on startup after third-party bank sandbox API down.
## Resolution Steps
1. Consulted runbook RB-bad-deploy-rollback.
2. Restarted impacted pods in payments-gateway.
