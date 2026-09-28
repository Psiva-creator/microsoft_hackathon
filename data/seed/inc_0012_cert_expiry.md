# Post-Mortem: INC-0012 - TLS Handshake Failures on payments-gateway

## Executive Summary
On 2026-05-18 at 09:10 UTC, inbound payments gateway requests failed due to expired SSL certificates. The outage lasted 41 minutes before certificate re-issuance and deployment.

## Symptoms
- 100% of external webhook callbacks failed with TLS handshake errors.
- Logs: x509: certificate has expired for domain api.payments.internal.
- Monitoring alert: CertificateExpiryCritical.

## Root Cause
An automated certificate renewal cron job failed silently following a service-account token rotation 3 weeks prior. The renewal process lacked failure alerting.

## Resolution Steps
1. Followed runbook RB-cert-expiry.
2. Manually provisioned wildcard TLS certificate using emergency offline CA.
3. Updated Kubernetes secret tls-payments-gateway and restarted ingress pods.
4. Corrected IAM service-account binding for cert-manager cron job.
