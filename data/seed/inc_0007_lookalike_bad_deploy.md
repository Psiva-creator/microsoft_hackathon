# Post-Mortem: payments-gateway crash on startup after missing config env var
## Summary
Incident affecting payments-gateway. Users observed severe latency and 500 errors.
## Symptoms
- Error rate above 20%.
- Elevated response times.
- Logs: Error in database client: payments-gateway crash on startup after missing config env var.
## Root Cause
Underlying root cause identified as bad_deploy: payments-gateway crash on startup after missing config env var.
## Resolution Steps
1. Identified root cause in system metrics.
2. Applied recovery steps according to standard runbook.
3. System returned to normal operating capacity.
