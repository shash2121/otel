locals {
  name_prefix = "${var.environment_name}-"

  common_tags = merge(var.tags, {
    Environment = var.environment_name
    ManagedBy   = "Terraform"
  })
}
