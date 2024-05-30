#---------------------------------------------------------------------------
# Create Terraform Policies | Supports both OPA & Sentinel  
#---------------------------------------------------------------------------


module "policies" {
    source                 = "./modules/policies"
    for_each               = { for k, v in var.policy_list: k => v }
    organization           = each.value.organization
    policy_set_name        = each.value.policy_set_name
    policy_set_description = each.value.policy_set_description
    policy_engine          = each.value.policy_engine
    workspace_ids          = each.value.workspace_ids
    # is_global              = try(each.value.is_global, true)
    # workspace_exclusions   = try(each.value.workspace_exclusions, [])
    # workspace_inclusions   = try(each.value.workspace_inclusions, [])
    policy_name            = each.value.policy_name
    policy_description     = each.value.policy_description
    enforcement_mode       = each.value.enforcement_mode
    policy_code            = each.value.policy_code
    opa_query              = try(each.value.opa_query, "")
}