import { TagProps,BranchProps } from '../lib/constructs/aws-tags'

export abstract class SharedConfigs {
    /**AWS Variables */
    public static readonly VPC_NAME: string = "vpc1"
    public static readonly AWS_REGION: string = "us-east-1"
    public static readonly CG_S3_KMS_ALIAS: string = "s3/0/kek"

    /**Repo/Github Variables */
    public static readonly GITHUB_ORG: string = "cg-open-itg"
    public static readonly GITHUB_REPO: string = "CloudSecPolicyAsCode"
    public static readonly CODEBUILD_ROLE: string = "StandardPipelineRole"

    /**App Variables */
    public static readonly APP_NAME: string = "TfePreventPolicies"
    public static readonly PIPELINE_NAME: string = "Tfe-Prevent-Policies"
    public static readonly BUILDSPEC_PATH: string = "iac/pipeline/build/buildspec.yml"
    
    /**UPDATE the Environment Key - used to filter downstream values*/
    public static readonly TARGET_ENVIRONMENT: string = "dev" //"qa" or "prod" 
    
    public static readonly RESOURCE_TAGS: TagProps = {
        "usage-id": "AA00002871",
        "cost-center": "524079",
        "ppmc-id": "84253",
        "toc": "ETOC",
        "exp-date": "99-00-9999",
        "env-type": SharedConfigs.TARGET_ENVIRONMENT,
        "sd-period": "na"
    }
    /** TARGET_ENVIRONMENT value used as input to recieve the following variables*/
    public static readonly ACCOUNT_MAP: BranchProps = {
        "dev":"374601996262",
        "qa":"888486914708",
        "prod":"953351123406"
    }
    public static readonly BRANCH_MAP: BranchProps = {
        "dev":"develop",
        "qa":"test",
        "prod":"production"
    }
    public static readonly STAR_MAP: BranchProps = {
        "dev":"7446f84b-a460-4ee3-b0b0-1af2f1080cf3",
        "qa":"",
        "prod":""
    }
}