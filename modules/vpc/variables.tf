variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment_name" {
  description = "Environment name"
  type        = string
  default     = "otel-demo"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_newbits" {
  description = "New bits for subnetting"
  type        = number
  default     = 8
}

variable "cluster_name" {
  description = "EKS cluster name for subnet tagging"
  type        = string
  default     = "otel-eks"
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
