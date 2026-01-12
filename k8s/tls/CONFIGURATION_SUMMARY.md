# Unity TLS/HTTPS Configuration Summary

## Overview
This document provides a complete summary of the TLS/HTTPS configuration for the Unity Kubernetes deployment.

---

## Current State

### Infrastructure Status
| Component | Status | Details |
|-----------|--------|---------|
| cert-manager | ✓ Running | 3 pods in cert-manager namespace |
| ClusterIssuer (selfsigned) | ✓ Ready | For local development |
| ClusterIssuer (letsencrypt) | ✓ Ready | For production |
| ClusterIssuer (smallstep) | ✗ Not Ready | Optional SmallStep CA |
| Certificate (unity-tls) | ✓ Ready | Valid for 1 year |
| TLS Secret | ✓ Exists | unity-tls-cert in unity namespace |
| Ingress | Updated | TLS configuration added |

### Certificate Details
- **Name**: unity-tls
- **Namespace**: unity
- **Secret Name**: unity-tls-cert
- **Issuer**: selfsigned-issuer (ClusterIssuer)
- **Hosts**:
  - unity.homelab.local
  - ui.homelab.local
  - *.homelab.local
- **Duration**: 8760h (1 year)
- **Renewal Window**: 720h (30 days before expiry)
- **Auto-renewal**: Yes (managed by cert-manager)

---

## Configuration Files

### Primary Files (Already Applied)
1. **`/home/holon/Projects/unity/k8s/tls/selfsigned-issuer.yaml`**
   - ClusterIssuer for self-signed certificates
   - Certificate definition for unity-tls
   - Status: Applied and working

2. **`/home/holon/Projects/unity/k8s/deployments/ingress.yaml`**
   - Main Kubernetes Ingress resource
   - Now includes TLS configuration
   - Status: Updated, ready to apply

### Alternative Configuration
3. **`/home/holon/Projects/unity/k8s/tls/ingress-https-fixed.yaml`**
   - Traefik IngressRoute CRDs
   - Includes HTTP->HTTPS redirect middleware
   - More advanced than standard Ingress
   - Use this OR the standard ingress, not both

### Production Issuers
4. **`/home/holon/Projects/unity/issuers.yaml`**
   - Let's Encrypt with Cloudflare DNS-01
   - SmallStep CA with ACME
   - Certificates for mylaniakea.com and holons.dev
   - Status: Available but not used yet

---

## Deployment Architecture

### Option 1: Standard Kubernetes Ingress (Current)
```
┌─────────────────────────────────────────────────────┐
│                    Internet                         │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
           ┌──────────────────┐
           │  Traefik Ingress │
           │   Controller     │
           └────┬────────┬────┘
                │        │
         HTTP   │        │  HTTPS
        (web)   │        │  (websecure)
                │        │
                ▼        ▼
     ┌──────────────────────────┐
     │   unity-ingress          │
     │   (Kubernetes Ingress)   │
     │                          │
     │   TLS: unity-tls-cert    │
     └────┬────────────────┬────┘
          │                │
          ▼                ▼
    ┌─────────┐      ┌──────────┐
    │ Backend │      │ Frontend │
    │ Service │      │ Service  │
    │  :8000  │      │   :80    │
    └─────────┘      └──────────┘
```

**Features:**
- Both HTTP and HTTPS work
- No automatic redirect
- Simple configuration
- Standard Kubernetes resource

### Option 2: Traefik IngressRoute (Advanced)
```
┌─────────────────────────────────────────────────────┐
│                    Internet                         │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
           ┌──────────────────┐
           │  Traefik Ingress │
           │   Controller     │
           └────┬────────┬────┘
                │        │
         HTTP   │        │  HTTPS
        (web)   │        │  (websecure)
                │        │
                ▼        ▼
     ┌──────────────┐  ┌──────────────────┐
     │ HTTP Routes  │  │  HTTPS Routes    │
     │ + Redirect   │  │  + TLS Cert      │
     │  Middleware  │  │                  │
     └──────┬───────┘  └────┬─────────────┘
            │ 308           │
            │ redirect      │ direct
            │               │
            └───────┬───────┘
                    ▼
           ┌─────────────────┐
           │  Backend/        │
           │  Frontend        │
           │  Services        │
           └─────────────────┘
```

**Features:**
- Automatic HTTP->HTTPS redirect (308 Permanent)
- Separate IngressRoute for HTTP and HTTPS
- Middleware for redirect logic
- More control over routing

---

## Ingress Annotations Explained

