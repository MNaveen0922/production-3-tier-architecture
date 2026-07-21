variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}


variable "sns_topic_arn" {
  description = "ARN of the alerts topic - every alarm below notifies here"
  type        = string
}


variable "node_group_asg_name" {
  description = "ASG backing the EKS managed node group - used for the CPU alarm dimension"
  type        = string
}


variable "db_instance_id" {
  description = "RDS instance identifier - used for the RDS alarm dimensions"
  type        = string
}


variable "orders_dlq_name" {
  description = "DLQ name - used for the DLQ depth alarm dimension"
  type        = string
}


variable "ec2_cpu_threshold" {
  type    = number
  default = 80
}

variable "rds_cpu_threshold" {
  type    = number
  default = 80
}


variable "rds_free_storage_threshold_bytes" {
  description = "Alarm fires when RDS free storage drops below this many bytes (default 5GB)"
  type        = number
  default     = 5368709120 
}


variable "app_services" {
  description = "List of app service names to create log groups for"
  type        = list(string)
  default     = ["auth", "ticket", "assignment", "frontend", "worker"]
}

variable "log_retention_days" {
  description = "How long CloudWatch keeps app logs before deleting them"
  type        = number
  default     = 14
}
