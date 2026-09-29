# Post-Mortem: INC-0010 - web-frontend slow render caused by Redis memory eviction
## Summary
Incident INC-0010 affecting web-frontend, redis-cache.
## Symptoms
- cache hit ratio dropped from 95% to 40%
- database CPU surge
- Logs: redis.exceptions.ConnectionError: Error 111 connecting to 10.0.1.20:6379. Connection refused
## Root Cause
Root cause identified as cache_issue: web-frontend slow render caused by Redis memory eviction.
## Resolution Steps
1. Consulted runbook RB-cache-stampede.
2. Restarted impacted pods in web-frontend.
