package aws.efs.no_public_access
import rego.v1

# Restrict public access to EFS file systems

# Runbook link
# https://github.com/open-itg/aws_runbooks/blog/master/efs/Runbook.md

# Terraform policy resource link
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/efs_file_system
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/efs_file_system_policy

# AWS link to policy definition/explaination
# https://docs.aws.amazon.com/efs/latest/ug/NFS-access-control-efs.html
# https://docs.aws.amazon.com/efs/latest/ug/access-control-block-public-access.html#what-is-a-public-policy

metadata := {
    "policy": "aws.efs.no_public_access",
    "description": "Restrict public access to EFS file systems",
    "policy_definition": "https://github.com/cg-open-itg/CloudSecPolicyAsCode/blog/master/policy/efs/no_public_access.rego",
    "severity": "high",
    "resourceTypes": ["aws_efs_file_system", "aws_efs_file_system_policy"]
}

# ----------------------------------------------------------------------------------------------
# Functions block
# ----------------------------------------------------------------------------------------------
file_systems := data.utils.get_resources_by_type("aws_efs_file_system", input.plan.resource_changes)
file_system_policies := data.utils.get_resources_by_type("aws_efs_file_system_policy", input.plan.resource_changes)

is_in_scope(resource) if {
	resource.mode == "managed"
	data.utils.is_resource_create_or_update(resource)
}

# verify an associated policy exits
file_system_has_policy(file_system, plan) if {
    # case 1 - file system defined in a module (or nested module)
    config_file_system_policy := data.utils.find_configuration_resources_by_type_and_module(
        "aws_efs_file_system_policy",
        file_system.module_address,
        plan
    )[_]
    file_system_address_without_module_prefix := substring(
        file_system.address,
        count(file_system.module_address) + 1,
        count(file_system.address)
    )
    file_system_address_without_module_prefix in config_file_system_policy.expressions.file_system_id.references
} else if {
    # case 2 - file system defined in the root module
    config_file_system_policy := data.utils.find_configuration_resources_by_type("aws_efs_file_system_policy", plan)[_]
    file_system.address in config_file_system_policy.expressions.file_system_id.references
} else := false if {
    true
}

lookup_iam_policy(data_resource_address, file_system_policy) := data_policy if {
    # case 1 - data resource lives inside module (or nested module)
    data.utils.has(file_system_policy, "module_address")
    data_resource := data.utils.find_configuration_resource_by_address_and_module(data_resource_address, file_system_policy.module_address, input.plan)
    data_policy := data_resource[0].expressions.statement
} else := data_policy if {
    # case 2 - data resource live in root module
    data_resource := data.utils.get_resources_by_address(data_resource_address, input.plan.configuration.root_module.resources)
    data_resource != []
    data_policy := data_resource[0].expressions.statement
}

# looks up the data reference for the policy
find_data_reference(config_file_system_policy) := data_reference if {
    references := config_file_system_policy.expressions.policy.references
    reference := references[_]
    startswith(reference, "data.")
    not endswith(reference, ".json")
    data_reference := reference
} else := false if {
    true
}

# ensure each statement has proper condition key elasticfilesystem:AccessedViaMountTarget with a value of true
has_valid_policy(statements) := true if {
    count([statement |
        statement := statements[_]
        policy_has_condition_key(statement)
    ]) == count(statements)
}

policy_has_condition_key(statement) if {
    statement.effect["constant_value"] == "Allow"
    condition := statement.condition[_]
    condition.test["constant_value"] == "Bool"
    condition.variable["constant_value"] == "elasticfilesystem:AccessedViaMountTarget"
    condition.values["constant_value"] == ["true"]
} else if {
    statement.effect["constant_value"] == "Deny"
    condition := statement.condition[_]
    condition.test["constant_value"] == "Bool"
    condition.variable["constant_value"] == "elasticfilesystem:AccessedViaMountTarget"
    condition.values["constant_value"] == ["false"]
} else := false if {
	true
}

# ----------------------------------------------------------------------------------------------
# Deny block
# ----------------------------------------------------------------------------------------------

#
# rule 1: ensure all EFS file systems have a resource policy attached.
#
violations contains reason if {
	file_system := file_systems[_]
    is_in_scope(file_system)
	not file_system_has_policy(file_system, input.plan)
	reason := sprintf("AWS-EFS-NO_PUBLIC_ACCESS: EFS resource '%v' does not have a resource policy attached.", [file_system.address])
}

#
# rule 2: ensure that policies do not leverage jsonencode function
#
violations contains reason if {
    file_system_policy := file_system_policies[_]
    is_in_scope(file_system_policy)
    config_file_system_policy := data.utils.find_configuration_resource(file_system_policy, input.plan)
    not find_data_reference(config_file_system_policy)
    reason := sprintf("AWS-EFS-NO_PUBLIC_ACCESS: EFS resource policy '%v' is invalid. Policy should not leverage jsonencode function.", [file_system_policy.address])
}

#
# rule 3: ensure resource policies are valid
#
violations contains reason if {
    file_system_policy := file_system_policies[_]
    is_in_scope(file_system_policy)
    # lookup the efs policy in config
    config_file_system_policy := data.utils.find_configuration_resource(file_system_policy, input.plan)
    # find the data reference address for the policy
    root_policy_reference := find_data_reference(config_file_system_policy)
    # lookup data resource and extract iam policy
    iam_policy := lookup_iam_policy(root_policy_reference, file_system_policy)
    # validate policy
    not has_valid_policy(iam_policy)
    reason := sprintf("AWS-EFS-NO_PUBLIC_ACCESS: EFS resource policy '%v' is invalid.", [file_system_policy.address])
}

deny := [ msg |
    count(violations) != 0
    msg := {
        "decision": "fail",
        "violations": violations,
        "metadata": metadata,
    }
]
