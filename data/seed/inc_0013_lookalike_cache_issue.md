# Post-Mortem: web-frontend slow render caused by Redis memory eviction
## Summary
Incident affecting web-frontend, redis-cache. Users observed severe latency and 500 errors.
## Symptoms
- Error rate above 20%.
- Elevated response times.
- Logs: Error in database client: web-frontend slow render caused by Redis memory eviction.
## Root Cause
Underlying root cause identified as cache_issue: web-frontend slow render caused by Redis memory eviction.
## Resolution Steps
1. Identified root cause in system metrics.
2. Applied recovery steps according to standard runbook.
3. System returned to normal operating capacity.
