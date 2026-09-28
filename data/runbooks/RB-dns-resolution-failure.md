---
id: RB-dns-resolution-failure
title: Cluster DNS Resolution Failure Recovery
services: [checkout-api, orders-service, inventory-service, payments-gateway]
---

# RB-dns-resolution-failure: Cluster DNS Resolution Failure Recovery

## Symptoms
- Services fail to connect to downstream databases or APIs with: `dial tcp: lookup postgres-primary: no such host`.
- Sporadic timeouts across multiple independent services simultaneously.
- CoreDNS pods evicted, OOM-killed, or CPU throttled.

## Verification Steps
1. Verify CoreDNS pod status and restart count:
   ```bash
   kubectl get pods -n kube-system -l k8s-app=kube-dns
   ```
2. Test internal DNS lookup from inside an application container:
   ```bash
   kubectl exec -it <service-pod> -- nslookup postgres-primary.default.svc.cluster.local
   ```
3. Inspect CoreDNS error logs:
   ```bash
   kubectl logs -n kube-system -l k8s-app=kube-dns --tail=100
   ```

## Remediation Steps
1. Restart CoreDNS deployments cleanly:
   ```bash
   kubectl rollout restart -n kube-system deployment/coredns
   ```
2. Scale up CoreDNS replicas if under heavy query load:
   ```bash
   kubectl scale -n kube-system deployment/coredns --replicas=5
   ```
3. Apply PodDisruptionBudget (PDB) to prevent node drain eviction:
   ```bash
   kubectl apply -f k8s/coredns-pdb.yaml
   ```
4. Verify resolution latency returns below 5ms.
