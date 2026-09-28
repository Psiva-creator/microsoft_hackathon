# Post-Mortem: orders-service connection starvation from internal DNS timeout
## Summary
Incident affecting orders-service, postgres-primary. Visible symptoms mirror connection_pool but root cause differs.
## Symptoms
- Error rate above 20%.
- Elevated response times.
- Logs: Error in database client: orders-service connection starvation from internal DNS timeout.
## Root Cause
Underlying root cause identified as network_dns: orders-service connection starvation from internal DNS timeout.
## Resolution Steps
1. Confirmed symptoms are not due to connection_pool by inspecting logs.
2. Applied remediation for network_dns.
3. Restored service availability.
