#!/bin/bash
# Certificate setup script for kc-booth production deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSL_DIR="${SCRIPT_DIR}/nginx/ssl"

echo "=================================="
echo "kc-booth Certificate Setup"
echo "=================================="
echo ""

# Create SSL directory
mkdir -p "${SSL_DIR}"

echo "Choose certificate type:"
echo "1) Self-signed certificate (for testing/internal use)"
echo "2) Let's Encrypt certificate (for production with domain)"
echo ""
read -p "Enter choice [1-2]: " choice

case $choice in
  1)
    echo ""
    echo "Generating self-signed certificate..."
    echo ""
    read -p "Enter hostname/domain (e.g., kc-booth.local): " DOMAIN
    
    openssl req -x509 -nodes -days 365 \
      -newkey rsa:4096 \
      -keyout "${SSL_DIR}/key.pem" \
      -out "${SSL_DIR}/cert.pem" \
      -subj "/CN=${DOMAIN}/O=kc-booth/C=US" \
      -addext "subjectAltName=DNS:${DOMAIN},DNS:localhost"
    
    echo ""
    echo "✓ Self-signed certificate generated"
    echo "  Certificate: ${SSL_DIR}/cert.pem"
    echo "  Key: ${SSL_DIR}/key.pem"
    echo ""
    echo "⚠️  WARNING: Self-signed certificates will show security warnings"
    echo "   in browsers. Only use for testing or internal deployments."
    ;;
    
  2)
    echo ""
    echo "Setting up Let's Encrypt certificate..."
    echo ""
    read -p "Enter your domain (e.g., kc-booth.example.com): " DOMAIN
    read -p "Enter your email address: " EMAIL
    
    echo ""
    echo "Instructions for Let's Encrypt setup:"
    echo ""
    echo "1. Ensure your domain points to this server's IP address"
    echo "2. Ensure ports 80 and 443 are open in your firewall"
    echo "3. Start the services with HTTP only first:"
    echo "   docker compose -f docker-compose.prod.yml up -d nginx certbot"
    echo ""
    echo "4. Run certbot to obtain certificate:"
    echo "   docker compose -f docker-compose.prod.yml exec certbot \\"
    echo "     certbot certonly --webroot \\"
    echo "     -w /var/www/certbot \\"
    echo "     -d ${DOMAIN} \\"
    echo "     --email ${EMAIL} \\"
    echo "     --agree-tos --no-eff-email"
    echo ""
    echo "5. Create symlinks to certificates:"
    echo "   ln -sf /etc/letsencrypt/live/${DOMAIN}/fullchain.pem ${SSL_DIR}/cert.pem"
    echo "   ln -sf /etc/letsencrypt/live/${DOMAIN}/privkey.pem ${SSL_DIR}/key.pem"
    echo ""
    echo "6. Restart nginx:"
    echo "   docker compose -f docker-compose.prod.yml restart nginx"
    echo ""
    echo "Note: Certificate will auto-renew every 12 hours via certbot service"
    ;;
    
  *)
    echo "Invalid choice. Exiting."
    exit 1
    ;;
esac

echo ""
echo "✓ Certificate setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and fill in values"
echo "2. Start production services:"
echo "   docker compose -f docker-compose.prod.yml up --build -d"
echo "3. Create admin user:"
echo "   python3 create_admin_user.py"
echo ""
