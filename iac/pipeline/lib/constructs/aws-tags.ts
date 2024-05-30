import * as cdk from 'aws-cdk-lib'
import { Construct } from 'constructs'

export interface TagProps {
    // Resource Tagging Standards: [https://confluence.capgroup.com/display/HCEA/Resource+Tagging+standards]
    [key: string]: string | undefined
    "usage-id": string      // <ATM_ID>|<service_name>|network|storage
    "cost-center": string   // 6-digit [https://confluence.capgroup.com/display/FINOP/Valid+ITG+cost+centers]
    "ppmc-id": string       // 5-digit PPMC|10-alphanum ITBM ("PRJ00#####")
    "toc": string           // ("ETOC")
    "exp-date": string      // ("99-00-9999")
    "env-type": string      // ("dev"|"tst"|"prd")
    "sd-period": string     // ("na"|"us-office-hours"|"us-batch-hours")
    "backup"?: string       // storage resources ("standard"|"not-required-"...)
}

export interface BranchProps {
    [key: string]: string | undefined     
    "dev": string  
    "qa": string
    "prod": string
}

// TODO: tag custom resources (https://github.com/aws/aws-cdk/issues/13851)

export abstract class AwsTag {
    public static add(scope: Construct, tags: TagProps) {
        for (const key in tags) {
            cdk.Tags.of(scope).add(key, tags[key]!);
        }
    }
}