### Current Ingress Annotations
```yaml
annotations:
  kubernetes.io/ingress.class: traefik
  # Use both web (HTTP) and websecure (HTTPS) entrypoints
  traefik.ingress.kubernetes.io/router.entrypoints: web,websecure
  # Certificate issuer to use
  cert-manager.io/cluster-issuer: selfsigned-issuer
  # Redirect HTTP to HTTPS
  traefik.ingress.kubernetes.io/redirect-entry-point: https
  traefik.ingress.kubernetes.io/redirect-permanent: "true"
```

**Note:** The redirect annotations may not work with standard Ingress. For guaranteed HTTP->HTTPS redirect, use the IngressRoute approach (Option 2).

---

## Deployment Options Comparison

| Feature | Standard Ingress | Traefik IngressRoute |
|---------|------------------|----------------------|
| HTTPS Support | ✓ Yes | ✓ Yes |
| HTTP Support | ✓ Yes | ✓ Yes |
| HTTP→HTTPS Redirect | ⚠ Maybe | ✓ Yes (guaranteed) |
| Configuration Complexity | Simple | Moderate |
| Portability | High (standard K8s) | Low (Traefik-specific) |
| Advanced Features | Limited | Extensive |
| Middleware Support | No | Yes |
| Current Status | Updated, ready | Config exists, not applied |

---

## Step-by-Step Deployment

### Quick Deploy (Recommended)
```bash
# Option 1: Standard Ingress
/home/holon/Projects/unity/k8s/tls/deploy-tls.sh

# Option 2: Advanced with Redirect
/home/holon/Projects/unity/k8s/tls/deploy-tls-advanced.sh

# Verify
/home/holon/Projects/unity/k8s/tls/verify-tls.sh
```

### Manual Deploy
```bash
# 1. Apply cert-manager resources
kubectl apply -f /home/holon/Projects/unity/k8s/tls/selfsigned-issuer.yaml

# 2. Wait for certificate
kubectl wait --for=condition=ready certificate/unity-tls -n unity --timeout=60s

# 3a. Apply standard ingress
kubectl apply -f /home/holon/Projects/unity/k8s/deployments/ingress.yaml

# OR 3b. Apply IngressRoute (delete ingress first)
kubectl delete ingress unity-ingress -n unity
kubectl apply -f /home/holon/Projects/unity/k8s/tls/ingress-https-fixed.yaml

# 4. Verify
kubectl get certificate,ingress,ingressroute -n unity
```

---

## Testing Checklist

- [ ] Add hosts to /etc/hosts: `127.0.0.1 unity.homelab.local ui.homelab.local`
- [ ] Check certificate status: `kubectl get certificate -n unity`
- [ ] Test HTTPS backend: `curl -k https://unity.homelab.local/health`
- [ ] Test HTTPS frontend: `curl -k https://ui.homelab.local`
- [ ] Test HTTP redirect: `curl -I http://unity.homelab.local` (if using IngressRoute)
- [ ] Browser access: https://unity.homelab.local
- [ ] Browser access: https://ui.homelab.local
- [ ] Accept self-signed certificate warning in browser

---

## Switching to Production (Let's Encrypt)

### Prerequisites
1. Public domain (e.g., unity.mylaniakea.com)
2. Cloudflare account with API token
3. DNS records pointing to your cluster

### Steps
```bash
# 1. Create Cloudflare API token secret
kubectl create secret generic cloudflare-api-token \
  --namespace=unity \
  --from-literal=api-token=YOUR_CLOUDFLARE_API_TOKEN

# 2. Apply Let's Encrypt ClusterIssuer
kubectl apply -f /home/holon/Projects/unity/issuers.yaml

# 3. Update certificate in selfsigned-issuer.yaml
# Change issuerRef:
#   name: letsencrypt-cloudflare
#   kind: ClusterIssuer

# 4. Update certificate hosts to public domain
# dnsNames:
#   - unity.mylaniakea.com
#   - ui.mylaniakea.com

# 5. Update ingress annotation
# cert-manager.io/cluster-issuer: letsencrypt-cloudflare

# 6. Reapply
kubectl delete certificate unity-tls -n unity
kubectl apply -f /home/holon/Projects/unity/k8s/tls/selfsigned-issuer.yaml
kubectl apply -f /home/holon/Projects/unity/k8s/deployments/ingress.yaml

# 7. Wait for Let's Encrypt to issue certificate (can take 1-2 minutes)
kubectl wait --for=condition=ready certificate/unity-tls -n unity --timeout=5m
```

---

## Troubleshooting Guide

### Certificate Not Ready
**Symptom:** `kubectl get certificate` shows READY=False

**Diagnosis:**
```bash
kubectl describe certificate unity-tls -n unity
kubectl get certificaterequest -n unity
kubectl describe certificaterequest <name> -n unity
kubectl logs -n cert-manager deployment/cert-manager
```

