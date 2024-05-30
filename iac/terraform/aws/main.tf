data "aws_vpc" "vpc" {
  filter {
    name   = "tag:Name"
    values = ["vpc1"]
  }
}

data "aws_subnets" "vpc_subnets" {
  filter {
    name   = "tag:Name"
    values = ["private-*"]
  }
}

#------------------------------------------------------------
# Create S3 Bucket to ingest tool findings 
#------------------------------------------------------------
module "create_bucket" {
  source         = "./modules/storage"
  account_env    = var.account_env
  bucket_name    = "${var.bucket_name}-${var.account_env}-${var.account_region_prefix}"
  data_class     = var.bucket_data_class
  data_type      = var.bucket_data_type
  kms_key_arn    = var.kms_key_s3
  version_bucket = true 
  vpc_id         = data.aws_vpc.vpc.id
  tags           = merge(var.tags,{"env-type":"${var.account_env}"})
}



