package aws.sns.no_public_access
import rego.v1

# Restrict traffic to topics within own AWS account

# Runbook link
# https://github.com/open-itg/aws_runbooks/blog/master/sqs/Runbook.md

# Terraform policy resource link
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sns_topic_policy

# AWS link to policy definition/explaination
# https://docs.aws.amazon.com/sns/latest/dg/security-iam.html#access-control

metadata := {
    "policy": "aws.sns.no_public_access",
    "description": "Restrict traffic to topics within own AWS account",
    "policy_definition": "https://github.com/cg-open-itg/CloudSecPolicyAsCode/blog/master/opa/policies/sns/aws-sns-m-1.rego",
    "severity": "high",
    "resourceTypes": ["aws_sns_topic", "aws_sns_topic_policy"]
}

# ----------------------------------------------------------------------------------------------
# Functions block
# ----------------------------------------------------------------------------------------------
topics := data.utils.get_resources_by_type("aws_sns_topic", input.plan.resource_changes)
topic_policies := data.utils.get_resources_by_type("aws_sns_topic_policy", input.plan.resource_changes)
root_topic_policies := data.utils.get_resources_by_type("aws_sns_topic_policy", input.plan.configuration.root_module.resources)

is_in_scope(resource) if {
	resource.mode == "managed"
	data.utils.is_resource_create_or_update(resource)
}

topic_has_inline_policy(topic, plan) if {
    # ensure the topic doesn't have an associated 'aws_sns_queue_policy' resource
    not topic_has_policy(topic, plan)

    topic.change.after.policy != ""
    topic.change.after.policy != null
}

topic_has_policy(topic, plan) if {
    # case 1 - topic defined in a module (or nested module)
    data.utils.has(topic, "module_address")
    config_topic_policy := data.utils.find_configuration_resources_by_type_and_module(
        "aws_sns_topic_policy",
        topic.module_address,
        input.plan
    )[_]
    topic_without_module_prefix := substring(
        topic.address,
        count(topic.module_address) + 1,
        count(topic.address)
    )
    topic_without_module_prefix in config_topic_policy.expressions.arn.references
} else if {
    # case 2 - topic defined in the root module
    not data.utils.has(topic, "module_address")
    config_topic_policy := data.utils.find_configuration_resources_by_type("aws_sns_topic_policy", plan)[_]
    topic.address in config_topic_policy.expressions.arn.references
} else := false if {
    true
}

has_valid_policy(policyString) := true if {
    policy := json.unmarshal(policyString)
    statements := policy.Statement
    count([statement |
        statement := statements[_]
        policy_has_account_condition_key(statement)
    ]) == count(statements)
}

policy_has_account_condition_key(statement) if {
    statement.Effect == "Allow"
    statement.Condition.StringEquals["aws:PrincipalAccount"]
} else if {
    statement.Effect == "Deny"
    statement.Condition.StringNotEquals["aws:PrincipalAccount"]
} else := false if {
	true
}

# ----------------------------------------------------------------------------------------------
# Deny block
# ----------------------------------------------------------------------------------------------

#
# rule 1: ensure all SNS topics have a resource policy attached.
#
violations contains reason if {
	topic := topics[_]
    is_in_scope(topic)
	not topic_has_inline_policy(topic, input.plan)
	not topic_has_policy(topic, input.plan)
	reason := sprintf("AWS-SNS-NO_PUBLIC_ACCESS: SNS resource '%v' does not have a resource policy attached.", [topic.address])
}

#
# rule 2: ensure inline policies are valid
#
violations contains reason if {
    topic := topics[_]
    is_in_scope(topic)
    topic_has_inline_policy(topic, input.plan)
    not has_valid_policy(topic.change.after.policy)
    reason := sprintf("AWS-SNS-NO_PUBLIC_ACCESS: SNS resource '%v' policy should restrict traffic to within own AWS account (use 'aws:PrincipalAccount' condition key).", [topic.address])
}

#
# rule 3: ensure all non-inline policies are valid
#
violations contains reason if {
    topic_policy := topic_policies[_]
    is_in_scope(topic_policy)
    not has_valid_policy(topic_policy.change.after.policy)
    reason := sprintf("AWS-SNS-NO_PUBLIC_ACCESS: SNS resource policy '%v' is invalid.", [topic_policy.address])
}

deny := [ msg |
    count(violations) != 0
    msg := {
        "decision": "fail",
        "violations": violations,
        "metadata": metadata,
    }
]
