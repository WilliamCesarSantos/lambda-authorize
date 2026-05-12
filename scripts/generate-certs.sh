#!/usr/bin/env bash
# generate-certs.sh — Generates an RSA key pair for signing JWT tokens.
#
# Output (inside certs/):
#   private.pem     — RSA 2048-bit private key   (NEVER commit to git)
#   public.pem      — RSA public key             (safe to share)
#   certificate.pem — Self-signed X.509 cert     (safe to share; optional mTLS use)

set -euo pipefail

CERTS_DIR="$(cd "$(dirname "$0")/.." && pwd)/certs"
mkdir -p "$CERTS_DIR"

echo "Generating RSA 2048-bit private key..."
openssl genrsa -out "$CERTS_DIR/private.pem" 2048

echo "Extracting public key..."
openssl rsa -in "$CERTS_DIR/private.pem" -pubout -out "$CERTS_DIR/public.pem"

echo "Generating self-signed X.509 certificate (365 days)..."
openssl req -new -x509 \
  -key "$CERTS_DIR/private.pem" \
  -out "$CERTS_DIR/certificate.pem" \
  -days 365 \
  -subj "/CN=lambda-authorize/O=Example Org/C=BR"

chmod 600 "$CERTS_DIR/private.pem"
chmod 644 "$CERTS_DIR/public.pem" "$CERTS_DIR/certificate.pem"

echo ""
echo "Certificates written to: $CERTS_DIR"
echo "  private.pem     — RSA private key      [SECRET — never commit]"
echo "  public.pem      — RSA public key        [safe to share with other services]"
echo "  certificate.pem — Self-signed X.509 cert [safe to share]"
