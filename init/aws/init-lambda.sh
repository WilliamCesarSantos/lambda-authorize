#!/bin/bash
set -e

REGION="sa-east-1"
ACCOUNT_ID="000000000000"
FUNCTION_NAME="lambda-authorize"

# --------------------------------------------------------------------------
# Lambda
# --------------------------------------------------------------------------
echo "[localstack-init] Creating Lambda function from ZIP..."

awslocal lambda create-function \
  --function-name "$FUNCTION_NAME" \
  --runtime python3.13 \
  --handler lambda_function.lambda_handler \
  --zip-file fileb:///var/lib/localstack/lambda-zip/lambda.zip \
  --role "arn:aws:iam::${ACCOUNT_ID}:role/lambda-role" \
  --timeout 30 \
  --memory-size 256 \
  --environment "Variables={DB_HOST=postgres,DB_PORT=5432,DB_NAME=lambdaauth,DB_USER=lambda,DB_PASSWORD=lambda,AWS_ENDPOINT_URL=http://localstack:4566,AWS_ACCESS_KEY_ID=dummy,AWS_SECRET_ACCESS_KEY=dummy,AWS_REGION=${REGION},JWT_EXPIRATION_HOURS=1,PEPPER_SECRET_NAME=/lambda-authorize/pepper,PRIVATE_KEY_SECRET_NAME=/lambda-authorize/private-key,PUBLIC_KEY_SECRET_NAME=/lambda-authorize/public-key,JWKS_KID=dev-key-1}" \
  --region "$REGION"

echo "[localstack-init] Waiting for Lambda to become active..."
awslocal lambda wait function-active \
  --function-name "$FUNCTION_NAME" \
  --region "$REGION"

# --------------------------------------------------------------------------
# API Gateway
# --------------------------------------------------------------------------
echo "[localstack-init] Creating REST API Gateway..."

REST_API_ID=$(awslocal apigateway create-rest-api \
  --name "lambda-authorize-api" \
  --region "$REGION" \
  --query 'id' --output text)

echo "[localstack-init] REST API ID: $REST_API_ID"

ROOT_ID=$(awslocal apigateway get-resources \
  --rest-api-id "$REST_API_ID" \
  --region "$REGION" \
  --query 'items[0].id' --output text)

LOGIN_ID=$(awslocal apigateway create-resource \
  --rest-api-id "$REST_API_ID" \
  --parent-id "$ROOT_ID" \
  --path-part "login" \
  --region "$REGION" \
  --query 'id' --output text)

awslocal apigateway put-method \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$LOGIN_ID" \
  --http-method POST \
  --authorization-type NONE \
  --region "$REGION"

LAMBDA_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}"

awslocal apigateway put-integration \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$LOGIN_ID" \
  --http-method POST \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/${LAMBDA_ARN}/invocations" \
  --region "$REGION"

awslocal apigateway create-deployment \
  --rest-api-id "$REST_API_ID" \
  --stage-name prod \
  --region "$REGION"

# --------------------------------------------------------------------------
# Custom domain → http://localhost:4566/auth/v1/login
# --------------------------------------------------------------------------
echo "[localstack-init] Configuring custom domain mapping..."

awslocal apigateway create-domain-name \
  --domain-name localhost \
  --endpoint-configuration '{"types":["REGIONAL"]}' \
  --region "$REGION"

awslocal apigateway create-base-path-mapping \
  --domain-name localhost \
  --base-path "auth/v1" \
  --rest-api-id "$REST_API_ID" \
  --stage prod \
  --region "$REGION"

echo "[localstack-init] Saving API ID for nginx gateway..."
mkdir -p /gateway-config
echo "$REST_API_ID" > /gateway-config/api-id.txt

echo "[localstack-init] Setup complete."
echo "[localstack-init] Endpoint: POST http://localhost:4566/auth/v1/login"
