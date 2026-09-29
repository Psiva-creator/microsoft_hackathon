# Post-Mortem: Incident INC-0036
## Summary
Service outage affecting orders-service, inventory-service for 59 minutes.
## Symptoms
- cache hit ratio dropped from 95% to 40%
- database CPU surge
- Error logs: OOM command not allowed when used memory > 'maxmemory' in redis-cache
## Root Cause
Identified issue in cache_issue affecting subsystem stability: cache hit ratio dropped from 95% to 40%.
## Resolution Steps
1. Followed runbook RB-cache-stampede.
2. Investigated logs from orders-service and applied fix.
3. Validated health check.
