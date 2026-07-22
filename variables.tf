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

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
