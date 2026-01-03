#!/bin/bash

# TLS/SSL Setup for Unity Platform
# SmallStep (internal) + Cloudflare/Let's Encrypt (public)

set -e

SMALLSTEP_CA_URL="https://pki.mylaniakea.ca.smallstep.com"
SMALLSTEP_ACME_PROVISIONER="${SMALLSTEP_ACME_PROVISIONER:-acme}"
CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:-}"
SMALLSTEP_CA_FINGERPRINT="${SMALLSTEP_CA_FINGERPRINT:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Unity TLS/SSL Setup${NC}"
echo "===================="
echo ""

# Step 1: Verify cert-manager is ready
echo -e "${YELLOW}Step 1: Checking cert-manager...${NC}"
if kubectl get pod -l app.kubernetes.io/name=cert-manager -n cert-manager &>/dev/null; then
    echo -e "${GREEN}✓ cert-manager is running${NC}"
else
    echo -e "${RED}✗ cert-manager not found. Run Phase 1 first.${NC}"
    exit 1
fi

# Step 2: Get SmallStep root certificate
echo ""
echo -e "${YELLOW}Step 2: Downloading SmallStep root certificate...${NC}"
mkdir -p /tmp/smallstep
curl -s "$SMALLSTEP_CA_URL/roots.pem" -o /tmp/smallstep/root.pem
if [ -f /tmp/smallstep/root.pem ]; then
    echo -e "${GREEN}✓ Downloaded SmallStep root certificate${NC}"
    # Get fingerprint
    FINGERPRINT=$(step certificate fingerprint /tmp/smallstep/root.pem)
    echo "  Fingerprint: $FINGERPRINT"
else
    echo -e "${RED}✗ Failed to download root certificate${NC}"
    exit 1
fi

# Step 3: Create secrets namespace
echo ""
echo -e "${YELLOW}Step 3: Creating Kubernetes secrets...${NC}"
kubectl create secret tls smallstep-root \
    --cert=/tmp/smallstep/root.pem \
    --key=/tmp/smallstep/root.pem \
    -n homelab \
    --dry-run=client -o yaml | kubectl apply -f -
echo -e "${GREEN}✓ SmallStep root certificate secret created${NC}"

# Step 4: Cloudflare secret
if [ -z "$CLOUDFLARE_API_TOKEN" ]; then
    echo -e "${RED}✗ CLOUDFLARE_API_TOKEN not set${NC}"
    echo "  Set it: export CLOUDFLARE_API_TOKEN=<token>"
    exit 1
fi

kubectl create secret generic cloudflare-api-token \
    --from-literal=api-token="$CLOUDFLARE_API_TOKEN" \
    -n homelab \
    --dry-run=client -o yaml | kubectl apply -f -
echo -e "${GREEN}✓ Cloudflare API token secret created${NC}"

echo ""
echo -e "${GREEN}Prerequisites complete! Ready for Phase 2-3.${NC}"

