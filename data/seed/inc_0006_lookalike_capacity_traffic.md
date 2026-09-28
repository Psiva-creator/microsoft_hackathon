# Post-Mortem: postgres-primary write failure due to connection limits under traffic spike
## Summary
Incident affecting postgres-primary, orders-service. Visible symptoms mirror disk_full but root cause differs.
## Symptoms
- Error rate above 20%.
- Elevated response times.
- Logs: Error in database client: postgres-primary write failure due to connection limits under traffic spike.
## Root Cause
Underlying root cause identified as capacity_traffic: postgres-primary write failure due to connection limits under traffic spike.
## Resolution Steps
1. Confirmed symptoms are not due to disk_full by inspecting logs.
2. Applied remediation for capacity_traffic.
3. Restored service availability.
