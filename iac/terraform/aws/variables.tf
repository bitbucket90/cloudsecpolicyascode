#--------------------------------------------
# Main Variables
#--------------------------------------------

variable "account_env" {
  type    = string
  default = "dev"
}

variable "account_region" {
  type    = string
  default = "us-east-1"
}

variable "account_region_prefix" {
  type    = string
  default = "e1"
}

variable "account_id" {
  type    = string
  default = ""
}

variable "bucket_name" {
  type    = string
}

variable "bucket_data_class" {
  type    = string
}

variable "bucket_data_type" {
  type    = string
}

variable "kms_key_s3" {
  type    = string
  default = ""
}

variable "tfe_env" {
  type    = string
  default = "dev"
}

variable "tags" {
  type = map
  default = {
    "usage-id"         = "AA00002871"
    "cost-center"      = "524079"
    "sec-profile"      = "normal"
    "exp-date"         = "99-00-9999"
    "sd-period"        = "na"
    "ppmc-id"          = 84253
    "cloud-dependency" = "cloudonly"
    "site"             = "aws"
    "toc"              = "ETOC"
  }
}