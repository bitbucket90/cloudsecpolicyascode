package terraform.policies.storage_tag

import input.plan as plan

metadata := {
    "policy": "aws.tags.storage",
    "description": "Storage Services Must Include Tag 'data-type' and 'data-classification'",
    "policy_definition": "",
    "severity": "medium",
    "resourceTypes": ["aws_s3_bucket","aws_efs_file_system","aws_db_instance"],
    "requiredTags": ["data-classification","data_type"],
    "resourceType":""
}

deny[msg] {
    resource := plan.resource_changes[_]
    resource.type == "aws_s3_bucket" #metadata["resourceTypes"][_]#storage_resource_types[_]
    required_tags := {"data-classification", "data-type"}
    provided_tags := {tag | resource.change.after.tags[tag]}
    missing_tags := required_tags - provided_tags
    count(missing_tags) > 0
    msg := {
       "status":"Failed",
       "resourceAddress": resource.address,
       "policy": metadata.policy,
       "description": metadata.description,
       "severity": metadata.severity,
       "remediation": metadata.description
    }
}