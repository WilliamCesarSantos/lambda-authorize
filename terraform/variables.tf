variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "sa-east-1"
}

variable "environment" {
  description = "Deployment environment (e.g. production, staging)"
  type        = string
}

variable "pepper" {
  description = "Pepper value for password hashing"
  type        = string
  sensitive   = true
}

variable "private_key_pem" {
  description = "RSA private key PEM content"
  type        = string
  sensitive   = true
}

variable "public_key_pem" {
  description = "RSA public key PEM content"
  type        = string
  sensitive   = true
}

variable "jwks_kid" {
  description = "Key ID for JWKS"
  type        = string
  default     = "prod-key-1"
}

variable "aurora_min_capacity" {
  description = "Minimum Aurora Serverless v2 capacity (ACUs)"
  type        = number
  default     = 0.5
}

variable "aurora_max_capacity" {
  description = "Maximum Aurora Serverless v2 capacity (ACUs)"
  type        = number
  default     = 1.0
}

variable "lambda_zip_path" {
  description = "Path to the Lambda deployment ZIP file"
  type        = string
}
