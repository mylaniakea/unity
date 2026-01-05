# Unity TLS/HTTPS Configuration Status

**Date:** 2026-01-04
**Status:** ✓ READY TO DEPLOY

---

## Infrastructure Status

### cert-manager
- **Status:** ✓ Running
- **Pods:** 3/3 running in cert-manager namespace
- **Age:** 18+ hours
- **Components:**
  - cert-manager controller
  - cert-manager webhook
  - cert-manager cainjector

### ClusterIssuers (Certificate Authorities)
| Name | Status | Age | Purpose |
|------|--------|-----|---------|
| selfsigned-issuer | ✓ Ready | 13h | Self-signed certs for development |
| letsencrypt-cloudflare | ✓ Ready | 17h | Let's Encrypt for production |
| smallstep-ca | ✗ Not Ready | 17h | Optional SmallStep CA (not required) |

### Certificates
| Name | Namespace | Status | Secret | Age |
|------|-----------|--------|--------|-----|
| unity-tls | unity | ✓ Ready | unity-tls-cert | 13h |

**Certificate Details:**
- **Issuer:** selfsigned-issuer
- **Hosts:** unity.homelab.local, ui.homelab.local, *.homelab.local
- **Duration:** 8760h (1 year)
- **Renewal:** 720h (30 days before expiry)
- **Auto-renewal:** Enabled

### TLS Secrets
| Name | Type | Namespace | Age |
|------|------|-----------|-----|
| unity-tls-cert | kubernetes.io/tls | unity | 13h |

### Ingress
| Name | Hosts | Ports | Status |
|------|-------|-------|--------|
| unity-ingress | unity.homelab.local, ui.homelab.local | 80 | ✓ Exists (HTTP only) |

**Note:** Ingress configuration has been updated to include TLS but not yet applied.

### Services
| Name | Type | Cluster-IP | Ports | Status |
|------|------|------------|-------|--------|
| backend-service | ClusterIP | 10.43.228.245 | 8000/TCP | ✓ Running |
| frontend-service | ClusterIP | 10.43.247.167 | 80/TCP | ✓ Running |

---

## Configuration Files Status

### TLS Directory: `/home/holon/Projects/unity/k8s/tls/`

| File | Size | Type | Status |
|------|------|------|--------|
| selfsigned-issuer.yaml | 452B | Config | ✓ Applied |
| ingress-https-fixed.yaml | 1.5K | Config | Ready (alternative) |
| ingress-https.yaml | 1.5K | Config | Ready (alternative) |
| deploy-tls.sh | 3.2K | Script | ✓ Ready |
| deploy-tls-advanced.sh | 3.7K | Script | ✓ Ready |
| verify-tls.sh | 3.5K | Script | ✓ Ready |
| README.md | 4.3K | Docs | ✓ Complete |
| QUICKSTART.md | 5.7K | Docs | ✓ Complete |
| CONFIGURATION_SUMMARY.md | 14K | Docs | ✓ Complete |
| STATUS.md | This file | Docs | ✓ Complete |

### Main Ingress File
**Path:** `/home/holon/Projects/unity/k8s/deployments/ingress.yaml`
**Status:** ✓ Updated with TLS configuration
**Changes:**
- Added TLS section with hosts and secret
- Added websecure entrypoint
- Added cert-manager annotation
- Added redirect annotations

### Production Issuers
**Path:** `/home/holon/Projects/unity/issuers.yaml`
**Status:** ✓ Available for production use
**Contains:**
- Let's Encrypt ClusterIssuer with Cloudflare DNS-01
- SmallStep CA ClusterIssuer
- Certificates for mylaniakea.com and holons.dev

---

## What's Been Done

### ✓ Completed Tasks

1. **cert-manager Installation**
   - Installed and verified running
   - All 3 pods healthy

2. **ClusterIssuer Configuration**
   - Self-signed issuer created and ready
   - Let's Encrypt issuer configured
   - SmallStep CA configured (optional)

3. **Certificate Creation**
   - unity-tls certificate issued
   - Secret created and populated
   - Valid for unity.homelab.local and ui.homelab.local

4. **Ingress Update**
   - Main ingress file updated with TLS config
   - Added websecure entrypoint
   - Added cert-manager annotations
   - Added redirect annotations

