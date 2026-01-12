# Unity TLS/HTTPS Deployment Guide

## Executive Summary

**Status:** ✓ TLS/HTTPS is fully configured and ready to deploy

Unity now has complete TLS/HTTPS support using cert-manager with self-signed certificates for local development and Let's Encrypt for production.

---

## Quick Deploy (3 Commands)

```bash
# 1. Deploy TLS configuration
/home/holon/Projects/unity/k8s/tls/deploy-tls.sh

# 2. Verify deployment
/home/holon/Projects/unity/k8s/tls/verify-tls.sh

# 3. Access Unity over HTTPS
# https://unity.homelab.local
# https://ui.homelab.local
```

---

## What Was Configured

### 1. Certificate Management (cert-manager)
- **Status:** Already installed and running
- **Version:** Latest (running 3 pods in cert-manager namespace)
- **Components:**
  - cert-manager controller
  - cert-manager webhook
  - cert-manager cainjector

### 2. ClusterIssuers (Certificate Authorities)
Three issuers are configured:

| Issuer | Status | Purpose | Use Case |
|--------|--------|---------|----------|
| `selfsigned-issuer` | ✓ Ready | Self-signed certs | Local development |
| `letsencrypt-cloudflare` | ✓ Ready | Let's Encrypt via Cloudflare | Production |
| `smallstep-ca` | ✗ Not Ready | SmallStep CA | Optional internal CA |

### 3. Certificate
- **Name:** unity-tls
- **Namespace:** unity
- **Status:** ✓ Issued and Ready
- **Secret:** unity-tls-cert
- **Valid Hosts:**
  - unity.homelab.local (Backend API)
  - ui.homelab.local (Frontend UI)
  - *.homelab.local (Wildcard)
- **Validity:** 1 year (8760h)
- **Auto-renewal:** 30 days before expiry

### 4. Ingress Configuration
Main ingress at `/home/holon/Projects/unity/k8s/deployments/ingress.yaml` updated with:
- TLS configuration enabled
- Both HTTP (web) and HTTPS (websecure) entrypoints
- Certificate annotation for automatic cert management
- HTTP to HTTPS redirect annotations

---

## Architecture

```
                        Internet/Browser
                              │
                              │ HTTP/HTTPS
                              ▼
                    ┌──────────────────┐
                    │  Traefik Ingress │
                    │    Controller    │
                    │                  │
                    │  Entrypoints:    │
                    │  - web (80)      │
                    │  - websecure(443)│
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
    ┌─────────────────┐          ┌─────────────────┐
    │  HTTP Route     │          │  HTTPS Route    │
    │  Port 80        │          │  Port 443       │
    │                 │          │                 │
    │  (Optional      │          │  TLS Secret:    │
    │   redirect)     │          │  unity-tls-cert │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             └──────────┬─────────────────┘
                        │
         ┌──────────────┴───────────────┐
         │                              │
         ▼                              ▼
┌──────────────────┐         ┌──────────────────┐
│ Backend Service  │         │ Frontend Service │
│ unity.homelab    │         │ ui.homelab       │
│ Port 8000        │         │ Port 80          │
└──────────────────┘         └──────────────────┘
         │                              │
         ▼                              ▼
┌──────────────────┐         ┌──────────────────┐
│ Backend Pods     │         │ Frontend Pods    │
│ (FastAPI)        │         │ (React)          │
└──────────────────┘         └──────────────────┘

Certificate Management (cert-manager):
┌─────────────────────────────────────────┐
│  cert-manager (namespace: cert-manager) │
│                                         │
│  ┌────────────────┐                    │
│  │ ClusterIssuer  │                    │
│  │ selfsigned-    │                    │
│  │ issuer         │                    │
│  └───────┬────────┘                    │
│          │ creates                     │
│          ▼                             │
│  ┌────────────────┐                    │
│  │  Certificate   │                    │
│  │  unity-tls     │                    │
│  └───────┬────────┘                    │
│          │ generates                   │
│          ▼                             │
│  ┌────────────────┐                    │
│  │ Secret         │                    │
│  │ unity-tls-cert │                    │
│  │ (TLS key+cert) │                    │
│  └────────────────┘                    │
└─────────────────────────────────────────┘
```

