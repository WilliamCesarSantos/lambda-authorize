variable "environment" {
  description = "Deployment environment"
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
