output "cluster_id" {
  value       = aws_eks_cluster.cluster.id
  description = "EKS cluster ID"
}

output "cluster_endpoint" {
  value       = aws_eks_cluster.cluster.endpoint
  description = "EKS cluster endpoint"
}

output "cluster_certificate_authority_data" {
  value       = aws_eks_cluster.cluster.certificate_authority[0].data
  description = "Cluster CA data"
  sensitive   = true
}

output "cluster_name" {
  value       = aws_eks_cluster.cluster.name
  description = "EKS cluster name"
}

output "node_group_arn" {
  value       = aws_eks_node_group.node_group.arn
  description = "Node group ARN"
}