---

## Deployment Options

### Option 1: Standard Kubernetes Ingress (Recommended)
**Best for:** Simple setup, standard Kubernetes environments

**Features:**
- ✓ HTTPS enabled on port 443
- ✓ HTTP still works on port 80
- ✓ Standard Kubernetes Ingress resource
- ✓ Portable across different ingress controllers
- ⚠ HTTP redirect may not work (Traefik annotation dependent)

**Deploy:**
```bash
/home/holon/Projects/unity/k8s/tls/deploy-tls.sh
```

### Option 2: Traefik IngressRoute (Advanced)
**Best for:** Advanced routing, guaranteed HTTP→HTTPS redirect

**Features:**
- ✓ HTTPS enabled on port 443
- ✓ Automatic HTTP→HTTPS redirect (308 Permanent)
- ✓ Traefik Middleware for advanced routing
- ✓ Separate routes for HTTP and HTTPS
- ⚠ Traefik-specific (not portable)

**Deploy:**
```bash
/home/holon/Projects/unity/k8s/tls/deploy-tls-advanced.sh
```

---

## File Structure

```
/home/holon/Projects/unity/
├── k8s/
│   ├── deployments/
│   │   └── ingress.yaml                    # ✓ Updated with TLS config
│   └── tls/                                # ← New TLS directory
│       ├── CONFIGURATION_SUMMARY.md        # Detailed technical summary
│       ├── QUICKSTART.md                   # Quick start guide
│       ├── README.md                       # Full documentation
│       ├── deploy-tls.sh                   # ✓ Standard deployment script
│       ├── deploy-tls-advanced.sh          # ✓ Advanced deployment script
│       ├── verify-tls.sh                   # ✓ Verification script
│       ├── selfsigned-issuer.yaml          # ✓ ClusterIssuer + Certificate
│       ├── ingress-https-fixed.yaml        # IngressRoute config
│       └── ingress-https.yaml              # Alternative IngressRoute
└── issuers.yaml                            # Production ClusterIssuers (Let's Encrypt, SmallStep)
```

**Scripts are executable:** All `.sh` files have execute permissions

---

## Current Status

```bash
# ClusterIssuers
✓ selfsigned-issuer         READY (13h)
✓ letsencrypt-cloudflare    READY (17h)
✗ smallstep-ca              NOT READY (optional)

# Certificate
✓ unity-tls                 READY (13h)
  Secret: unity-tls-cert    Created (13h)

# Ingress
✓ unity-ingress             EXISTS (HTTP only)
  Updated config ready to apply with TLS

# Services
✓ backend-service           ClusterIP 8000/TCP
✓ frontend-service          ClusterIP 80/TCP
```

---

## Deployment Steps

### Prerequisites Check
```bash
# 1. Verify cert-manager is running
kubectl get pods -n cert-manager

# 2. Verify certificate exists
kubectl get certificate -n unity

# 3. Verify services are running
kubectl get svc -n unity
```

### Deploy TLS
```bash
# Run deployment script
/home/holon/Projects/unity/k8s/tls/deploy-tls.sh

# This script will:
# 1. Check cert-manager installation
# 2. Apply ClusterIssuer and Certificate
# 3. Wait for certificate to be ready
# 4. Apply TLS-enabled ingress
# 5. Verify configuration
```

### Verify Deployment
```bash
# Run verification script
/home/holon/Projects/unity/k8s/tls/verify-tls.sh

# This script checks:
# - cert-manager status
# - ClusterIssuers status
# - Certificate status
# - TLS secret existence
# - Ingress configuration
# - HTTPS connectivity
# - Certificate details
```

### Access Unity
```bash
# Add hosts to /etc/hosts (if not already done)
echo "127.0.0.1 unity.homelab.local ui.homelab.local" | sudo tee -a /etc/hosts

# Test backend
curl -k https://unity.homelab.local/health

# Test frontend
curl -k https://ui.homelab.local

# Open in browser
# https://unity.homelab.local
# https://ui.homelab.local
```

