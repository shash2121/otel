output "db_instance_endpoint" {
  value       = aws_db_instance.this.address
  description = "RDS endpoint"
}

output "db_instance_port" {
  value       = aws_db_instance.this.port
  description = "RDS port"
}

output "db_instance_arn" {
  value       = aws_db_instance.this.arn
  description = "RDS ARN"
}

output "db_instance_identifier" {
  value       = aws_db_instance.this.identifier
  description = "RDS identifier"
}

output "db_instance_name" {
  value       = aws_db_instance.this.db_name
  description = "Database name"
}
