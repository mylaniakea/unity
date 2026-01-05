#!/bin/bash
set -e

echo "================================================"
echo "Unity TLS/HTTPS with Traefik IngressRoute"
echo "Advanced Configuration with HTTP->HTTPS Redirect"
echo "================================================"
echo ""

# Check if cert-manager is installed
echo "Step 1: Checking cert-manager installation..."
if kubectl get namespace cert-manager &> /dev/null; then
    echo "✓ cert-manager namespace exists"
else
    echo "✗ cert-manager is not installed!"
    exit 1
fi
echo ""

# Apply ClusterIssuer and Certificate
echo "Step 2: Applying ClusterIssuer and Certificate..."
kubectl apply -f /home/holon/Projects/unity/k8s/tls/selfsigned-issuer.yaml
echo "✓ Applied selfsigned-issuer and unity-tls certificate"
echo ""

# Wait for certificate to be ready
echo "Step 3: Waiting for certificate to be issued..."
for i in {1..30}; do
    if kubectl get certificate unity-tls -n unity -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null | grep -q "True"; then
        echo "✓ Certificate unity-tls is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "✗ Certificate not ready after 30 seconds"
        exit 1
    fi
    echo "  Waiting for certificate... ($i/30)"
    sleep 1
done
echo ""

# Remove standard ingress if it exists
echo "Step 4: Removing standard Ingress (if exists)..."
if kubectl get ingress unity-ingress -n unity &> /dev/null; then
    kubectl delete ingress unity-ingress -n unity
    echo "✓ Removed standard ingress"
else
    echo "  No standard ingress found, skipping"
fi
echo ""

# Apply Traefik IngressRoute with TLS and redirect
echo "Step 5: Applying Traefik IngressRoute with TLS..."
kubectl apply -f /home/holon/Projects/unity/k8s/tls/ingress-https-fixed.yaml
echo "✓ Applied IngressRoute with:"
echo "  - HTTPS routes on websecure entrypoint"
echo "  - HTTP->HTTPS redirect middleware"
echo "  - HTTP routes that redirect to HTTPS"
echo ""

# Verify IngressRoutes
echo "Step 6: Verifying IngressRoute configuration..."
echo "HTTPS Routes:"
kubectl get ingressroute unity-frontend-https unity-backend-https -n unity 2>/dev/null || echo "  Not found"
echo ""
echo "HTTP Routes (with redirect):"
kubectl get ingressroute unity-frontend-http unity-backend-http -n unity 2>/dev/null || echo "  Not found"
echo ""
echo "Middleware:"
kubectl get middleware https-redirect -n unity 2>/dev/null || echo "  Not found"
echo ""

# Show next steps
echo "================================================"
echo "Advanced TLS Configuration Complete!"
echo "================================================"
echo ""
echo "Features enabled:"
echo "✓ HTTPS on unity.homelab.local and ui.homelab.local"
echo "✓ Automatic HTTP->HTTPS redirect"
echo "✓ Self-signed certificate (valid for 1 year)"
echo ""
echo "Next steps:"
echo "1. Add hosts to /etc/hosts (if not already done):"
echo "   echo '127.0.0.1 unity.homelab.local ui.homelab.local' | sudo tee -a /etc/hosts"
echo ""
echo "2. Test HTTPS access:"
echo "   curl -k https://unity.homelab.local/health"
echo "   curl -k https://ui.homelab.local"
echo ""
echo "3. Test HTTP redirect:"
echo "   curl -I http://unity.homelab.local"
echo "   # Should see: HTTP/1.1 308 Permanent Redirect"
echo "   # Location: https://unity.homelab.local"
echo ""
echo "4. Access in browser (accept self-signed certificate warning):"
echo "   https://unity.homelab.local"
echo "   https://ui.homelab.local"
echo ""
echo "To switch to Let's Encrypt for production:"
echo "  1. kubectl apply -f /home/holon/Projects/unity/issuers.yaml"
echo "  2. Update Certificate issuerRef to: letsencrypt-cloudflare"
echo "  3. Ensure Cloudflare API token secret exists"
echo ""
