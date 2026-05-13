terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  backend "s3" {}
}

provider "aws" {
  region = var.aws_region
}

module "networking" {
  source = "./modules/networking"

  environment = var.environment
}

module "secrets" {
  source = "./modules/secrets"

  environment     = var.environment
  pepper          = var.pepper
  private_key_pem = var.private_key_pem
  public_key_pem  = var.public_key_pem
}

module "rds" {
  source = "./modules/rds"

  environment        = var.environment
  subnet_ids         = module.networking.private_subnet_ids
  security_group_id  = module.networking.sg_aurora_id
  db_password        = module.secrets.db_password
  aurora_min_capacity = var.aurora_min_capacity
  aurora_max_capacity = var.aurora_max_capacity
}

module "lambda" {
  source = "./modules/lambda"

  environment           = var.environment
  aws_region            = var.aws_region
  subnet_ids            = module.networking.private_subnet_ids
  security_group_id     = module.networking.sg_lambda_id
  lambda_zip_path       = var.lambda_zip_path
  db_host               = module.rds.cluster_endpoint
  db_password_secret_arn = module.secrets.db_password_secret_arn
  pepper_secret_arn     = module.secrets.pepper_secret_arn
  private_key_secret_arn = module.secrets.private_key_secret_arn
  public_key_secret_arn  = module.secrets.public_key_secret_arn
  jwks_kid              = var.jwks_kid
}
