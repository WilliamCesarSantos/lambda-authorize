#!/bin/sh
set -e

API_ID_FILE="/gateway-config/api-id.txt"

echo "[gateway] Waiting for API Gateway ID..."
until [ -f "$API_ID_FILE" ] && [ -s "$API_ID_FILE" ]; do
  sleep 1
done

REST_API_ID=$(cat "$API_ID_FILE")
echo "[gateway] REST API ID: $REST_API_ID"

cat > /etc/nginx/conf.d/default.conf << EOF
server {
    listen 80;

    location = /auth/v1/login {
        proxy_pass http://localstack:4566/_aws/execute-api/${REST_API_ID}/prod/login;
        proxy_set_header Host "localstack:4566";
        proxy_pass_request_headers on;
        proxy_pass_request_body on;
        proxy_buffering off;
    }

    location / {
        proxy_pass http://localstack:4566;
        proxy_set_header Host \$http_host;
        proxy_pass_request_headers on;
        proxy_pass_request_body on;
    }
}
EOF

echo "[gateway] nginx config written, starting..."
exec nginx -g "daemon off;"