**Note:** `-k` flag skips certificate verification for self-signed certs

---

## Testing

### 1. Certificate Verification
```bash
# Check certificate status
kubectl get certificate -n unity

# Should show:
# NAME        READY   SECRET           AGE
# unity-tls   True    unity-tls-cert   13h

# View certificate details
kubectl describe certificate unity-tls -n unity
```

### 2. HTTPS Endpoints
```bash
# Backend health check
curl -k https://unity.homelab.local/health
# Expected: {"status": "healthy", ...}

# Frontend
curl -k https://ui.homelab.local
# Expected: HTML content
```

### 3. Certificate Details
```bash
# View certificate using openssl
openssl s_client -connect unity.homelab.local:443 \
  -servername unity.homelab.local </dev/null 2>/dev/null | \
  openssl x509 -noout -text | grep -A 2 "Subject:\|Issuer:\|DNS:"

# Should show:
# Subject: CN = unity.homelab.local
# DNS:unity.homelab.local, DNS:ui.homelab.local, DNS:*.homelab.local
```

### 4. Browser Testing
1. Open browser
2. Navigate to https://unity.homelab.local
3. You'll see a certificate warning (expected for self-signed)
4. Click "Advanced" → "Accept Risk and Continue"
5. Unity backend API should load
6. Repeat for https://ui.homelab.local for frontend

---

## Troubleshooting

### Certificate Not Ready
```bash
# Check certificate status
kubectl describe certificate unity-tls -n unity

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager --tail=50

# Common issues:
# - ClusterIssuer not ready
# - Invalid DNS names
# - RBAC permissions
```

### HTTPS Connection Refused
```bash
# Check Traefik logs
kubectl logs -n kube-system -l app.kubernetes.io/name=traefik --tail=50

# Check if websecure entrypoint is enabled
kubectl get service -n kube-system traefik

# Should show both ports 80 and 443
```

### Browser Shows "NET::ERR_CERT_AUTHORITY_INVALID"
**This is expected for self-signed certificates!**

**Solutions:**
1. **For testing:** Click "Advanced" and accept the risk
2. **For production:** Use Let's Encrypt (see production section below)
3. **For local trust:** Import the CA certificate to your system trust store

---

## Production Deployment (Let's Encrypt)

To switch to Let's Encrypt for production with valid certificates:

### Prerequisites
- Public domain (e.g., unity.mylaniakea.com)
- Cloudflare account with API token
- DNS records pointing to your cluster

### Steps
```bash
# 1. Create Cloudflare API token secret
kubectl create secret generic cloudflare-api-token \
  --namespace=unity \
  --from-literal=api-token=YOUR_CLOUDFLARE_API_TOKEN

# 2. Edit certificate configuration
# Update /home/holon/Projects/unity/k8s/tls/selfsigned-issuer.yaml
# Change:
#   issuerRef:
#     name: letsencrypt-cloudflare  # was: selfsigned-issuer
#     kind: ClusterIssuer
# And update dnsNames to public domains:
#   dnsNames:
#     - unity.mylaniakea.com
#     - ui.mylaniakea.com

# 3. Update ingress annotation
# In /home/holon/Projects/unity/k8s/deployments/ingress.yaml
# Change:
#   cert-manager.io/cluster-issuer: letsencrypt-cloudflare

# 4. Delete old certificate and secret
kubectl delete certificate unity-tls -n unity
kubectl delete secret unity-tls-cert -n unity

# 5. Apply updated configuration
kubectl apply -f /home/holon/Projects/unity/k8s/tls/selfsigned-issuer.yaml
kubectl apply -f /home/holon/Projects/unity/k8s/deployments/ingress.yaml

# 6. Wait for Let's Encrypt to issue certificate
kubectl wait --for=condition=ready certificate/unity-tls \
  -n unity --timeout=5m

# 7. Verify
kubectl get certificate -n unity
# Should show READY=True
```

---

## Security Notes

### Self-Signed Certificates (Current Setup)
**Use for:** Local development, testing, internal services

**Pros:**
- ✓ Works immediately
- ✓ No external dependencies
- ✓ Free
- ✓ No rate limits

