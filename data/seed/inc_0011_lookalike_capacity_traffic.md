# Post-Mortem: INC-0011 - web-frontend slow render caused by flash sale 10x traffic spike
## Summary
Incident INC-0011 affecting web-frontend, redis-cache.
## Symptoms
- HTTP 502 Bad Gateway under surge
- rate limit exceeded
- Logs: HTTP 429 Too Many Requests: Ingress gateway connection queue full
## Root Cause
Root cause identified as capacity_traffic: web-frontend slow render caused by flash sale 10x traffic spike.
## Resolution Steps
1. Consulted runbook RB-bad-deploy-rollback.
2. Restarted impacted pods in web-frontend.
