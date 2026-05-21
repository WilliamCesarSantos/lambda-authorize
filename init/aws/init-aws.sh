#!/bin/bash
set -e

REGION="sa-east-1"

awslocal secretsmanager create-secret \
  --name /lambda-authorize/pepper \
  --secret-string "dev-pepper" \
  --region "$REGION"

awslocal secretsmanager create-secret \
  --name /lambda-authorize/private-key \
  --secret-string "$(cat /usr/share/localstack/certs/private.pem)" \
  --region "$REGION"

awslocal secretsmanager create-secret \
  --name /lambda-authorize/public-key \
  --secret-string "$(cat /usr/share/localstack/certs/public.pem)" \
  --region "$REGION"

awslocal secretsmanager create-secret \
  --name /lambda-authorize/db-password \
  --secret-string "lambda" \
  --region "$REGION"

echo "[localstack-init] Secrets created successfully."
