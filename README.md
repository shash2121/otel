# OpenTelemetry on AWS EKS

End-to-end observability demo, Terraform provisions the infra, Helm deploys
the stack, k6 generates load, dashboards show everything.

## What It Provisions

| Layer | Components |
|-------|-----------|
| Infra (Terraform) | VPC, EKS, RDS PostgreSQL, Secrets Manager, EBS CSI, Secrets Store CSI, AWS LBC, Pod Identity |
| Observability (Helm) | OTel Collector, Jaeger, Loki, Prometheus + Alertmanager, Grafana |
| Sample app | Two-service Flask app (gateway + backend) with OTel SDK, auto-instrumented |
| Load testing | k6 scripts — browsing, surge, burst, full production pattern |


## File Structure

```
otel/
├── terraform.tf             # Terraform config
├── main.tf                  # VPC + EKS + RDS modules
├── modules/
│   ├── vpc/                 # VPC with public/private subnets
│   ├── eks/                 # EKS + LBC + CSI + Pod Identity
│   ├── rds/                 # PostgreSQL instance
│   ├── secrets-manager/     # RDS credentials
│   ├── security-group/      # RDS security group
│   └── aws-policies/        # LBC IAM policy
├── helm-values/             # Helm values for all charts
├── k8s/                     # App + ingress + dashboards manifests
├── otel-app/                # Sample app source
│   ├── service-a/           # API gateway
│   └── service-b/           # Backend + DB access
├── k6-load-generation/      # Load-test scripts
└── README.md                # This file
```
