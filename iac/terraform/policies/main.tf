#---------------------------------------------------------------------------
# Create Terraform Policies | Supports both OPA & Sentinel  
#---------------------------------------------------------------------------


module "policies" {
    source                 = "./modules/policies"
    for_each               = toset( var.policy_keys )#{ for k, v in var.policy_list: k => v }
    organization           = var.policy_list[each.key].organization#each.value.organization
    policy_set_name        = var.policy_list[each.key].policy_set_name#each.value.policy_set_name
    policy_set_description = var.policy_list[each.key].policy_set_description#each.value.policy_set_description
    policy_engine          = var.policy_list[each.key].policy_engine#each.value.policy_engine
    workspace_ids          = var.policy_list[each.key].workspace_ids #each.value.workspace_ids
    policies               = var.policy_list[each.key].policies #each.value.policies
    policy_keys            = var.policy_list[each.key].policy_keys
}