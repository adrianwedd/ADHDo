#!/bin/bash

# MCP ADHD Server - SSL Certificate Generation Script
# Generates self-signed SSL certificates for development/testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Default values
DOMAIN=${1:-localhost}
CERT_DIR="nginx/ssl"
KEY_SIZE=2048
DAYS=365

print_status "Generating SSL certificate for domain: $DOMAIN"

# Create SSL directory if it doesn't exist
mkdir -p "$CERT_DIR"

# Generate private key
print_status "Generating private key..."
openssl genrsa -out "$CERT_DIR/key.pem" $KEY_SIZE

# Create certificate configuration
cat > "$CERT_DIR/cert.conf" << EOF
[req]
default_bits = $KEY_SIZE
prompt = no
distinguished_name = dn
req_extensions = v3_req

[dn]
CN = $DOMAIN
O = MCP ADHD Server
C = US

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = $DOMAIN
DNS.2 = *.$DOMAIN
DNS.3 = localhost
DNS.4 = 127.0.0.1
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

# Generate certificate signing request and self-signed certificate
print_status "Generating certificate..."
openssl req -new -x509 -key "$CERT_DIR/key.pem" -out "$CERT_DIR/cert.pem" \
    -days $DAYS -config "$CERT_DIR/cert.conf" -extensions v3_req

# Set appropriate permissions
chmod 600 "$CERT_DIR/key.pem"
chmod 644 "$CERT_DIR/cert.pem"

# Clean up temporary files
rm "$CERT_DIR/cert.conf"

print_success "SSL certificate generated successfully!"
print_status "Certificate details:"
echo ""

# Display certificate information
openssl x509 -in "$CERT_DIR/cert.pem" -text -noout | grep -A 3 "Subject:"
openssl x509 -in "$CERT_DIR/cert.pem" -text -noout | grep -A 3 "Validity"
openssl x509 -in "$CERT_DIR/cert.pem" -text -noout | grep -A 10 "Subject Alternative Name"

echo ""
print_warning "This is a self-signed certificate for development/testing only!"
print_warning "For production, use certificates from a trusted CA like Let's Encrypt."

echo ""
print_status "Files generated:"
echo "  Private key: $CERT_DIR/key.pem"
echo "  Certificate: $CERT_DIR/cert.pem"

echo ""
print_status "To use with production CA:"
echo "  1. Generate CSR: openssl req -new -key $CERT_DIR/key.pem -out cert.csr -config cert.conf"
echo "  2. Submit CSR to your CA (Let's Encrypt, DigiCert, etc.)"
echo "  3. Replace $CERT_DIR/cert.pem with the CA-issued certificate"

echo ""
print_status "To start with SSL enabled:"
echo "  docker-compose --profile ssl up -d"