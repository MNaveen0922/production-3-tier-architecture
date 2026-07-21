variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}


variable "ecr_repository_urls" {
  description = "Map of service name to ECR repository URL (from modules/ecr/)"
  type        = map(string)
}


variable "additional_parameters" {
  description = "Map of extra config key -> value to store as SSM parameters (non-secret config only - use modules/secrets/ for anything sensitive)"
  type        = map(string)
  default     = {}
}
