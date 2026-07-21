
output "alb_security_group_id" {
  description = "SG ID for the ALB - reference this in Ingress annotations: alb.ingress.kubernetes.io/security-groups"
  value       = module.vpc.alb_security_group_id
}

output "vpc_id" {
  description = "VPC ID - used by ALB Controller Helm install"
  value       = module.vpc.vpc_id
}


output "eks_cluster_name" {
  description = "EKS cluster name - use with: aws eks update-kubeconfig --name <this>"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "Kubernetes API server URL"
  value       = module.eks.cluster_endpoint
}


output "rds_endpoint" {
  description = "RDS host:port the app connects to"
  value       = module.rds.db_endpoint
}

output "rds_master_user_secret_arn" {
  description = "Secrets Manager ARN holding the AWS-managed RDS master password"
  value       = module.rds.db_master_user_secret_arn
}


output "ecr_repository_urls" {
  description = "Map of service name to ECR repository URL, for CI/CD docker push"
  value       = module.ecr.repository_urls
}


output "assets_bucket_name" {
  description = "Name of the S3 assets bucket"
  value       = module.s3.bucket_name
}


output "orders_queue_url" {
  description = "SQS event queue URL for app/worker pods"
  value       = module.sqs.orders_queue_url
}


output "sns_topic_arn" {
  description = "SNS alerts/notifications topic ARN - used by the worker pod to send notifications"
  value       = module.sns.sns_topic_arn
}


output "app_pod_role_arn" {
  description = "IAM Role ARN to annotate on the app's Kubernetes ServiceAccount (eks.amazonaws.com/role-arn)"
  value       = module.iam_irsa.app_pod_role_arn
}

output "alb_controller_role_arn" {
  description = "IAM Role ARN to annotate on the aws-load-balancer-controller ServiceAccount"
  value       = module.alb_controller.alb_controller_role_arn
}

output "cloudwatch_agent_role_arn" {
  description = "IAM Role ARN to annotate on the CloudWatch agent ServiceAccount"
  value       = module.iam_irsa.cloudwatch_agent_role_arn
}
