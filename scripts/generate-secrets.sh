#!/bin/bash

# MCP ADHD Server - Secrets Generation Script
# Generates secure secrets for production deployment

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

# Function to generate random string
generate_secret() {
    local length=${1:-32}
    openssl rand -hex $length
}

# Function to generate JWT secret
generate_jwt_secret() {
    openssl rand -base64 32
}

# Function to generate secure password
generate_password() {
    local length=${1:-16}
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
}

print_status "Generating secure secrets for MCP ADHD Server..."

echo ""
print_status "Copy these values to your .env file:"
echo ""

echo "# ============================================================================"
echo "# GENERATED SECRETS - $(date)"
echo "# ============================================================================"
echo ""

echo "# Application Security"
echo "SECRET_KEY=$(generate_secret 32)"
echo "JWT_SECRET=$(generate_jwt_secret)"
echo ""

echo "# Database Credentials"
echo "POSTGRES_PASSWORD=$(generate_password 20)"
echo ""

echo "# Grafana Admin Credentials"
echo "GRAFANA_PASSWORD=$(generate_password 16)"
echo ""

echo "# Build Information"
echo "BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
echo ""

print_success "Secrets generated successfully!"
print_warning "Store these secrets securely and never commit them to version control!"
print_warning "Consider using a secrets management service for production deployments."

echo ""
print_status "Next steps:"
echo "  1. Copy the generated values to your .env file"
echo "  2. Set appropriate file permissions: chmod 600 .env"
echo "  3. Add .env to .gitignore (already done)"
echo "  4. Consider using Docker secrets or Kubernetes secrets for orchestration"