output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "grafana_admin_password_cmd" {
  description = "Command to get Grafana admin password"
  value       = "kubectl get secret grafana -o jsonpath='{.data.admin-password}' | base64 -d"
}

output "port_forward_cmds" {
  description = "kubectl port-forward commands to access UIs"
  value = <<-EOT

    # Access Grafana:
    kubectl port-forward svc/grafana 3000:80

    # Access Jaeger UI:
    kubectl port-forward svc/jaeger-query 16686:16686

    # Access Loki (API for log queries):
    kubectl port-forward svc/loki 3100:3100

    # Access sample app Service A:
    kubectl port-forward svc/service-a 5001:5000

    # Access sample app Service B:
    kubectl port-forward svc/service-b 5002:5000
  EOT
}
