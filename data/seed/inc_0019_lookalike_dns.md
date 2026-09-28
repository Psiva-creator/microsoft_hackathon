# Post-Mortem: INC-0019 - CoreDNS Pod Eviction Causing Database Disconnection

## Executive Summary
On 2026-08-02 at 18:30 UTC, checkout-api returned widespread 503 errors and connection timeouts for 35 minutes. While symptoms closely resembled pool exhaustion (INC-0007), the root cause was cluster DNS resolution failure.

## Symptoms
- checkout-api 503 errors and client-facing timeouts.
- Error log: dial tcp: lookup postgres-primary on 10.96.0.10:53: no such host.
- Latency spike across multiple internal services simultaneously.

## Root Cause
CoreDNS pods were evicted from worker nodes under sudden memory pressure. checkout-api was unable to resolve the hostname postgres-primary, causing subsequent connection attempts to fail.

## Resolution Steps
1. Consulted runbook RB-dns-resolution-failure.
2. Restarted CoreDNS deployment and scaled replicas from 2 to 6.
3. Added PodDisruptionBudget and dedicated resource guarantees to CoreDNS.
