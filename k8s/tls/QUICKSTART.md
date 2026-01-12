# Unity TLS/HTTPS Quick Start Guide

## Current Status Summary

**Already Configured:**
- ✓ cert-manager installed and running
- ✓ ClusterIssuer `selfsigned-issuer` is ready
- ✓ Certificate `unity-tls` is issued and ready
- ✓ TLS secret `unity-tls-cert` exists
- ✓ Ingress file updated with TLS configuration

**What You Need to Do:**
Apply the TLS configuration to activate HTTPS

---

## Option 1: Simple TLS (Recommended for most users)

Uses standard Kubernetes Ingress with TLS enabled.

```bash
# Deploy TLS configuration
/home/holon/Projects/unity/k8s/tls/deploy-tls.sh

# Verify deployment
/home/holon/Projects/unity/k8s/tls/verify-tls.sh
```

**Features:**
- HTTPS on unity.homelab.local and ui.homelab.local
- HTTP still works (no automatic redirect)
- Standard Kubernetes Ingress

---

## Option 2: Advanced TLS with HTTP Redirect

Uses Traefik IngressRoute CRDs with automatic HTTP->HTTPS redirect.

```bash
# Deploy advanced TLS configuration
/home/holon/Projects/unity/k8s/tls/deploy-tls-advanced.sh

# Verify deployment
/home/holon/Projects/unity/k8s/tls/verify-tls.sh
```

**Features:**
- HTTPS on unity.homelab.local and ui.homelab.local
- Automatic HTTP->HTTPS redirect (permanent 308)
- Traefik IngressRoute with Middleware

---

## Manual Deployment (Step by Step)

If you prefer to apply manually:

### 1. Apply ClusterIssuer and Certificate
```bash
kubectl apply -f /home/holon/Projects/unity/k8s/tls/selfsigned-issuer.yaml
```

### 2. Wait for certificate
```bash
kubectl get certificate -n unity -w
# Wait until unity-tls shows READY=True
```

### 3. Choose ingress type:

**Option A: Standard Ingress**
```bash
kubectl apply -f /home/holon/Projects/unity/k8s/deployments/ingress.yaml
```

**Option B: Traefik IngressRoute (with redirect)**
```bash
# Delete standard ingress first
kubectl delete ingress unity-ingress -n unity

# Apply IngressRoute
kubectl apply -f /home/holon/Projects/unity/k8s/tls/ingress-https-fixed.yaml
```

---

## Testing Your Setup

### 1. Add hosts to /etc/hosts (if not already done)
```bash
echo "127.0.0.1 unity.homelab.local ui.homelab.local" | sudo tee -a /etc/hosts
```

### 2. Test HTTPS endpoints
```bash
# Backend health check
curl -k https://unity.homelab.local/health

# Frontend
curl -k https://ui.homelab.local

# Check certificate
openssl s_client -connect unity.homelab.local:443 -servername unity.homelab.local </dev/null 2>/dev/null | openssl x509 -noout -text
```

### 3. Test HTTP redirect (if using Option 2)
```bash
curl -I http://unity.homelab.local
# Should return: HTTP/1.1 308 Permanent Redirect
# Location: https://unity.homelab.local
```

### 4. Browser access
Open in your browser:
- https://unity.homelab.local
- https://ui.homelab.local

**Note:** You'll see a certificate warning because it's self-signed. Click "Advanced" and "Accept Risk" to proceed.

---

## Troubleshooting

### Certificate not ready
```bash
# Check certificate status
kubectl describe certificate unity-tls -n unity

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager -f
```

### HTTPS not working
```bash
# Check ingress
kubectl describe ingress unity-ingress -n unity

# Or check IngressRoute
kubectl get ingressroute -n unity

# Check Traefik logs
kubectl logs -n kube-system -l app.kubernetes.io/name=traefik -f
```

### "Connection refused" errors
```bash
# Verify services are running
kubectl get pods -n unity
kubectl get svc -n unity

# Check if ports are correct
kubectl describe svc backend-service -n unity
kubectl describe svc frontend-service -n unity
```

---

## Production Deployment (Let's Encrypt)

For production with valid certificates:

### 1. Apply Let's Encrypt ClusterIssuer
```bash
kubectl apply -f /home/holon/Projects/unity/issuers.yaml
```

### 2. Update Certificate to use Let's Encrypt
Edit `/home/holon/Projects/unity/k8s/tls/selfsigned-issuer.yaml`:
```yaml
issuerRef:
  name: letsencrypt-cloudflare  # Changed from selfsigned-issuer
  kind: ClusterIssuer
```

### 3. Ensure Cloudflare API token secret exists
```bash
kubectl create secret generic cloudflare-api-token \
  --namespace=unity \
  --from-literal=api-token=YOUR_CLOUDFLARE_API_TOKEN
```

### 4. Update ingress annotation
Change `cert-manager.io/cluster-issuer: selfsigned-issuer` to `letsencrypt-cloudflare`

### 5. Delete old certificate and secret
```bash
kubectl delete certificate unity-tls -n unity
kubectl delete secret unity-tls-cert -n unity
```

### 6. Reapply
```bash
kubectl apply -f /home/holon/Projects/unity/k8s/tls/selfsigned-issuer.yaml
kubectl apply -f /home/holon/Projects/unity/k8s/deployments/ingress.yaml
```

---

## Files Overview

| File | Purpose |
|------|---------|
| `selfsigned-issuer.yaml` | ClusterIssuer and Certificate definitions |
| `ingress-https-fixed.yaml` | Traefik IngressRoute with TLS and redirect |
| `deploy-tls.sh` | Automated deployment script (standard) |
| `deploy-tls-advanced.sh` | Automated deployment script (advanced) |
| `verify-tls.sh` | Verification and testing script |
| `README.md` | Comprehensive documentation |
| `QUICKSTART.md` | This file |

---

## Resources

- **Certificate Secret**: `unity-tls-cert` (namespace: unity)
- **ClusterIssuer**: `selfsigned-issuer`
- **Certificate**: `unity-tls` (namespace: unity)
- **Valid Hosts**: unity.homelab.local, ui.homelab.local, *.homelab.local
- **Validity**: 1 year (8760h)
- **Renewal**: 30 days before expiry (720h)

---

## Need Help?

1. Run verification script: `/home/holon/Projects/unity/k8s/tls/verify-tls.sh`
2. Check cert-manager logs: `kubectl logs -n cert-manager deployment/cert-manager`
3. Check Traefik logs: `kubectl logs -n kube-system -l app.kubernetes.io/name=traefik`
4. Describe certificate: `kubectl describe certificate unity-tls -n unity`
