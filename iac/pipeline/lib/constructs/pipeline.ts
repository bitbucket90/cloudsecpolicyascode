/**AWS Constructs */
import * as cdk from 'aws-cdk-lib'
import * as iam from 'aws-cdk-lib/aws-iam'
// import * as kms from 'aws-cdk-lib/aws-kms'
import * as codepipeline from 'aws-cdk-lib/aws-codepipeline'
import * as actions from 'aws-cdk-lib/aws-codepipeline-actions'
import { Construct } from 'constructs'

/**Soteria Constructs */
import { AspectsPermissionsBoundary } from './boundary-roles'
import { CodeBuild } from './build-actions'
import { S3Bucket } from './artifact-bucket'
import { PipelineRoles } from './pipeline-roles'
export { PipelineRoles }

export interface CodePipelineProps {
    // env: string
    atmId?: string
    appName: string
    githubOrg?: string
    githubRepo: string
    gitBranch: string
    buildspecPath?: string
    targetEnvironment?: string
    buildArtifact?: string
    accountId?: string
    region?: string
    regionCode?: string
    s3KmsAlias?: string
    kmsKeyAlias?: string
    bucketName?: string 
    acctAlias?: string
    vpcName?: string
    // buildRole?: iam.Role
    // pipelineRole?: iam.Role
    nameAlias?: string
    tfeEnv?: string
    pipelineName: string
    artifactBucket: string
    codeStarArn: string
    codebuildRoleArn: string
}

export class CodePipeline extends Construct {
    public readonly pipeline: codepipeline.Pipeline

    constructor(scope: Construct, id: string, props: CodePipelineProps) {
        super(scope, id)
        
        /**Base Params */
        const BaseDefaults = {
            titleEnv: props.targetEnvironment!.split(" ").map((l: string) => l[0].toUpperCase() + l.substr(1)).join(" "),
            regionCode: "",
            kmsKeyAlias:"",
            bucketName:"",
            bucketLogPrefix:"",
            codestarArn: "",
            tfeDirectory: 'iac/terraform',
            buildArtifact: 'buildArtifact',
            region: cdk.Stack.of(this).region,
            accountId: cdk.Stack.of(this).account,
            buildspecPath: props.buildspecPath,
            githubBranch: props.gitBranch,
            nameAlias: props.targetEnvironment == "qa" ? "aws-soteria" : "soteria",
            tfeEnv: props.targetEnvironment == "prod" ? "prd" : props.targetEnvironment,
            acctAlias: props.targetEnvironment == "qa" ? "tst" : props.targetEnvironment,
            pipelineName: `${props.pipelineName}-${props.targetEnvironment?.split(" ").map((l: string) => l[0].toUpperCase() + l.substr(1)).join(" ")}`
        }

        /**Update Keys */
        BaseDefaults.regionCode = BaseDefaults.region.substr(3, 1) + BaseDefaults.region.substr(8, 1)
        BaseDefaults.kmsKeyAlias = `alias/${BaseDefaults.nameAlias}-${BaseDefaults.acctAlias}/useast1/${props.s3KmsAlias}`//`${BaseDefaults.nameAlias}-${BaseDefaults.acctAlias}/useast1/${props.s3KmsAlias}`
        BaseDefaults.bucketName = `${props.artifactBucket}-${props.targetEnvironment}-${BaseDefaults.regionCode}`
        BaseDefaults.codestarArn = `arn:aws:codestar-connections:${BaseDefaults.region}:${BaseDefaults.accountId}:connection/${props.codeStarArn}`

        /**Merge BaseDefaults with properities */
        props = { ...BaseDefaults, ...props }
        
        /**Initialize new Codepipeline Build Artifact */
        const gitSourceArtifact = new codepipeline.Artifact('gitSourceArtifact')
        const buildArtifact = new codepipeline.Artifact(props.buildArtifact)

        /**Create Pipeline Role and Build Role */
        const pipelineRole  = new PipelineRoles(this, 'PipelineRole', {
            roleName: `${props.appName}PipelineRole${BaseDefaults.titleEnv}`,
            artifactBucket: BaseDefaults.bucketName,
            codeStarArn: BaseDefaults.codestarArn
        }).role

        /**Create Pipeline Artifact bucket */
        const s3Bucket = new S3Bucket(this, id + "Artifact", {
            bucketName: BaseDefaults.bucketName,
            createBucketName: false,
            deleteOnDestroy: !/^pro?d/i.test(props.targetEnvironment!),
            ...props
        })

        /**Create Codestar Connection Source Action */
        const sourceAction = new actions.CodeStarConnectionsSourceAction({
            actionName: 'source',
            owner: props.githubOrg!,
            repo: props.githubRepo,
            branch: BaseDefaults.githubBranch,
            triggerOnPush: true,
            output: gitSourceArtifact,
            connectionArn: BaseDefaults.codestarArn,
            variablesNamespace: 'SourceVar',
            role: pipelineRole
        })

        /**Initiate Codebuild to package policies - Requires buildspecPath - comes from ParamStore*/
        const buildAction = new CodeBuild(this, "BuildAction", {
            buildActionName: "PackagePolicies",
            pipelineRole: pipelineRole,
            bucketName: props.bucketName,
            // buildRole: props.buildRole,
            buildspecPath: props.buildspecPath,
            inputArtifacts: gitSourceArtifact,
            outputArtifacts: [buildArtifact],
            ...props
        }).BuildAction


        /**Assign stages to Pipeline*/
        this.pipeline = new codepipeline.Pipeline(this, "Pipeline", {
            pipelineType: codepipeline.PipelineType.V2,
            pipelineName: id,
            artifactBucket: s3Bucket.bucket,
            role: pipelineRole,
            stages: [
                { stageName: "GitHub-Source", actions: [sourceAction] },
                { stageName: "Package-Policies", actions: [buildAction] },
            ]
        })

        cdk.Tags.of(this.pipeline).add('consumer_pipeline_type', 'iac-tfe');
        AspectsPermissionsBoundary.add(this.pipeline)

    }
    
}