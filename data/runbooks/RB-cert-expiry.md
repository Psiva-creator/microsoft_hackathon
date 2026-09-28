---
id: RB-cert-expiry
title: TLS Certificate Expiry Remediation
services: [payments-gateway, auth-service, web-frontend]
---

# RB-cert-expiry: TLS Certificate Expiry Remediation

## Symptoms
- Inbound API requests failing with TLS/SSL errors.
- Client logs showing: `x509: certificate has expired` or `SSL_ERROR_EXPIRED_CERT_HASH`.
- Upstream payment processors or web clients unable to establish secure handshakes.

## Verification Steps
1. Verify the certificate validity dates on the affected endpoint:
   ```bash
   echo | openssl s_client -servername <domain> -connect <domain>:443 2>/dev/null | openssl x509 -noout -dates
   ```
2. Check automated cert-manager or Let's Encrypt renewal logs:
   ```bash
   kubectl describe certificate <cert-name>
   kubectl logs -n cert-manager -l app=cert-manager --tail=100
   ```

## Remediation Steps
1. Trigger an emergency renewal via cert-manager:
   ```bash
   kubectl renew certificate <cert-name>
   ```
2. If automated renewal fails due to DNS challenge failure or rotated secrets:
   - Manually provision emergency certificate from backup provider or Vault.
   - Update Kubernetes secret:
     ```bash
     kubectl create secret tls <cert-secret-name> --cert=tls.crt --key=tls.key --dry-run=client -o yaml | kubectl apply -f -
     ```
3. Restart ingress controllers to reload the new certificate into memory:
   ```bash
   kubectl rollout restart deployment/ingress-nginx-controller
   ```
4. Confirm SSL handshake succeeds via curl:
   ```bash
   curl -Iv https://<domain>/health
   ```
