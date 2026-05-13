#!/bin/bash
set -e

awslocal secretsmanager create-secret \
  --name /lambda-authorize/pepper \
  --secret-string "dev-pepper-DO-NOT-USE-IN-PRODUCTION"

awslocal secretsmanager create-secret \
  --name /lambda-authorize/private-key \
  --secret-string "$(cat /certs/private.pem)"

awslocal secretsmanager create-secret \
  --name /lambda-authorize/public-key \
  --secret-string "$(cat /certs/public.pem)"

awslocal secretsmanager create-secret \
  --name /lambda-authorize/db-password \
  --secret-string "lambda"

echo "[localstack-init] Secrets created successfully."
