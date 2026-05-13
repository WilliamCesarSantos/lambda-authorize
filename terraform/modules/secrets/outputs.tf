output "db_password" {
  description = "Generated database password"
  value       = random_password.db_password.result
  sensitive   = true
}

output "db_password_secret_arn" {
  description = "ARN of the db-password secret"
  value       = aws_secretsmanager_secret.db_password.arn
}

output "pepper_secret_arn" {
  description = "ARN of the pepper secret"
  value       = aws_secretsmanager_secret.pepper.arn
}

output "private_key_secret_arn" {
  description = "ARN of the private-key secret"
  value       = aws_secretsmanager_secret.private_key.arn
}

output "public_key_secret_arn" {
  description = "ARN of the public-key secret"
  value       = aws_secretsmanager_secret.public_key.arn
}
