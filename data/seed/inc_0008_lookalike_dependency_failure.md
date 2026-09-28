# Post-Mortem: payments-gateway crash on startup after third-party bank sandbox API down
## Summary
Incident affecting payments-gateway. Visible symptoms mirror bad_deploy but root cause differs.
## Symptoms
- Error rate above 20%.
- Elevated response times.
- Logs: Error in database client: payments-gateway crash on startup after third-party bank sandbox API down.
## Root Cause
Underlying root cause identified as dependency_failure: payments-gateway crash on startup after third-party bank sandbox API down.
## Resolution Steps
1. Confirmed symptoms are not due to bad_deploy by inspecting logs.
2. Applied remediation for dependency_failure.
3. Restored service availability.
