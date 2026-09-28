# Post-Mortem: orders-service connection starvation from unclosed session
## Summary
Incident affecting orders-service, postgres-primary. Users observed severe latency and 500 errors.
## Symptoms
- Error rate above 20%.
- Elevated response times.
- Logs: Error in database client: orders-service connection starvation from unclosed session.
## Root Cause
Underlying root cause identified as connection_pool: orders-service connection starvation from unclosed session.
## Resolution Steps
1. Identified root cause in system metrics.
2. Applied recovery steps according to standard runbook.
3. System returned to normal operating capacity.
