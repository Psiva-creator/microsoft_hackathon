# Post-Mortem: INC-0009 - orders-service connection starvation from internal DNS timeout
## Summary
Incident INC-0009 affecting orders-service, postgres-primary.
## Symptoms
- CoreDNS lookup failures
- service discovery timeouts
- Logs: dial tcp: lookup postgres-primary on 10.96.0.10:53: no such host
## Root Cause
Root cause identified as network_dns: orders-service connection starvation from internal DNS timeout.
## Resolution Steps
1. Consulted runbook RB-dns-resolution-failure.
2. Restarted impacted pods in orders-service.
