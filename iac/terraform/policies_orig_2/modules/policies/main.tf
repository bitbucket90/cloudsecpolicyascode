#---------------------------------------------------------------------------
# Main Module | Create Terraform Policies | Supports both OPA & Sentinel  
#---------------------------------------------------------------------------

# locals {
#   # If workspace include list is not empty is global must be false 
#   is_global = false #length( var.workspace_inclusions ) > 0  ? false : true
# }

resource "tfe_policy" "custom_policy" {
  #---------------------------------
  # Required Arguments
  #---------------------------------
  for_each               = { for k, v in var.policies: k => v }
  name                   = each.value.policy_name
  policy                 = each.value.policy_code
  #---------------------------------
  # Required Arg for OPA Rules
  #---------------------------------
  query                  = each.value.opa_query
  #---------------------------------
  # Optional Arguments
  #---------------------------------
  description            = each.value.policy_description # Default: ""
  organization           = var.organization # Default: Must be in provider block
  kind                   = var.policy_engine # Default: Sentinel 
  enforce_mode           = each.value.enforcement_mode # Default: Advisory
}

resource "tfe_policy_set" "policy_set" {
  #---------------------------------
  # Required Arguments
  #---------------------------------
  name                = var.policy_set_name
  policy_ids          = values(tfe_policy.custom_policy)[*].id
  #---------------------------------
  # Optional Arguments
  #---------------------------------
  description         = var.policy_set_description# Default: ""
  organization        = var.organization # Default: Must be in provider block
  kind                = var.policy_engine # Default: Sentinel
  # global              = local.is_global #try(var.is_global, true) # Default: false 
  workspace_ids       = var.workspace_ids#each.value.workspace_ids

  #depends_on = [ tfe_policy.custom_policy ]
}

# resource "tfe_workspace_policy_set" "workspaces" {
#   count               = length(var.workspace_inclusions)
#   policy_set_id       = tfe_policy_set.policy_set.id 
#   workspace_id        = var.workspace_inclusions[count.index]

#   depends_on = [ tfe_policy_set.policy_set ]
# }

# resource "tfe_workspace_policy_set_exclusion" "policy_exceptions" {
#   count               = length(var.workspace_exclusions)
#   policy_set_id       = tfe_policy_set.policy_set.id 
#   workspace_id        = var.workspace_exclusions[count.index]

#   depends_on = [ tfe_policy_set.policy_set ]
# }