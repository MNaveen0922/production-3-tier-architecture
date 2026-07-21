
output "ecr_parameter_names" {
  description = "Map of service name to SSM parameter name for ECR repo URLs"
  value = {
    for name, param in aws_ssm_parameter.ecr_repository_url : name => param.name
  }
}


output "config_parameter_names" {
  description = "Map of config key to SSM parameter name for generic config values"
  value = {
    for name, param in aws_ssm_parameter.config : name => param.name
  }
}