5. **Alternative Configurations**
   - Created Traefik IngressRoute with HTTP redirect
   - Configured middleware for redirect

6. **Deployment Automation**
   - Created deploy-tls.sh for standard deployment
   - Created deploy-tls-advanced.sh for IngressRoute deployment
   - Created verify-tls.sh for validation

7. **Documentation**
   - README.md with comprehensive guide
   - QUICKSTART.md for quick reference
   - CONFIGURATION_SUMMARY.md with technical details
   - STATUS.md (this file) for current state
   - DEPLOY_TLS.md in project root

---

## What Needs To Be Done

### Pending Actions

1. **Apply TLS Configuration** (Required)
   ```bash
   /home/holon/Projects/unity/k8s/tls/deploy-tls.sh
   ```
   This will:
   - Verify cert-manager is running
   - Ensure certificate is ready
   - Apply TLS-enabled ingress
   - Verify configuration

2. **Add Hosts to /etc/hosts** (If not already done)
   ```bash
   echo "127.0.0.1 unity.homelab.local ui.homelab.local" | sudo tee -a /etc/hosts
   ```

3. **Verify Deployment** (Recommended)
   ```bash
   /home/holon/Projects/unity/k8s/tls/verify-tls.sh
   ```

4. **Test HTTPS Access** (Required)
   ```bash
   curl -k https://unity.homelab.local/health
   curl -k https://ui.homelab.local
   ```

5. **Browser Testing** (Recommended)
   - Open https://unity.homelab.local
   - Accept self-signed certificate warning
   - Verify backend API works
   - Open https://ui.homelab.local
   - Verify frontend UI loads

### Optional Actions

1. **Enable HTTP to HTTPS Redirect**
   ```bash
   /home/holon/Projects/unity/k8s/tls/deploy-tls-advanced.sh
   ```
   This uses Traefik IngressRoute with automatic redirect.

