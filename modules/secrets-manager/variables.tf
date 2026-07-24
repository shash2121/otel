variable "secret_name" {
  description = "Secret name in AWS Secrets Manager"
  type        = string
}

variable "description" {
  description = "Secret description"
  type        = string
  default     = "Managed by Terraform"
}

variable "secret_string" {
  description = "Key-value pairs to store"
  type        = map(string)
}

variable "recovery_window_in_days" {
  description = "Days before permanent deletion (0 = immediate)"
  type        = number
  default     = 0
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
