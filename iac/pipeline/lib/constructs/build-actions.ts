import { kebabCase } from 'lodash'

/**AWS Calls */
import * as cdk from 'aws-cdk-lib'
import * as ec2 from 'aws-cdk-lib/aws-ec2'
import * as iam from 'aws-cdk-lib/aws-iam'
import * as kms from 'aws-cdk-lib/aws-kms'
import * as codebuild from 'aws-cdk-lib/aws-codebuild'
import * as codepipeline from 'aws-cdk-lib/aws-codepipeline'
import * as actions from 'aws-cdk-lib/aws-codepipeline-actions'
import { Construct } from 'constructs'

//import { KmsKey } from '@banzai/cg-kms-key'

export interface CodeBuildProps {
    vpcName?: string 
    appName: string
    bucketName?: string
    buildspecPath?: string
    targetEnvironment?: string
    acctAlias?: string
    accountId?: string
    buildActionName?: string
    kmsKeyAlias?: string
    runOrder?: number
    // buildRole?: iam.Role
    pipelineRole: iam.IRole
    codebuildRoleArn:string
    inputArtifacts?: codepipeline.Artifact
    outputArtifacts?: codepipeline.Artifact[]
}

const PropDefaults = {
    vpcName: 'vpc-1',
    buildspecPath: 'iac/pipeline/build/buildspec.yml',
    runOrder: 1,
    buildActionName: "BuildAction"
}

export class CodeBuild extends Construct {
    public BuildAction: codepipeline.IAction

    constructor(scope: Construct, id: string, props: CodeBuildProps) {
        super(scope, id)

        props = { ...PropDefaults, ...props }

        /**Retrieve StandardPipeline Role Required By Codebuild */
        const codebuild_role = iam.Role.fromRoleArn(this, 'BuildRole', props.codebuildRoleArn, {
            mutable: false
        })

        /**Retrieve VPC details -> IVPC */
        const accountVpc = ec2.Vpc.fromLookup(this, 'vpc', {
            vpcName: props.vpcName,
        })

        /**Get Subnets for VPC */
        const subPrivate1 = ec2.Subnet.fromSubnetId(this, 'subprivate1', "subnet-058f034d4a1cf0284")
        const subPrivate2 = ec2.Subnet.fromSubnetId(this, 'subprivate2', "subnet-092")

        const codeBuildSecurityGroup = new ec2.SecurityGroup(
            this,
            id + "BuildSg",
            {
                vpc: accountVpc,
                description: `${id} Pipeline CodeBuild Security Group`,
                securityGroupName: `${props.appName}CodebuildSecurityGroup`,
                allowAllOutbound: false
            }
        )

        /**Ingress Rule for Github WebHook */
        codeBuildSecurityGroup.addIngressRule(
            ec2.Peer.ipv4(accountVpc.vpcCidrBlock),
            ec2.Port.tcpRange(443, 443)
        )
        /**Egree Rule to enforce external traffic over https. Default is allow all egress traffic */
        codeBuildSecurityGroup.addEgressRule(
            //ec2.Peer.ipv4(accountVpc.vpcCidrBlock),
            ec2.Peer.anyIpv4(),
            ec2.Port.tcpRange(443, 443)
        )

        const buildProject = new codebuild.PipelineProject(
            this,
            id + "BuildProject",
            {
                buildSpec: codebuild.BuildSpec.fromSourceFilename(
                    props.buildspecPath!//'iac/pipeline/build/buildspec.yml'
                ),
                environment: {
                    buildImage: codebuild.LinuxBuildImage.STANDARD_7_0,
                    privileged: true,
                },
                projectName:`${props.appName}Build`,
                securityGroups: [codeBuildSecurityGroup],
                vpc: accountVpc,
                subnetSelection:{subnets:[subPrivate1,subPrivate2]},//["subnet-058f034d4a1cf0284"],
                encryptionKey: kms.Alias.fromAliasName(this, 'kmsKey', props.kmsKeyAlias!),
                role: codebuild_role //props.buildRole
            }
        )

        this.BuildAction = new actions.CodeBuildAction({
            actionName: props.buildActionName!,
            role: props.pipelineRole,
            project: buildProject,
            variablesNamespace: 'Build',
            input: props.inputArtifacts!,
            outputs: props.outputArtifacts,
            runOrder: props.runOrder,
            environmentVariables: {
                SOTERIA_ENV: {
                    value: props.acctAlias
                },
                BUCKET_NAME: {
                    value: props.bucketName
                },
                ACCOUNT_ID: {
                    value: props.accountId
                },
                TARGET_ENV: {
                    value: props.targetEnvironment
                }
            }
        })
    }
    

}