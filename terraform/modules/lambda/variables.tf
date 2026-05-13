variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for VPC config"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group ID for Lambda"
  type        = string
}

variable "lambda_zip_path" {
  description = "Path to the Lambda ZIP file"
  type        = string
}

variable "db_host" {
  description = "Aurora cluster endpoint"
  type        = string
}

variable "db_password_secret_arn" {
  description = "ARN of the db-password secret"
  type        = string
}

variable "pepper_secret_arn" {
  description = "ARN of the pepper secret"
  type        = string
}

variable "private_key_secret_arn" {
  description = "ARN of the private-key secret"
  type        = string
}

variable "public_key_secret_arn" {
  description = "ARN of the public-key secret"
  type        = string
}

variable "jwks_kid" {
  description = "Key ID for JWKS"
  type        = string
  default     = "prod-key-1"
}
