#---------------------------------------------------------------------------
# Main Variables | Create Terraform Policies | Supports both OPA & Sentinel  
#---------------------------------------------------------------------------
variable "organization" { type = string }
variable "policy_set_name" {}
variable "policy_set_description" {}
variable "policy_engine" {}
variable "policy_name" {}
variable "policy_description" {}
variable "enforcement_mode" {}
variable "policy_code" {}
variable "workspace_ids" {}
variable "opa_query" {
    default = ""
}
# variable "workspace_exclusions" {
#     default = []
# }
# variable "workspace_inclusions" {
#     default = []
# }
# variable "is_global" {
#     default = true
# }