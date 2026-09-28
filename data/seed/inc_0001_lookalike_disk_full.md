# Post-Mortem: INC-0001 - postgres-primary write failure due to disk exhaustion
## Summary
Incident INC-0001 affecting postgres-primary, orders-service.
## Symptoms
- database write rejections
- disk capacity at 100%
- Logs: java.io.IOException: Disk space is full for path /var/lib/postgresql/data
## Root Cause
Root cause identified as disk_full: postgres-primary write failure due to disk exhaustion.
## Resolution Steps
1. Consulted runbook RB-disk-full.
2. Restarted impacted pods in postgres-primary.
