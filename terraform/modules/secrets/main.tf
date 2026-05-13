resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_secretsmanager_secret" "db_password" {
  name = "/lambda-authorize/db-password"

  tags = {
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db_password.result
}

resource "aws_secretsmanager_secret" "pepper" {
  name = "/lambda-authorize/pepper"

  tags = {
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "pepper" {
  secret_id     = aws_secretsmanager_secret.pepper.id
  secret_string = var.pepper
}

resource "aws_secretsmanager_secret" "private_key" {
  name = "/lambda-authorize/private-key"

  tags = {
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "private_key" {
  secret_id     = aws_secretsmanager_secret.private_key.id
  secret_string = var.private_key_pem
}

resource "aws_secretsmanager_secret" "public_key" {
  name = "/lambda-authorize/public-key"

  tags = {
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "public_key" {
  secret_id     = aws_secretsmanager_secret.public_key.id
  secret_string = var.public_key_pem
}
