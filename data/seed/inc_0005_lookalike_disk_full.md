# Post-Mortem: postgres-primary write failure due to disk exhaustion
## Summary
Incident affecting postgres-primary, orders-service. Users observed severe latency and 500 errors.
## Symptoms
- Error rate above 20%.
- Elevated response times.
- Logs: Error in database client: postgres-primary write failure due to disk exhaustion.
## Root Cause
Underlying root cause identified as disk_full: postgres-primary write failure due to disk exhaustion.
## Resolution Steps
1. Identified root cause in system metrics.
2. Applied recovery steps according to standard runbook.
3. System returned to normal operating capacity.
