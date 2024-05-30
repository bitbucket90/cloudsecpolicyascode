provider "aws" {
  region  = var.account_region
  # assume_role {
  #   role_arn = var.role_mapping
  # }
}

provider "aws" {
  region  = "us-west-2"
  alias = "secondary_provider"
  # assume_role {
  #   role_arn = var.role_mapping
  # }
}