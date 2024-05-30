#--------------------------------------------
# S3 Module Variables
#--------------------------------------------

variable "account_env" {
  type    = string
  default = "dev"
}

variable "bucket_name" {
  type    = string
}

variable "kms_key_arn" {
  type    = string
}

variable "version_bucket" {
  type = bool 
  default = false
}

variable "vpc_id" {
  type    = string
}

variable "data_class" {
  type    = string
  default = "none"
}

variable "data_type" {
  type    = string
  default = "none"
}

variable "tags" {
    type = map 
}