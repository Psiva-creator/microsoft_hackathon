# Post-Mortem: Incident INC-0039
## Summary
Service outage affecting inventory-service, auth-service for 29 minutes.
## Symptoms
- third-party vendor API timeouts
- upstream 500 responses
- Error logs: StripeConnectionError: Error communicating with Stripe api.stripe.com after 10000ms
## Root Cause
Identified issue in dependency_failure affecting subsystem stability: third-party vendor API timeouts.
## Resolution Steps
1. Followed runbook RB-bad-deploy-rollback.
2. Investigated logs from inventory-service and applied fix.
3. Validated health check.
