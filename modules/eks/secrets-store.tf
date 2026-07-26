resource "helm_release" "csi_secrets_store" {
  name       = "csi-secrets-store"
  repository = "https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts"
  chart      = "secrets-store-csi-driver"
  namespace  = "kube-system"

  set {
    name  = "syncSecret.enabled"
    value = "true"
  }
  set {
    name  = "enableSecretRotation"
    value = "true"
  }
  set {
    name  = "tokenRequests[0].audience"
    value = "pods.eks.amazonaws.com"
  }

  depends_on = [aws_eks_node_group.node_group]
}

resource "helm_release" "secrets_provider_aws" {
  name       = "secrets-provider-aws"
  repository = "https://aws.github.io/secrets-store-csi-driver-provider-aws"
  chart      = "secrets-store-csi-driver-provider-aws"
  namespace  = "kube-system"

  set {
    name  = "secrets-store-csi-driver.install"
    value = "false"
  }

  depends_on = [
    aws_eks_node_group.node_group,
    helm_release.csi_secrets_store,
  ]
}
