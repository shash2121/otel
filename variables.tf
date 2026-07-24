variable "region" {
  description = "AWS region"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
}

variable "environment_name" {
  description = "Environment name"
  type        = string
}

variable "subnet_newbits" {
  description = "Subnet newbits"
  type        = number
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
}

variable "cluster_version" {
  description = "EKS cluster version"
  type        = string
}

variable "node_group_name" {
  description = "Node group name"
  type        = string
}

variable "node_group_instance_types" {
  description = "Node group instance types"
  type        = list(string)
}

variable "node_group_desired_size" {
  description = "Desired node count"
  type        = number
}

variable "node_group_min_size" {
  description = "Minimum node count"
  type        = number
}

variable "node_group_max_size" {
  description = "Maximum node count"
  type        = number
}

# RDS (PostgreSQL)
variable "db_identifier" {
  description = "RDS instance identifier"
  type        = string
  default     = "otel-demo-db"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "otel_demo"
}

variable "db_username" {
  description = "Master username"
  type        = string
  default     = "otel_admin"
}

variable "db_port" {
  description = "Database port"
  type        = number
  default     = 5432
}

variable "db_allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "secret_name" {
  description = "Secrets Manager secret name for RDS credentials"
  type        = string
  default     = "otel-demo-rds-credentials"
}

variable "pod_identity_sa_name" {
  description = "K8s service account for pod identity"
  type        = string
  default     = "otel-demo-sa"
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
