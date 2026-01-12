#!/bin/bash
set -e

echo "================================================"
echo "Unity TLS/HTTPS Configuration Deployment"
echo "================================================"
echo ""

# Check if cert-manager is installed
echo "Step 1: Checking cert-manager installation..."
if kubectl get namespace cert-manager &> /dev/null; then
    echo "✓ cert-manager namespace exists"
    CERT_MANAGER_PODS=$(kubectl get pods -n cert-manager --no-headers 2>/dev/null | wc -l)
    echo "✓ Found $CERT_MANAGER_PODS cert-manager pods"
else
    echo "✗ cert-manager is not installed!"
    echo "  Install with: kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml"
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
        echo "  Check status with: kubectl describe certificate unity-tls -n unity"
        exit 1
    fi
    echo "  Waiting for certificate... ($i/30)"
    sleep 1
done
echo ""

# Apply updated ingress
echo "Step 4: Applying TLS-enabled ingress..."
kubectl apply -f /home/holon/Projects/unity/k8s/deployments/ingress.yaml
echo "✓ Applied unity-ingress with TLS configuration"
echo ""

# Verify ingress
echo "Step 5: Verifying ingress configuration..."
if kubectl get ingress unity-ingress -n unity &> /dev/null; then
    echo "✓ Ingress unity-ingress exists"
    kubectl get ingress unity-ingress -n unity
else
    echo "✗ Ingress not found"
    exit 1
fi
echo ""

# Show certificate details
echo "Step 6: Certificate details..."
kubectl describe certificate unity-tls -n unity | grep -A 5 "Status:"
echo ""

# Show next steps
echo "================================================"
echo "TLS/HTTPS Configuration Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Add hosts to /etc/hosts (if not already done):"
echo "   echo '127.0.0.1 unity.homelab.local ui.homelab.local' | sudo tee -a /etc/hosts"
echo ""
echo "2. Test HTTPS access:"
echo "   curl -k https://unity.homelab.local/health"
echo "   curl -k https://ui.homelab.local"
echo ""
echo "3. Access in browser (accept self-signed certificate warning):"
echo "   https://unity.homelab.local"
echo "   https://ui.homelab.local"
echo ""
echo "4. (Optional) For HTTP->HTTPS redirect with Traefik IngressRoute:"
echo "   kubectl apply -f /home/holon/Projects/unity/k8s/tls/ingress-https-fixed.yaml"
echo "   kubectl delete ingress unity-ingress -n unity"
echo ""
echo "Certificate Secret: unity-tls-cert"
echo "Issuer: selfsigned-issuer (ClusterIssuer)"
echo "Valid for: unity.homelab.local, ui.homelab.local, *.homelab.local"
echo ""
