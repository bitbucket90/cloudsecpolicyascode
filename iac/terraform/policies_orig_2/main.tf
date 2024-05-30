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
    policies               = each.value.policies
}