**Common Issues:**
- ClusterIssuer not ready
- Invalid DNS names
- cert-manager not running
- RBAC permissions

### HTTPS Not Working
**Symptom:** Connection refused or timeout on HTTPS

**Diagnosis:**
```bash
# Check ingress
kubectl describe ingress unity-ingress -n unity

# Check services
kubectl get svc -n unity

# Check pods
kubectl get pods -n unity

# Check Traefik
kubectl logs -n kube-system -l app.kubernetes.io/name=traefik
```

**Common Issues:**
- Traefik not configured for websecure entrypoint
- Service ports incorrect
- Backend pods not running
- Firewall blocking port 443

### HTTP Redirect Not Working
**Symptom:** HTTP still works, no redirect to HTTPS

**Solution:**
Use Traefik IngressRoute approach (Option 2) which has explicit redirect middleware.

```bash
kubectl delete ingress unity-ingress -n unity
kubectl apply -f /home/holon/Projects/unity/k8s/tls/ingress-https-fixed.yaml
```

### Browser Certificate Warning
**Symptom:** "Your connection is not private" warning

**Explanation:**
This is expected for self-signed certificates. The certificate is valid but not trusted by browsers.

**Solutions:**
1. Click "Advanced" → "Accept Risk" (for testing)
2. Import CA certificate to system trust store
3. Use Let's Encrypt for production (no warnings)

---

## Certificate Lifecycle

### Automatic Renewal
cert-manager automatically renews certificates 30 days before expiry.

**Check renewal status:**
```bash
kubectl describe certificate unity-tls -n unity | grep -A 5 "Renewal Time"
```

### Manual Renewal
```bash
# Delete certificate (will be recreated)
kubectl delete certificate unity-tls -n unity

# Reapply
kubectl apply -f /home/holon/Projects/unity/k8s/tls/selfsigned-issuer.yaml

# Or force renewal by deleting secret
kubectl delete secret unity-tls-cert -n unity
# cert-manager will recreate it
```

### Certificate Rotation
When switching issuers (e.g., self-signed to Let's Encrypt):
1. Delete existing certificate and secret
2. Update Certificate resource with new issuerRef
3. Apply updated configuration
4. Wait for new certificate to be issued

---

## Security Considerations

### Self-Signed Certificates
**Pros:**
- Works immediately
- No external dependencies
- Free
- Good for development/testing

**Cons:**
- Browser warnings
- Not trusted by default
- Manual trust required
- Not suitable for production

### Let's Encrypt
**Pros:**
- Trusted by all browsers
- Free
- Automatic renewal
- Production-ready

**Cons:**
- Requires public domain
- Rate limits (50 certs/week)
- DNS or HTTP validation needed
- External dependency

### Best Practices
1. Use self-signed for local development
2. Use Let's Encrypt for staging/production
3. Monitor certificate expiry
4. Test renewal process
5. Keep cert-manager updated
6. Use separate certificates per environment
7. Rotate certificates regularly

---

## Resources and Links

### Documentation
- [cert-manager docs](https://cert-manager.io/docs/)
- [Traefik Ingress docs](https://doc.traefik.io/traefik/routing/providers/kubernetes-ingress/)
- [Traefik IngressRoute docs](https://doc.traefik.io/traefik/routing/providers/kubernetes-crd/)
- [Let's Encrypt docs](https://letsencrypt.org/docs/)

### Unity TLS Files
- ClusterIssuer & Certificate: `/home/holon/Projects/unity/k8s/tls/selfsigned-issuer.yaml`
- Standard Ingress: `/home/holon/Projects/unity/k8s/deployments/ingress.yaml`
- IngressRoute: `/home/holon/Projects/unity/k8s/tls/ingress-https-fixed.yaml`
- Production Issuers: `/home/holon/Projects/unity/issuers.yaml`
- Deploy Script: `/home/holon/Projects/unity/k8s/tls/deploy-tls.sh`
- Verify Script: `/home/holon/Projects/unity/k8s/tls/verify-tls.sh`
- Quick Start: `/home/holon/Projects/unity/k8s/tls/QUICKSTART.md`
- Full README: `/home/holon/Projects/unity/k8s/tls/README.md`

---

## Summary

Unity now has a complete TLS/HTTPS configuration:

1. **cert-manager** is installed and managing certificates
2. **Self-signed ClusterIssuer** is ready for immediate use
3. **Let's Encrypt ClusterIssuer** is configured for production
4. **Certificate** is issued and stored in Kubernetes secret
5. **Ingress** is updated with TLS configuration
6. **Deployment scripts** are ready to apply the configuration
7. **Verification scripts** are available to test the setup

**Next Action:** Run `/home/holon/Projects/unity/k8s/tls/deploy-tls.sh` to activate HTTPS!
