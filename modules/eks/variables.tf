variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "otel-eks"
}

variable "cluster_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.31"
}

variable "node_group_name" {
  description = "Node group name"
  type        = string
  default     = "otel-node-group"
}

variable "node_group_instance_types" {
  description = "Node group instance types"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_group_desired_size" {
  description = "Desired node count"
  type        = number
  default     = 2
}

variable "node_group_min_size" {
  description = "Min node count"
  type        = number
  default     = 1
}

variable "node_group_max_size" {
  description = "Max node count"
  type        = number
  default     = 3
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs for EKS"
  type        = list(string)
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "db_secret_name" {
  description = "Secrets Manager secret name for RDS credentials"
  type        = string
  default     = ""
}

variable "db_identifier" {
  description = "RDS instance identifier for IAM policy"
  type        = string
  default     = ""
}

variable "pod_identity_sa_name" {
  description = "Service account name for pod identity association"
  type        = string
  default     = "otel-demo-sa"
}
