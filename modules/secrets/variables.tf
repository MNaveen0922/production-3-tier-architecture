variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}


variable "recovery_window_days" {
  description = "Days a deleted secret stays recoverable before permanent purge (0 = immediate delete)"
  type        = number
  default     = 0
}


variable "jwt_key_length" {
  description = "Character length of the generated JWT signing key"
  type        = number
  default     = 64
}
