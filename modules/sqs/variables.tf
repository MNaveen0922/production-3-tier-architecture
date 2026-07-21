variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}


variable "max_receive_count" {
  description = "Number of failed processing attempts before a message goes to the DLQ"
  type        = number
  default     = 5
}


variable "visibility_timeout_seconds" {
  description = "Time a message is hidden from other consumers while one worker processes it"
  type        = number
  default     = 30
}


variable "message_retention_seconds" {
  description = "How long unconsumed messages are kept before permanent deletion"
  type        = number
  default     = 345600 
}
