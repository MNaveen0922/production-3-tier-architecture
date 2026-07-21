variable "project_name" {
  description = "Short name used as a prefix for every resource this module creates"
  type        = string
}

variable "environment" {
  description = "Environment name, e.g. 'prod' or 'dev'"
  type        = string
}

variable "vpc_cidr" {
  description = "IP address range for the whole VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Which AWS Availability Zones to spread subnets across (2, for high availability)"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "alb_target_ports" {
  description = "Real container ports the ALB Controller (target-type=ip mode) sends traffic to directly: frontend(80), auth(8001), ticket(8002), assignment(8003)"
  type        = list(number)
  default     = [80, 8001, 8002, 8003]
}

variable "nat_gateway_count" {
  description = "How many NAT Gateways: 1 = cheaper, shared, single point of failure. 2 = one per AZ, more resilient, costs more."
  type        = number
  default     = 1
}
