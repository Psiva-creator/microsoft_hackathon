---
id: RB-bad-deploy-rollback
title: Emergency Rollback of Defective Deployment
services: [web-frontend, checkout-api, payments-gateway, orders-service, inventory-service]
---

# RB-bad-deploy-rollback: Emergency Rollback of Defective Deployment

## Symptoms
- Immediate spike in 5xx HTTP error rates within 15 minutes of a new deployment.
- Elevated error logs matching newly introduced code paths.
- CrashLoopBackOff or healthcheck probe failures on newly deployed pods.

## Verification Steps
1. Identify the recent deployment tag and commit hash:
   ```bash
   kubectl rollout history deployment/<service-name>
   ```
2. Inspect differences between the new revision and the previous stable revision:
   ```bash
   git diff <previous_tag>..<current_tag>
   ```
3. Check pod logs for initialization failures or unhandled exceptions:
   ```bash
   kubectl logs -l app=<service-name> --tail=100
   ```

## Remediation Steps
1. Trigger immediate rollout undo to the preceding known-good revision:
   ```bash
   kubectl rollout undo deployment/<service-name>
   ```
2. Verify rollout status of the rollback:
   ```bash
   kubectl rollout status deployment/<service-name>
   ```
3. Confirm error rate drops back to baseline in observability dashboards.
4. Notify engineering team on Slack channel and lock deployment pipeline until hotfix.
