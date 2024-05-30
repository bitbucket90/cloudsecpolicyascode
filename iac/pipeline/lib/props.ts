import * as cdk from 'aws-cdk-lib'
import * as iam from 'aws-cdk-lib/aws-iam'

import { TagProps } from '../lib/constructs/aws-tags' //BranchProps
import { SharedConfigs } from '../bin/constants'

export interface StackProperties extends cdk.StackProps {
    //targetEnvironment: string
    env: cdk.Environment
    pipeline: string
    buildspecPath: string
    atmId: string
    awsRegion: string
    targetEnvironment: string
    appName: string
    vpcName: string
    s3KmsAlias: string
    githubOrg?: string
    githubRepo: string
    pipelineName: string
    artifactBucket: string
    codebuildRoleName: string
    accountId: string
    gitBranch: string
    codeStarArn: string
    codebuildRoleArn:string
    resourceTags: TagProps
}


// const account_id = SharedConfigs.ACCOUNT_MAP[SharedConfigs.RESOURCE_TAGS['env-type'].toLowerCase()] as string
const account_id = SharedConfigs.ACCOUNT_MAP[SharedConfigs.TARGET_ENVIRONMENT.toLowerCase()] as string
const git_branch = SharedConfigs.BRANCH_MAP[SharedConfigs.TARGET_ENVIRONMENT.toLowerCase()] as string
const star_arn = SharedConfigs.STAR_MAP[SharedConfigs.TARGET_ENVIRONMENT.toLowerCase()] as string
const build_arn = `arn:aws:iam::${account_id}:role/${SharedConfigs.CODEBUILD_ROLE}`
const bucket_prefix = `${SharedConfigs.PIPELINE_NAME.toLowerCase()}-artifact` // Artifact Bucket Starts with

export const AppProps = {
    // accountAlias: SharedConfigs.AWS_ACCOUNT_ALIAS,
    atmId: SharedConfigs.RESOURCE_TAGS['usage-id'],
    targetEnvironment: SharedConfigs.TARGET_ENVIRONMENT,//RESOURCE_TAGS['env-type'],
    appName: SharedConfigs.APP_NAME,
    awsRegion: SharedConfigs.AWS_REGION,
    vpcName: SharedConfigs.VPC_NAME,
    s3KmsAlias: SharedConfigs.CG_S3_KMS_ALIAS,
    githubOrg: SharedConfigs.GITHUB_ORG,
    githubRepo: SharedConfigs.GITHUB_REPO,
    pipelineName: SharedConfigs.PIPELINE_NAME,
    artifactBucket: bucket_prefix,
    buildspecPath: SharedConfigs.BUILDSPEC_PATH,
    codebuildRoleName: SharedConfigs.CODEBUILD_ROLE,
    codebuildRoleArn: build_arn!,
    accountId: account_id!,
    gitBranch: git_branch!,
    codeStarArn: star_arn!,
    resourceTags: SharedConfigs.RESOURCE_TAGS
}