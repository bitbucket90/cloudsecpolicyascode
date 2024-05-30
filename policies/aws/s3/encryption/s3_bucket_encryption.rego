package aws.s3.encryption  

import input.plan as tfplan 

metadata := {
    "policy": "aws.s3.encryption",
    "description": "Ensure S3 is encrypted with CMK",
    "policy_definition": "",
    "severity": "medium",
    "resourceTypes": ["aws_s3_bucket"],
    "changeActions": ["create","update","no-op"],
    "allowed_sse_algorithms": ["aws:kms"] 
}

# Store S3 Buckets being created 
get_resources[resource] {
    resource := tfplan.resource_changes[_]
    resource.type = metadata["resourceTypes"][_]
    resource.change.actions[_] = metadata["changeActions"][_]
}

array_contains(arr, elem) {
    arr[_] = elem
}

# Deny Needs to Return True to Fail 
deny[reason] {
    resource := get_resources[_]
    # count(resource.change.after.server_side_encryption_configuration) == 0
    encryption_conf := resource.change.after.server_side_encryption_configuration[_]
    encryption_rule := encryption_conf.rule[_].apply_server_side_encryption_by_default[_]
    not array_contains(metadata["allowed_sse_algorithms"], encryption_rule["sse_algorithm"])
    reason := {
        "status":"Failed",
        "resourceAddress": resource.address,
        "resourceName": resource.change.after.bucket,
        "policy": metadata.policy,
        "description": metadata.description,
        "severity": metadata.severity,
        "remediation_documentation": "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_server_side_encryption_configuration",
        "remediation": "Create New TF Resource 'aws_s3_bucket_server_side_encryption_configuration'. In rule object 'kms_master_key_id' equals your account S3 CMK ARN and 'sse_algorithm' equals 'aws:kms'",
        "meta":encryption_rule["sse_algorithm"]
    }
}