**Cons:**
- ✗ Browser warnings
- ✗ Not trusted by default
- ✗ Manual trust required
- ✗ Not suitable for public services

### Let's Encrypt (Production)
**Use for:** Production, public-facing services

**Pros:**
- ✓ Trusted by all browsers
- ✓ Free
- ✓ Automatic renewal
- ✓ Industry standard

**Cons:**
- ⚠ Rate limits (50 certs/week per domain)
- ⚠ Requires public domain
- ⚠ Requires DNS or HTTP validation
- ⚠ External dependency

---

## Certificate Lifecycle

### Automatic Renewal
cert-manager automatically renews certificates **30 days before expiry**.

**Current configuration:**
- **Duration:** 8760h (1 year)
- **Renewal window:** 720h (30 days before expiry)
- **Auto-renewal:** ✓ Enabled

**Monitor renewal:**
```bash
# Check certificate renewal time
kubectl describe certificate unity-tls -n unity | grep "Renewal Time"

# Check cert-manager logs for renewal attempts
kubectl logs -n cert-manager deployment/cert-manager | grep renewal
```

### Manual Renewal
```bash
# Force renewal by deleting the secret
kubectl delete secret unity-tls-cert -n unity
# cert-manager will automatically recreate it

# Or delete and recreate the certificate
kubectl delete certificate unity-tls -n unity
kubectl apply -f /home/holon/Projects/unity/k8s/tls/selfsigned-issuer.yaml
```

---

## Documentation

Comprehensive documentation is available:

1. **QUICKSTART.md** - Quick start guide (this file)
   - `/home/holon/Projects/unity/k8s/tls/QUICKSTART.md`

2. **CONFIGURATION_SUMMARY.md** - Technical deep dive
   - `/home/holon/Projects/unity/k8s/tls/CONFIGURATION_SUMMARY.md`

3. **README.md** - Complete reference
   - `/home/holon/Projects/unity/k8s/tls/README.md`

4. **Deployment Scripts** - Automated deployment
   - `/home/holon/Projects/unity/k8s/tls/deploy-tls.sh`
   - `/home/holon/Projects/unity/k8s/tls/deploy-tls-advanced.sh`

5. **Verification Script** - Testing and validation
   - `/home/holon/Projects/unity/k8s/tls/verify-tls.sh`

---

## Next Steps

1. **Deploy TLS:**
   ```bash
   /home/holon/Projects/unity/k8s/tls/deploy-tls.sh
   ```

2. **Verify:**
   ```bash
   /home/holon/Projects/unity/k8s/tls/verify-tls.sh
   ```

3. **Test in browser:**
   - https://unity.homelab.local
   - https://ui.homelab.local

4. **For production:**
   - Configure Cloudflare API token
   - Update to Let's Encrypt
   - Update DNS names to public domains
   - Redeploy

---

## Support

### Useful Commands
```bash
# Check everything
kubectl get clusterissuers,certificates,secrets,ingress -n unity

# Watch certificate issuance
kubectl get certificate -n unity -w

# View cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager -f

# View Traefik logs
kubectl logs -n kube-system -l app.kubernetes.io/name=traefik -f

# Test certificate
curl -kvI https://unity.homelab.local 2>&1 | grep -E "subject:|issuer:|expire"
```

### Common Issues
- **Certificate stuck in "Issuing":** Check cert-manager logs
- **HTTPS not working:** Verify Traefik has port 443 exposed
- **Browser warning:** Expected for self-signed, use Let's Encrypt for production
- **Connection refused:** Check if backend/frontend pods are running

---

## Summary

Unity TLS/HTTPS configuration is complete and ready to deploy:

✓ cert-manager installed and running
✓ Self-signed ClusterIssuer ready
✓ Let's Encrypt ClusterIssuer configured
✓ Certificate issued and valid
✓ TLS secret created
✓ Ingress updated with TLS configuration
✓ Deployment scripts created
✓ Verification scripts ready
✓ Documentation complete

**Deploy now with:** `/home/holon/Projects/unity/k8s/tls/deploy-tls.sh`
