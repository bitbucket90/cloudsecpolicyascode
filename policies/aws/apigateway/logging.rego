package aws.apigateway.logging

import rego.v1

# Restrict API deployment if logging is not enabled

# Runbook link
# https://github.com/cg-open-itg/aws_runbooks/blog/master/docs/runbooks/efs/Runbook.md

# Terraform policy resource link
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_method_settings
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_stage

# AWS link to policy definition/explaination
# https://aws.amazon.com/api-gateway/

metadata := {
    "policy": "aws.apigateway.logging",
    "description": "Restrict API deployment if logging is not enabled",
    "policy_definition": "https://github.com/cg-open-itg/CloudSecPolicyAsCode/blog/master/policy/aws/apigateway/logging.rego",
    "severity": "medium",
    "resourceTypes": ["aws_api_gateway_method_settings", "aws_api_gateway_stage"]
}

# ----------------------------------------------------------------------------------------------
# Functions block
# ----------------------------------------------------------------------------------------------

not_allowed_logging_level := "OFF"

contains_terraform_resource(array, value) if {
	array[_].type == value
}

is_logging_level_present(settings) if {
    logging_level := settings.logging_level
}

is_logging_level_allowed(value) if {
	value != not_allowed_logging_level
}

is_in_scope(resource, type) if {
	resource.mode == "managed"
	data.utils.is_create_or_update(resource.change.actions)
	resource.type == type
}

# ----------------------------------------------------------------------------------------------
# Deny block
# ----------------------------------------------------------------------------------------------

#
# rule 1: All API Gateway stages must have logging set to either INFO or ERROR
#
violations contains reason if {
    resource := input.plan.resource_changes[_]
    is_in_scope(resource, "aws_api_gateway_stage")
    not contains_terraform_resource(input.plan.resource_changes,"aws_api_gateway_method_settings")
    message := "AWS-APIGATEWAY-LOGGING: If aws_api_gateway_stage is created then aws_api_gateway_method_settings must be used with logging_level set to either INFO or ERROR '%s'"
    reason := sprintf(message, [resource.address])
}

#
# rule 2: method settings should never have log level set to 'OFF'
#
violations contains reason if {
    resource := input.plan.resource_changes[_]
    is_in_scope(resource, "aws_api_gateway_method_settings")
    settings := resource.change.after.settings[_]
    is_logging_level_present(settings)
    logging_level := settings.logging_level
    not is_logging_level_allowed(logging_level)
    message := "AWS-APIGATEWAY-LOGGING: logging_level under aws_api_gateway_method_settings should not be OFF '%s'"
    reason := sprintf(message, [resource.address])
}

#
# rule 3: Ensure that logging level is defined in method settings
#
violations contains reason if {
    resource := input.plan.resource_changes[_]
    is_in_scope(resource, "aws_api_gateway_method_settings")
    settings := resource.change.after.settings[_]
    not is_logging_level_present(settings)
    message := "AWS-APIGATEWAY-LOGGING:logging_level is not defined in aws_api_gateway_method_settings. Set logging_level as INFO or ERROR '%s'"
    reason := sprintf(message, [resource.address])
}

deny := [ msg |
    count(violations) != 0
    msg := {
        "decision": "fail",
        "violations": violations,
        "metadata": metadata,
    }
]
