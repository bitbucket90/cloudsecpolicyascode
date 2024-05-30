package aws.apigateway.private_endpoints

import rego.v1

# API Gateway resource should not be publicly accessible

# Runbook link
# https://github.com/cg-open-itg/aws_runbooks/blog/master/efs/Runbook.md

# Terraform policy resource link
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_rest_api

# AWS link to policy definition/explaination
# https://aws.amazon.com/api-gateway/

metadata := {
    "policy": "aws.apigateway.private_endpoints",
    "description": "API Gateway resource should not be publicly accessible",
    "policy_definition": "https://github.com/cg-open-itg/CloudSecPolicyAsCode/blog/master/policy/aws/apigateway/private_endpoints.rego",
    "severity": "high",
    "resourceTypes": ["aws_api_gateway_rest_api"]
}

# ----------------------------------------------------------------------------------------------
# Functions block
# ----------------------------------------------------------------------------------------------

allowed_endpoint_configuration_types := "PRIVATE"

is_in_scope(resource) if {
    resource.mode == "managed"
	data.utils.is_create_or_update(resource.change.actions)
    resource.type == "aws_api_gateway_rest_api"
}

# ----------------------------------------------------------------------------------------------
# Deny block
# ----------------------------------------------------------------------------------------------

#
# rule 1: ensure endpoint configuration is specified
#
violations contains reason if {
    resource := input.plan.resource_changes[_]
    is_in_scope(resource)
    not resource.change.after.endpoint_configuration
    message := "AWS-APIGATEWAY-PRIVATE_ENDPOINTS: API Gateway resource '%s' must not be publicly accessible. Set endpoint_configuration_types as PRIVATE"
    reason := sprintf(message, [resource.address])
}

#
# rule 2: ensure endpoints are of type "PRIVATE"
#
violations contains reason if {
    resource := input.plan.resource_changes[_]
    is_in_scope(resource)
    endpoint_configuration := resource.change.after.endpoint_configuration[_]
    not allowed_endpoint_configuration_types in endpoint_configuration.types
    message := "AWS-APIGATEWAY-PRIVATE_ENDPOINTS: API Gateway resource '%s' must not be publicly accessible. Set endpoint_configuration.types as PRIVATE"
    reason := sprintf(message, [resource.address])
}

#
# rule 3: ensure endpoint leverages VPC endpoints
#
violations contains reason if {
    resource := input.plan.resource_changes[_]
    is_in_scope(resource)
    config_resource := data.utils.find_configuration_resource(resource, input.plan)
    not config_resource.expressions.endpoint_configuration[0].vpc_endpoint_ids
    message := "AWS-APIGATEWAY-PRIVATE_ENDPOINTS: API Gateway resource '%s' must be accessed through VPC endpoints. Set the endpoint_configuration.vpc_endpoint_ids attribute"
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
