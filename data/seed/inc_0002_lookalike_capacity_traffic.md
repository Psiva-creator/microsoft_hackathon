# Post-Mortem: INC-0002 - postgres-primary write failure due to connection limits under traffic spike
## Summary
Incident INC-0002 affecting postgres-primary, orders-service.
## Symptoms
- HTTP 502 Bad Gateway under surge
- rate limit exceeded
- Logs: HTTP 429 Too Many Requests: Ingress gateway connection queue full
## Root Cause
Root cause identified as capacity_traffic: postgres-primary write failure due to connection limits under traffic spike.
## Resolution Steps
1. Consulted runbook RB-bad-deploy-rollback.
2. Restarted impacted pods in postgres-primary.
