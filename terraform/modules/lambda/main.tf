data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "lambda-authorize-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = {
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "vpc_access" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

data "aws_iam_policy_document" "secrets_access" {
  statement {
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      var.db_password_secret_arn,
      var.pepper_secret_arn,
      var.private_key_secret_arn,
      var.public_key_secret_arn,
    ]
  }
}

resource "aws_iam_role_policy" "secrets_access" {
  name   = "secrets-access-${var.environment}"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.secrets_access.json
}

resource "aws_lambda_function" "main" {
  function_name = "lambda-authorize-${var.environment}"
  role          = aws_iam_role.lambda.arn
  filename      = var.lambda_zip_path
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.13"
  timeout       = 30
  memory_size   = 256

  source_code_hash = filebase64sha256(var.lambda_zip_path)

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [var.security_group_id]
  }

  environment {
    variables = {
      DB_HOST                  = var.db_host
      DB_PORT                  = "5432"
      DB_NAME                  = "lambdaauth"
      DB_USER                  = "lambda"
      DB_PASSWORD              = ""
      AWS_REGION               = var.aws_region
      JWT_EXPIRATION_HOURS     = "1"
      PEPPER_SECRET_NAME       = "/lambda-authorize/pepper"
      PRIVATE_KEY_SECRET_NAME  = "/lambda-authorize/private-key"
      PUBLIC_KEY_SECRET_NAME   = "/lambda-authorize/public-key"
      JWKS_KID                 = var.jwks_kid
    }
  }

  tags = {
    Environment = var.environment
  }
}
