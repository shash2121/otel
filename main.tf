module "vpc" {
  source           = "./modules/vpc"
  vpc_cidr         = var.vpc_cidr
  environment_name = var.environment_name
  aws_region       = var.region
  subnet_newbits   = var.subnet_newbits
  cluster_name     = var.cluster_name
  tags             = local.common_tags
}

module "eks" {
  source                    = "./modules/eks"
  cluster_name              = var.cluster_name
  cluster_version           = var.cluster_version
  node_group_name           = var.node_group_name
  node_group_instance_types = var.node_group_instance_types
  node_group_desired_size   = var.node_group_desired_size
  node_group_min_size       = var.node_group_min_size
  node_group_max_size       = var.node_group_max_size
  vpc_id                    = module.vpc.vpc_id
  subnet_ids                = module.vpc.public_subnet_ids
  aws_region                = var.region
  deploy_observability      = var.deploy_observability
  tags                      = local.common_tags
}
