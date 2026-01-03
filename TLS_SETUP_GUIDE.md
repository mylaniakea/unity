# Unity Platform TLS/SSL Setup Guide

**Status**: cert-manager installed ✅  
**Next**: Configure SmallStep & Cloudflare credentials

---

## Overview

Your Unity platform will use:
- **SmallStep CA** (internal) for `*.homelab.local` certificates
- **Let's Encrypt + Cloudflare DNS** (public) for `*.mylaniakea.com` and `*.holons.dev`
- **cert-manager** to automate certificate issuance and renewal

All setup is automated once you provide credentials.

---

## What's Already Done

### ✅ Phase 1: Install cert-manager
- cert-manager v1.13.2 installed
- All CRDs created
- Webhook and controllers running
- Ready for issuer configuration

### ✅ Prepared Templates
- `issuers.yaml` - ClusterIssuer configurations (SmallStep + Cloudflare/Let's Encrypt)
- `ingress-tls.yaml` - Updated ingress with TLS
- `tls-setup.sh` - Automation script for credential setup

---

## What You Need to Provide

### 1. Cloudflare Information

**Get your Cloudflare email:**
```
Go to: https://dash.cloudflare.com → Account Settings
Copy: Email address associated with your Cloudflare account
```

**Create Cloudflare API Token:**
```
1. Go to: https://dash.cloudflare.com → Account → API Tokens
2. Click: "Create Token"
3. Use template: "Edit zone DNS"
4. Permissions:
   - Zone → DNS → Edit
5. Zone Resources:
   - Include → Specific zones → mylaniakea.com, holons.dev
6. TTL: 30 minutes (default)
7. Create and copy the token
```

**Provide:**
- Cloudflare email: `____________________`
- Cloudflare API token: `____________________`

### 2. SmallStep ACME Provisioner Name

**Confirm your provisioner name:**
```
1. Go to: https://pki.mylaniakea.ca.smallstep.com
2. Click: Settings → Provisioners
3. Look for provisioner named "acme" or similar
4. Copy the exact name
```

**Typical names:**
- `acme` (default)
- `my-acme`
- `k8s-acme`
- Check your instance for exact name

**Provide:**
- SmallStep ACME provisioner name: `____________________`

---

## How to Execute

### Step 1: Update Configuration Files

Edit `/home/holon/Projects/unity/issuers.yaml`:

**Find this section:**
```yaml
solvers:
- dns01:
    cloudflare:
      email: # Set to your Cloudflare account email
      apiTokenSecretRef:
```

**Replace with your email:**
```yaml
solvers:
- dns01:
    cloudflare:
      email: your-email@example.com
      apiTokenSecretRef:
```

**Also update the email in Let's Encrypt issuer section:**
```yaml
email: your-email@mylaniakea.com
```

### Step 2: Run Setup Script

```bash
# Set environment variables
export CLOUDFLARE_API_TOKEN="your-api-token-here"
export SMALLSTEP_ACME_PROVISIONER="acme"  # Or your provisioner name

# Run the setup script
/home/holon/Projects/unity/tls-setup.sh
```

This will:
1. Verify cert-manager is running
2. Download SmallStep root certificate
3. Create Kubernetes secrets for both providers
4. Verify everything is ready

### Step 3: Apply Issuers

```bash
kubectl apply -f /home/holon/Projects/unity/issuers.yaml
```

**Verify:**
```bash
kubectl get clusterissuer
kubectl get certificate -n homelab
```

Watch certificate issuance:
```bash
kubectl describe certificate homelab-local-cert -n homelab
kubectl describe certificate mylaniakea-com-cert -n homelab
```

### Step 4: Update Ingress

```bash
# Delete old ingress
kubectl delete ingress unity-ingress -n homelab

# Apply new TLS-enabled ingress
kubectl apply -f /home/holon/Projects/unity/ingress-tls.yaml
```

**Verify:**
```bash
kubectl get ingress -n homelab
kubectl describe ingress unity-ingress-internal -n homelab
```

### Step 5: Verify TLS Certificates

**Check certificate status:**
```bash
kubectl get certificate -n homelab -o wide
kubectl get secret -n homelab | grep tls
```

**View certificate details:**
```bash
kubectl get secret homelab-local-tls -n homelab -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -text -noout
```

**Test HTTPS access (internal):**
```bash
# Once DNS is set up to point to your cluster
curl -v https://unity.homelab.local/health
curl -v https://ui.homelab.local
```

**Test HTTPS access (public):**
```bash
curl -v https://unity.mylaniakea.com/health
curl -v https://ui.mylaniakea.com
```

---

## Architecture After Setup

```
┌─────────────────────────────────────────────────┐
│           External Clients                      │
│        (Internet, Remote Access)                │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
        Cloudflare DNS (mylaniakea.com, holons.dev)
                     │
                     ▼
    ┌───────────────────────────────────────┐
    │   k3s Traefik Ingress                 │
    │   HTTPS (Let's Encrypt certs)         │
    └───────────────────────────────────────┘
      │unity.mylaniakea.com      │holons.dev
      │ui.mylaniakea.com         │ui.holons.dev
      ▼                           ▼
    ┌──────────────────────────────────────┐
    │    Backend (8000)                    │
    │    Frontend (3000)                   │
    │  (Internal SmallStep mTLS ready)     │
    └──────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│        Internal Clients (HomeNet)               │
│        (Within your LAN/VPN)                    │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
    ┌───────────────────────────────────────┐
    │   k3s Traefik Ingress                 │
    │   HTTPS (SmallStep CA certs)          │
    └───────────────────────────────────────┘
      │unity.homelab.local   │ui.homelab.local
      ▼                       ▼
    ┌──────────────────────────────────────┐
    │    Backend (8000)                    │
    │    Frontend (3000)                   │
    │  (SmallStep trusted internally)      │
    └──────────────────────────────────────┘
```

---

## Auto-Renewal

cert-manager automatically renews certificates:

- **SmallStep certs**: 24h validity, renewed when ~50% expired
- **Let's Encrypt certs**: 90 days validity, renewed at 30 days

Check renewal status:
```bash
kubectl get certificate -n homelab -o wide
```

Monitor logs:
```bash
kubectl logs -f -l app.kubernetes.io/name=cert-manager -n cert-manager
```

---

## Troubleshooting

### Certificate Not Issuing

```bash
# Check certificate status
kubectl describe certificate homelab-local-cert -n homelab

# Check issuer status
kubectl describe clusterissuer smallstep-ca
kubectl describe clusterissuer letsencrypt-cloudflare

# Check cert-manager logs
kubectl logs -f -n cert-manager -l app.kubernetes.io/name=cert-manager
```

### SmallStep Connection Issues

```bash
# Verify SmallStep endpoint is reachable
curl -v https://pki.mylaniakea.ca.smallstep.com/health

# Check SmallStep root certificate
kubectl get secret smallstep-root -n homelab -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -text -noout
```

### Cloudflare Issues

```bash
# Verify Cloudflare API token
curl -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  https://api.cloudflare.com/client/v4/user/tokens/verify

# Check cert-manager logs for DNS-01 challenges
kubectl logs -f -n cert-manager -l app.kubernetes.io/name=cert-manager | grep -i cloudflare
```

---

## Next Steps (Future)

### Enable mTLS Between Services
Once internal certificates are working:
```bash
# Update backend/database connections to use TLS
# Configure PostgreSQL and Redis for encrypted connections
```

### Certificate Monitoring Dashboard
Add monitoring for certificate expiration:
```bash
# Prometheus metrics available from cert-manager
# Build dashboard in your existing monitoring
```

### Additional Public Domains
To add more domains:
1. Update `issuers.yaml` with new domain names
2. Create new Certificate resources
3. Update ingress with new hosts

---

## Security Notes

1. **Cloudflare API Token**
   - Store securely (already in Kubernetes Secret)
   - Rotate every 90 days
   - Limit to DNS:edit permission only

2. **SmallStep Root Certificate**
   - Automatically injected into containers
   - Trusted by cert-manager and applications
   - No manual CA injection needed

3. **Private Keys**
   - Stored in Kubernetes Secrets
   - Encrypted at rest (if etcd encryption enabled)
   - RBAC controls access

4. **HTTP → HTTPS Redirect**
   - All HTTP traffic redirects to HTTPS
   - HSTS ready for additional security

---

## Rollback

If you need to revert to HTTP-only:

```bash
# Delete TLS ingress
kubectl delete ingress unity-ingress-internal -n homelab
kubectl delete ingress unity-ingress-public-mylaniakea -n homelab
kubectl delete ingress unity-ingress-public-holons -n homelab

# Recreate HTTP-only ingress
kubectl apply -f /home/holon/Projects/unity/original-ingress.yaml

# Keep cert-manager installed for future use
```

---

## Summary

Once you provide:
1. Cloudflare email
2. Cloudflare API token
3. SmallStep ACME provisioner name

I will:
1. Update configuration files
2. Run automated setup
3. Create certificates
4. Update ingress with TLS
5. Verify everything works

**Your platform will then have:**
- ✅ Automatic HTTPS for internal network
- ✅ Automatic HTTPS for public internet
- ✅ Auto-renewing certificates
- ✅ Professional SSL/TLS setup

