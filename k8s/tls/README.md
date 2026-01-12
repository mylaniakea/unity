# Unity TLS/HTTPS Configuration with cert-manager

This directory contains the TLS/HTTPS configuration for Unity using cert-manager.

## Current Status

- **cert-manager**: Installed and running
- **ClusterIssuers**:
  - `selfsigned-issuer`: Ready (for local development)
  - `letsencrypt-cloudflare`: Ready (for production)
  - `smallstep-ca`: Not ready (optional)
- **Certificate**: `unity-tls` is issued and ready in unity namespace
- **Secret**: `unity-tls-cert` contains the TLS certificate

## Architecture

Unity supports two approaches for TLS/HTTPS:

### Option 1: Standard Kubernetes Ingress (Recommended for simplicity)
Uses the standard Kubernetes Ingress resource with TLS configuration.

### Option 2: Traefik IngressRoute (Recommended for advanced features)
Uses Traefik CRDs for more control and features like HTTP->HTTPS redirect.

## Deployment

### Step 1: Ensure cert-manager is installed
```bash
kubectl get pods -n cert-manager
```

### Step 2: Apply ClusterIssuer and Certificate
```bash
kubectl apply -f /home/holon/Projects/unity/k8s/tls/selfsigned-issuer.yaml
```

### Step 3: Choose your ingress approach

#### Option A: Standard Ingress (Updated main ingress)
```bash
kubectl apply -f /home/holon/Projects/unity/k8s/deployments/ingress.yaml
```

#### Option B: Traefik IngressRoute (Advanced with HTTP redirect)
```bash
kubectl apply -f /home/holon/Projects/unity/k8s/tls/ingress-https-fixed.yaml
```

### Step 4: Verify Certificate
```bash
# Check certificate status
kubectl get certificate -n unity

# Check certificate details
kubectl describe certificate unity-tls -n unity

# Verify secret was created
kubectl get secret unity-tls-cert -n unity
```

### Step 5: Test HTTPS Access
```bash
# Add to /etc/hosts if not already done
echo "127.0.0.1 unity.homelab.local ui.homelab.local" | sudo tee -a /etc/hosts

# Test HTTPS (will show certificate warning for self-signed)
curl -k https://unity.homelab.local
curl -k https://ui.homelab.local

# Test HTTP redirect (if using IngressRoute)
curl -I http://unity.homelab.local
```

## Certificate Issuers

### Self-Signed Issuer (Development)
- **Name**: `selfsigned-issuer`
- **Use case**: Local development, testing
- **File**: `selfsigned-issuer.yaml`
- **Browser warning**: Yes (self-signed)

### Let's Encrypt with Cloudflare (Production)
- **Name**: `letsencrypt-cloudflare`
- **Use case**: Production domains with Cloudflare DNS
- **File**: `/home/holon/Projects/unity/issuers.yaml`
- **Requires**: Cloudflare API token secret

To switch to Let's Encrypt for production:
1. Update ingress annotation: `cert-manager.io/cluster-issuer: letsencrypt-cloudflare`
2. Update Certificate issuerRef in `selfsigned-issuer.yaml`
3. Ensure Cloudflare API token secret exists

## Troubleshooting

### Certificate not issued
```bash
# Check certificate status
kubectl describe certificate unity-tls -n unity

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager
```

### Ingress not working
```bash
# Check ingress status
kubectl describe ingress unity-ingress -n unity

# Check Traefik logs
kubectl logs -n kube-system deployment/traefik
```

### Browser shows certificate error
This is expected for self-signed certificates. Options:
1. Accept the security exception in browser
2. Import the CA certificate to your system trust store
3. Use Let's Encrypt for production

## Files

- `selfsigned-issuer.yaml`: ClusterIssuer and Certificate for self-signed certs
- `ingress-https-fixed.yaml`: Traefik IngressRoute with TLS and HTTP->HTTPS redirect
- `ingress-https.yaml`: Alternative IngressRoute configuration
- `/home/holon/Projects/unity/issuers.yaml`: Production ClusterIssuers for Let's Encrypt and SmallStep

## Switching Between HTTP and HTTPS

### Using Standard Ingress
The main ingress at `/home/holon/Projects/unity/k8s/deployments/ingress.yaml` now supports both HTTP and HTTPS.

### Using IngressRoute
If you apply `ingress-https-fixed.yaml`, it will:
1. Create HTTPS routes on the `websecure` entrypoint
2. Create HTTP routes that redirect to HTTPS
3. Automatically redirect all HTTP traffic to HTTPS

## Next Steps

1. For production: Configure Let's Encrypt with Cloudflare DNS
2. For local trust: Import the self-signed CA certificate
3. Monitor certificate renewal (cert-manager handles this automatically)
