package aws.apigateway.encryption

import rego.v1

# Enforce encryption if caching is enabled in REST API

# Runbook link
# https://github.com/cg-open-itg/aws_runbooks/blog/master/efs/Runbook.md

# Terraform policy resource link
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_method_settings
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_stage

# AWS link to policy definition/explaination
# https://aws.amazon.com/api-gateway/

metadata := {
    "policy": "aws.apigateway.encryption",
    "description": "Enforce encryption if caching is enabled in REST API",
    "policy_definition": "https://github.com/cg-open-itg/CloudSecPolicyAsCode/blog/master/policy/aws/apigateway/encryption.rego",
    "severity": "medium",
    "resourceTypes": ["aws_api_gateway_stage", "aws_api_gateway_method_settings"]
}

# ----------------------------------------------------------------------------------------------
# Functions block
# ----------------------------------------------------------------------------------------------

contains_terraform_resource(array, value) if {
	array[_].type = value
}

is_cache_cluster_enabled(resource) if {
    data.utils.is_create_or_update(resource.change.actions)
    resource.mode == "managed"
    resource.change.after.cache_cluster_enabled == true
}

is_cache_data_encrypted(resource) if {
	resource.mode == "managed"
	data.utils.is_create_or_update(resource.change.actions)
    method_settings := resource.change.after.settings[_]
    method_settings.cache_data_encrypted == true
}


# ----------------------------------------------------------------------------------------------
# Deny block
# ----------------------------------------------------------------------------------------------

violations contains reason if {
    resource := input.plan.resource_changes[_]
	[path1, api_gw_stage] := walk(resource)
	api_gw_stage.type == "aws_api_gateway_stage"
	is_cache_cluster_enabled(api_gw_stage)
    not contains_terraform_resource(input.plan.resource_changes, "aws_api_gateway_method_settings")
	message := "AWS-APIGATEWAY-ENCRYPTION: If cache_cluster_enabled is set to true, then cache_data_encrypted must also be set to true. Set this parameter using aws_api_gateway_method_settings resource. '%s'"
    reason := sprintf(message, [api_gw_stage.address])
}

violations contains reason if {
    resource := input.plan.resource_changes[_]
	[path1, api_gw_stage] := walk(resource)
	api_gw_stage.type == "aws_api_gateway_stage"
	is_cache_cluster_enabled(api_gw_stage)
    [path2, api_gw_method_settings] := walk(input.plan.resource_changes)
    contains_terraform_resource(input.plan.resource_changes,"aws_api_gateway_method_settings")
    api_gw_method_settings.type == "aws_api_gateway_method_settings"
    not is_cache_data_encrypted(api_gw_method_settings)
    message := "AWS-APIGATEWAY-ENCRYPTION: If cache_cluster_enabled is set to true then cache_data_encrypted must also be set to true. '%s'"
    reason := sprintf(message, [api_gw_stage.address])
}

deny := [ msg |
    count(violations) != 0
    msg := {
        "decision": "fail",
        "violations": violations,
        "metadata": metadata,
    }
]
