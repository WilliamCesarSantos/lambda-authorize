output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = [aws_subnet.private_a.id, aws_subnet.private_b.id]
}

output "sg_lambda_id" {
  description = "Lambda security group ID"
  value       = aws_security_group.lambda.id
}

output "sg_aurora_id" {
  description = "Aurora security group ID"
  value       = aws_security_group.aurora.id
}
