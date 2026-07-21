output "jwt_signing_key_secret_arn" {
  description = "ARN of the JWT signing key secret - used in IAM policies and app runtime config"
  value       = aws_secretsmanager_secret.jwt_signing_key.arn
}


output "jwt_signing_key_secret_name" {
  description = "Name of the JWT signing key secret"
  value       = aws_secretsmanager_secret.jwt_signing_key.name
}
