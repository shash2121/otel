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
  db_secret_name            = var.secret_name
  db_identifier             = var.db_identifier
  pod_identity_sa_name      = var.pod_identity_sa_name
  tags                      = local.common_tags
}

resource "random_password" "db_password" {
  length  = 32
  special = false
}

module "secrets_manager" {
  source      = "./modules/secrets-manager"
  secret_name = var.secret_name
  description = "RDS credentials for OTel demo"
  secret_string = {
    DB_USERNAME = var.db_username
    DB_PASSWORD = random_password.db_password.result
    DB_HOST     = module.rds.db_instance_endpoint
    DB_PORT     = tostring(var.db_port)
    DB_NAME     = var.db_name
  }
  recovery_window_in_days = 0
  tags                    = local.common_tags
}

module "rds_sg" {
  source              = "./modules/security-group"
  security_group_name = "${var.environment_name}-rds-sg"
  description         = "Allow EKS to access RDS PostgreSQL"
  vpc_id              = module.vpc.vpc_id
  ingress_rules = {
    postgres = {
      description = "PostgreSQL from VPC"
      from_port   = var.db_port
      to_port     = var.db_port
      protocol    = "tcp"
      cidr_block  = var.vpc_cidr
    }
  }
  tags = local.common_tags
}

module "rds" {
  source                = "./modules/rds"
  db_identifier         = var.db_identifier
  allocated_storage     = var.db_allocated_storage
  engine                = "postgres"
  engine_version        = "16.3"
  instance_class        = var.db_instance_class
  db_name               = var.db_name
  username              = var.db_username
  password              = random_password.db_password.result
  port                  = var.db_port
  vpc_id                = module.vpc.vpc_id
  subnet_ids            = module.vpc.private_subnet_ids
  security_group_ids    = [module.rds_sg.security_group_id]
  skip_final_snapshot   = true
  publicly_accessible   = false
  backup_retention_period = 0
  tags                  = local.common_tags
}