2. **Configure Production (Let's Encrypt)**
   - Create Cloudflare API token secret
   - Update certificate issuerRef to letsencrypt-cloudflare
   - Update DNS names to public domains
   - Reapply configuration

---

## Known Issues

### 1. Self-Signed Certificate Warning
**Symptom:** Browser shows "Your connection is not private"
**Status:** ✓ Expected behavior
**Impact:** None (for development)
**Solution:** Accept risk or use Let's Encrypt for production

### 2. HTTP Redirect with Standard Ingress
**Symptom:** HTTP doesn't redirect to HTTPS
**Status:** ⚠ May not work with Traefik annotations
**Impact:** HTTP still accessible
**Solution:** Use IngressRoute approach (deploy-tls-advanced.sh)

### 3. SmallStep CA ClusterIssuer Not Ready
**Symptom:** smallstep-ca shows READY=False
**Status:** ⚠ Not critical
**Impact:** None (not currently used)
**Solution:** Optional, can configure SmallStep if needed

---

## Testing Checklist

### Pre-Deployment
- [x] cert-manager is running
- [x] ClusterIssuer is ready
- [x] Certificate is issued
- [x] TLS secret exists
- [x] Services are running
- [x] Ingress file is updated

### Post-Deployment (TODO)
- [ ] Apply TLS configuration
- [ ] Verify ingress has TLS section
- [ ] Test HTTPS backend endpoint
- [ ] Test HTTPS frontend endpoint
- [ ] Test HTTP redirect (if using IngressRoute)
- [ ] Verify certificate in browser
- [ ] Accept self-signed certificate
- [ ] Confirm Unity works over HTTPS

---

## Deployment Commands

### Quick Deploy
```bash
# Standard deployment (recommended)
/home/holon/Projects/unity/k8s/tls/deploy-tls.sh

# Verify
/home/holon/Projects/unity/k8s/tls/verify-tls.sh

# Test
curl -k https://unity.homelab.local/health
curl -k https://ui.homelab.local
```

### Advanced Deploy (with HTTP redirect)
```bash
# Advanced deployment with redirect
/home/holon/Projects/unity/k8s/tls/deploy-tls-advanced.sh

# Verify
/home/holon/Projects/unity/k8s/tls/verify-tls.sh

# Test redirect
curl -I http://unity.homelab.local
# Should return: HTTP/1.1 308 Permanent Redirect
```

### Manual Deploy
```bash
# 1. Apply ClusterIssuer and Certificate
kubectl apply -f /home/holon/Projects/unity/k8s/tls/selfsigned-issuer.yaml

# 2. Wait for certificate
kubectl wait --for=condition=ready certificate/unity-tls -n unity --timeout=60s

# 3. Apply ingress
kubectl apply -f /home/holon/Projects/unity/k8s/deployments/ingress.yaml

# 4. Verify
kubectl get certificate,ingress -n unity
```

---

## Production Readiness

### Current Environment: Development
- **Certificate Type:** Self-signed
- **Trust:** Not trusted by browsers
- **Validity:** 1 year
- **Automatic Renewal:** Yes
- **Suitable For:** Local development, testing

### For Production: Let's Encrypt
To make Unity production-ready with trusted certificates:

1. **Prerequisites:**
   - Public domain name
   - Cloudflare account
   - Cloudflare API token
   - DNS pointing to cluster

2. **Configuration:**
   ```bash
   # Create Cloudflare secret
   kubectl create secret generic cloudflare-api-token \
     --namespace=unity \
     --from-literal=api-token=YOUR_TOKEN

   # Update certificate issuer
   # Edit: /home/holon/Projects/unity/k8s/tls/selfsigned-issuer.yaml
   # Change issuerRef.name to: letsencrypt-cloudflare
   # Update dnsNames to public domains

   # Update ingress annotation
   # Edit: /home/holon/Projects/unity/k8s/deployments/ingress.yaml
   # Change: cert-manager.io/cluster-issuer: letsencrypt-cloudflare

   # Reapply
   kubectl delete certificate unity-tls -n unity
   kubectl apply -f /home/holon/Projects/unity/k8s/tls/selfsigned-issuer.yaml
   kubectl apply -f /home/holon/Projects/unity/k8s/deployments/ingress.yaml
   ```

3. **Verification:**
   ```bash
   # Wait for Let's Encrypt to issue (1-2 minutes)
   kubectl wait --for=condition=ready certificate/unity-tls \
     -n unity --timeout=5m

   # Verify
   kubectl describe certificate unity-tls -n unity
   ```

---

## Resources

### Documentation
- [README.md](./README.md) - Comprehensive documentation
- [QUICKSTART.md](./QUICKSTART.md) - Quick start guide
- [CONFIGURATION_SUMMARY.md](./CONFIGURATION_SUMMARY.md) - Technical details
- [/home/holon/Projects/unity/DEPLOY_TLS.md](../../DEPLOY_TLS.md) - Main deployment guide

### Scripts
- [deploy-tls.sh](./deploy-tls.sh) - Standard deployment
- [deploy-tls-advanced.sh](./deploy-tls-advanced.sh) - Advanced deployment
- [verify-tls.sh](./verify-tls.sh) - Verification script

### Configuration Files
- [selfsigned-issuer.yaml](./selfsigned-issuer.yaml) - ClusterIssuer and Certificate
- [ingress-https-fixed.yaml](./ingress-https-fixed.yaml) - Traefik IngressRoute
- [/home/holon/Projects/unity/k8s/deployments/ingress.yaml](../deployments/ingress.yaml) - Main ingress
- [/home/holon/Projects/unity/issuers.yaml](../../issuers.yaml) - Production issuers

### External Links
- [cert-manager Documentation](https://cert-manager.io/docs/)
- [Traefik Kubernetes Ingress](https://doc.traefik.io/traefik/routing/providers/kubernetes-ingress/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)

---

## Summary

**Current State:** ✓ Ready to Deploy

Unity has a complete TLS/HTTPS configuration:
- cert-manager is installed and running
- Certificate is issued and ready
- Ingress is updated with TLS configuration
- Deployment scripts are ready
- Documentation is complete

**Next Action:** Run `/home/holon/Projects/unity/k8s/tls/deploy-tls.sh` to activate HTTPS

**Expected Result:** Unity will be accessible over HTTPS at:
- https://unity.homelab.local (Backend API)
- https://ui.homelab.local (Frontend UI)

**Note:** Self-signed certificate warnings are expected. Accept the risk in your browser or switch to Let's Encrypt for production.

---

Last Updated: 2026-01-04 06:45 UTC
