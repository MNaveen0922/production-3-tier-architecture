
module "vpc" {
  source = "./modules/vpc"

  project_name       = var.project_name
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  nat_gateway_count  = var.nat_gateway_count
  alb_target_ports   = var.alb_target_ports
}

module "iam" {
  source = "./modules/iam"

  project_name = var.project_name
  environment  = var.environment
}

module "ecr" {
  source = "./modules/ecr"

  project_name = var.project_name
  environment  = var.environment
}

module "s3" {
  source = "./modules/s3"

  project_name         = var.project_name
  environment          = var.environment
  assets_bucket_suffix = var.assets_bucket_suffix
}

module "sqs" {
  source = "./modules/sqs"

  project_name = var.project_name
  environment  = var.environment
}

module "sns" {
  source = "./modules/sns"

  project_name = var.project_name
  environment  = var.environment
  alert_email  = var.alert_email
}

module "secrets" {
  source = "./modules/secrets"

  project_name = var.project_name
  environment  = var.environment
}


module "eks" {
  source = "./modules/eks"

  project_name = var.project_name
  environment  = var.environment


  vpc_id                      = module.vpc.vpc_id
  public_subnet_ids           = module.vpc.public_subnet_ids
  private_subnet_ids          = module.vpc.private_subnet_ids
  eks_nodes_security_group_id = module.vpc.eks_nodes_security_group_id


  eks_cluster_role_arn = module.iam.eks_cluster_role_arn
  eks_node_role_arn    = module.iam.eks_node_role_arn
}

module "rds" {
  source = "./modules/rds"

  project_name = var.project_name
  environment  = var.environment


  private_subnet_ids    = module.vpc.private_subnet_ids
  rds_security_group_id = module.vpc.rds_security_group_id

  db_multi_az = var.db_multi_az
}


module "alb_controller" {
  source = "./modules/alb-controller"

  project_name = var.project_name
  environment  = var.environment
  vpc_id       = module.vpc.vpc_id


  oidc_provider_arn = module.eks.oidc_provider_arn
  oidc_provider_url = module.eks.oidc_provider_url
}

module "iam_irsa" {
  source = "./modules/iam-irsa"

  project_name = var.project_name
  environment  = var.environment


  oidc_provider_arn = module.eks.oidc_provider_arn
  oidc_provider_url = module.eks.oidc_provider_url


  assets_bucket_arn          = module.s3.bucket_arn
  orders_queue_arn           = module.sqs.orders_queue_arn
  orders_dlq_arn             = module.sqs.orders_dlq_arn
  jwt_signing_key_secret_arn = module.secrets.jwt_signing_key_secret_arn
  rds_master_user_secret_arn = module.rds.db_master_user_secret_arn
}

module "ssm" {
  source = "./modules/ssm"

  project_name = var.project_name
  environment  = var.environment

  ecr_repository_urls = module.ecr.repository_urls

  additional_parameters = {
    eks_cluster_name = module.eks.cluster_name
    rds_endpoint     = module.rds.db_endpoint
    rds_db_name      = module.rds.db_name
    rds_db_user      = "admin"
    rds_secret_arn   = module.rds.db_master_user_secret_arn
    assets_bucket    = module.s3.bucket_name
    orders_queue_url = module.sqs.orders_queue_url
    sns_topic_arn    = module.sns.sns_topic_arn
    aws_region       = "us-east-1"
  }
}

module "cloudwatch" {
  source = "./modules/cloudwatch"

  project_name = var.project_name
  environment  = var.environment


  sns_topic_arn = module.sns.sns_topic_arn


  node_group_asg_name = module.eks.node_group_asg_name


  db_instance_id = module.rds.db_instance_id


  orders_dlq_name = module.sqs.orders_dlq_name
}
