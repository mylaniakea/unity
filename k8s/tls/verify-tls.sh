#!/bin/bash

echo "================================================"
echo "Unity TLS/HTTPS Verification"
echo "================================================"
echo ""

# Check cert-manager
echo "1. cert-manager Status:"
echo "---"
kubectl get pods -n cert-manager
echo ""

# Check ClusterIssuers
echo "2. ClusterIssuers:"
echo "---"
kubectl get clusterissuers
echo ""

# Check Certificate
echo "3. Certificate Status:"
echo "---"
kubectl get certificate -n unity
echo ""
kubectl describe certificate unity-tls -n unity | grep -A 10 "Status:"
echo ""

# Check Secret
echo "4. TLS Secret:"
echo "---"
kubectl get secret unity-tls-cert -n unity
echo ""

# Check Ingress
echo "5. Ingress Configuration:"
echo "---"
if kubectl get ingress unity-ingress -n unity &> /dev/null; then
    echo "Standard Ingress:"
    kubectl get ingress unity-ingress -n unity
    echo ""
    kubectl describe ingress unity-ingress -n unity | grep -A 5 "TLS:"
fi
echo ""

# Check IngressRoutes
echo "6. Traefik IngressRoutes:"
echo "---"
if kubectl get ingressroute -n unity &> /dev/null 2>&1; then
    kubectl get ingressroute -n unity
else
    echo "No IngressRoutes found"
fi
echo ""

# Check Middleware
echo "7. Traefik Middleware:"
echo "---"
if kubectl get middleware -n unity &> /dev/null 2>&1; then
    kubectl get middleware -n unity
else
    echo "No Middleware found"
fi
echo ""

# Test connectivity
echo "8. Connectivity Tests:"
echo "---"

# Check if hosts are resolvable
if grep -q "unity.homelab.local" /etc/hosts; then
    echo "✓ Hosts configured in /etc/hosts"
else
    echo "✗ Hosts NOT in /etc/hosts"
    echo "  Add with: echo '127.0.0.1 unity.homelab.local ui.homelab.local' | sudo tee -a /etc/hosts"
fi
echo ""

# Test HTTPS endpoints
echo "Testing HTTPS endpoints..."
echo ""

echo "Backend health check:"
if curl -k -s -o /dev/null -w "%{http_code}" https://unity.homelab.local/health 2>/dev/null | grep -q "200\|308"; then
    echo "✓ https://unity.homelab.local/health is reachable"
    curl -k -s https://unity.homelab.local/health 2>/dev/null || echo "Response received"
else
    echo "✗ https://unity.homelab.local/health is not reachable"
fi
echo ""

echo "Frontend:"
HTTP_CODE=$(curl -k -s -o /dev/null -w "%{http_code}" https://ui.homelab.local 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "304" ]; then
    echo "✓ https://ui.homelab.local is reachable (HTTP $HTTP_CODE)"
else
    echo "✗ https://ui.homelab.local returned HTTP $HTTP_CODE"
fi
echo ""

echo "HTTP redirect test:"
REDIRECT=$(curl -s -o /dev/null -w "%{http_code} -> %{redirect_url}" http://unity.homelab.local 2>/dev/null || echo "Failed")
echo "http://unity.homelab.local: $REDIRECT"
echo ""

# Certificate details
echo "9. Certificate Details:"
echo "---"
if kubectl get secret unity-tls-cert -n unity &> /dev/null; then
    echo "Certificate info:"
    kubectl get secret unity-tls-cert -n unity -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -text | grep -A 2 "Subject:\|Issuer:\|Not Before\|Not After\|DNS:"
else
    echo "✗ Certificate secret not found"
fi
echo ""

echo "================================================"
echo "Verification Complete"
echo "================================================"
echo ""
echo "Browser access:"
echo "  https://unity.homelab.local (Backend API)"
echo "  https://ui.homelab.local (Frontend UI)"
echo ""
echo "Note: Self-signed certificates will show a browser warning."
echo "Click 'Advanced' and 'Accept Risk' to proceed."
echo ""
