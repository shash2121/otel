output "secret_arn" {
  value       = aws_secretsmanager_secret.this.arn
  description = "Secret ARN"
}

output "secret_name" {
  value       = aws_secretsmanager_secret.this.name
  description = "Secret name"
}
