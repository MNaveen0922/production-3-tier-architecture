# Support Desk — Production-Grade 3-Tier Platform on AWS

An IT helpdesk ticketing application, fully containerized and deployed to
production on AWS EKS via Terraform + GitHub Actions. Built as a 3-tier
reference architecture: React frontend, FastAPI microservice backend,
MySQL database, with async messaging and notifications.

This is a different sample application from the reference project it was
modeled on, but follows the same repository layout, Terraform module
structure, CI/CD pattern, and Kubernetes manifests.

## Architecture

```
Internet
   │
   ▼
 ALB (public, created by AWS Load Balancer Controller from k8s/ingress.yaml)
   │
   ├── /auth      → auth-service      (FastAPI, :8001)
   ├── /tickets   → ticket-service    (FastAPI, :8002)
   ├── /assign    → assign-service    (FastAPI, :8003)
   └── /          → frontend-service  (React + Nginx, :80)

 EKS (private subnets)
   ├── auth-service, ticket-service, assign-service, frontend  (Deployments + HPA)
   ├── worker  (long-running SQS consumer, no HTTP port)
   └── aws-load-balancer-controller, CloudWatch agent, Fluent Bit (kube-system / amazon-cloudwatch)

 RDS MySQL (private subnets, SG allows only EKS nodes on :3306)
 SQS  (main queue + DLQ) — ticket-service/assign-service publish events
 SNS  (alerts topic, email subscription) — worker publishes ticket notifications, CI/CD publishes deploy status
 S3   (assets bucket) — private, encrypted, versioned
 SSM Parameter Store — non-secret runtime config (DB endpoint, queue URL, topic ARN, bucket name, ECR URLs)
 Secrets Manager — RDS master password (AWS-managed) + generated JWT signing key
 CloudWatch — log groups per service, dashboard, alarms (EKS node CPU, RDS CPU/storage, SQS DLQ depth) → SNS
```

## Why this domain

The reference project this was built from managed a digital library
(auth / book / borrow / worker / frontend). This project keeps the same
3-tier shape and the same AWS services, but implements a **support ticket
desk** instead:

| Reference concept | This project        |
|--------------------|---------------------|
| auth (signup/signin) | auth (signup/signin) |
| book (catalogue + CSV import) | ticket (catalogue + CSV import) |
| borrow (borrow a book) | assign (assign a ticket to an agent) |
| worker (SQS → email via SNS) | worker (SQS → email via SNS) |
| React frontend | React frontend |

## Repository layout

```
.
├── .github/workflows/
│   ├── ci-cd.yml            # test → build/push to ECR → Trivy scan → deploy to EKS → SNS notify
│   └── infrastructure.yml   # terraform fmt/validate/plan (PR) → apply (push) → install ALB controller
├── app/
│   ├── auth/                # FastAPI — signup, signin
│   ├── ticket/               # FastAPI — CRUD + CSV bulk import (queues rows to SQS)
│   ├── assignment/            # FastAPI — assign ticket to agent, list my assignments
│   ├── worker/               # long-running SQS consumer → SNS publisher, no docker-compose needed
│   ├── frontend/             # React (Vite) + Nginx, proxies /auth /tickets /assign
│   └── database/schema.sql  # MySQL schema + seed data (apply manually against RDS)
├── k8s/                      # namespace, serviceaccount (IRSA), configmap, 5 deployments+services,
│                              # ingress (ALB), HPA, CloudWatch agent + Fluent Bit daemonset
├── modules/                  # 13 reusable Terraform modules
│   ├── vpc/ iam/ ecr/ s3/ sqs/ sns/ secrets/ eks/ rds/
│   └── alb-controller/ iam-irsa/ ssm/ cloudwatch/
├── main.tf / variables.tf / outputs.tf / provider.tf / backend.tf
└── terraform.tfvars.example
```

No docker-compose, no shell scripts, and no GitHub OIDC — CI/CD authenticates
to AWS with long-lived access keys stored as GitHub Secrets, and all Docker
builds/pushes happen inside the `ci-cd.yml` pipeline itself.

## AWS services used

VPC · EKS · RDS (MySQL) · SQS · SNS · S3 · IAM (+ IRSA) · ALB (via AWS Load
Balancer Controller) · SSM Parameter Store · Secrets Manager · CloudWatch
(logs, alarms, dashboard) · ECR

## Deploying

### 1. One-time bootstrap
Create an S3 bucket for Terraform state and update `backend.tf` with its name.

### 2. terraform.tfvars
```bash
cp terraform.tfvars.example terraform.tfvars
```
Fill in:
- `assets_bucket_suffix` — any globally-unique string
- `alert_email` — e.g. `["mnaveen8639@gmail.com"]` (you'll get an SNS
  subscription-confirmation email after `apply` — click the link or you
  won't receive notifications)

### 3. GitHub Secrets
Set these in the repo's Settings → Secrets → Actions:

| Secret | Used by |
|---|---|
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | ci-cd.yml (ECR push, EKS deploy) |
| `AWS_ACCESS_KEY_ID_INFRA` / `AWS_SECRET_ACCESS_KEY_INFRA` | infrastructure.yml (Terraform apply) |
| `AWS_REGION` | both — `us-east-1` |
| `ECR_REGISTRY` | ci-cd.yml — `<account-id>.dkr.ecr.us-east-1.amazonaws.com` |
| `EKS_CLUSTER` | both — `support-desk-prod-eks` |
| `K8S_NAMESPACE` | ci-cd.yml — `support-desk` |
| `SNS_TOPIC_ARN` | ci-cd.yml — from `terraform output sns_topic_arn` |
| `TF_VERSION` | infrastructure.yml — e.g. `1.10.0` |
| `TF_VAR_ASSETS_BUCKET_SUFFIX` / `TF_VAR_ALERT_EMAIL` | infrastructure.yml |

### 4. First run
Push to `main` (or trigger `infrastructure.yml` manually with `apply`) to
provision the VPC/EKS/RDS/etc, then push to `main` under `app/**` or `k8s/**`
to build images and deploy. `infrastructure.yml` also installs the AWS Load
Balancer Controller via Helm and waits for it to be ready before `ci-cd.yml`'s
first Ingress apply.

### 5. Load the schema
Connect to the RDS endpoint (from `terraform output rds_endpoint`, password
from the Secrets Manager ARN in `terraform output rds_master_user_secret_arn`)
and run `app/database/schema.sql` once.

### 6. Find the app
```bash
kubectl get ingress -n support-desk
```
The ALB's DNS name serves the frontend at `/` and the three APIs at
`/auth`, `/tickets`, `/assign`.

## Notes on Kubernetes manifest placeholders

`k8s/serviceaccount.yaml`, the five `*-deployment.yaml` files, and
`k8s/ingress.yaml` contain `<ACCOUNT_ID>` / `<ALB_SECURITY_GROUP_ID>`
placeholders. Fill these in from `terraform output` once, or template them
in `ci-cd.yml` before `kubectl apply` — the reference project this was based
on took the same manual-fill approach for a portfolio-scale deployment.
