output "security_group_id" {
  value       = aws_security_group.this.id
  description = "Security group ID"
}

output "security_group_arn" {
  value       = aws_security_group.this.arn
  description = "Security group ARN"
}
