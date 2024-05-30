import * as cdk from 'aws-cdk-lib'
import * as iam from 'aws-cdk-lib/aws-iam'
import * as cdkConstants from 'cdk-constants'
import { Construct } from 'constructs'

export interface CodePipelineProps {
    roleName: string
    artifactBucket: string
    // appName: string 
    codeStarArn: string
}

export class PipelineRoles extends Construct {
    public readonly role: iam.IRole
    // public readonly buildRole: iam.Role

    constructor(scope: Construct, id: string, props: CodePipelineProps) {
        super(scope, id)

        const pipelinePolicies = new iam.PolicyDocument({
            statements: [
                new iam.PolicyStatement({
                    effect: iam.Effect.ALLOW,
                    actions: [
                        'sts:AssumeRole',
                    ],
                    resources: ['*'],
                }),
                new iam.PolicyStatement({
                    effect: iam.Effect.ALLOW,
                    actions: [
                        'codepipeline:*',
                        'cloudformation:*',
                        'codebuild:*',
                        'kms:Encrypt',
                        'kms:Decrypt',
                        'kms:DescribeKey',
                        'kms:GenerateDataKey',
                        'iam:PassRole',
                        'secretsmanager:DescribeSecret',
                        'secretsmanager:GetSecretValue',
                    ],
                    resources: ['*'],
                }),
                new iam.PolicyStatement({
                    effect: iam.Effect.ALLOW,
                    actions: [
                        'codestar-connections:UseConnection'
                    ],
                    resources: [props.codeStarArn],
                }),
                new iam.PolicyStatement({
                    effect: iam.Effect.ALLOW,
                    actions: ['sns:Publish'],
                    resources: ['*'],
                }),
                new iam.PolicyStatement({
                    effect: iam.Effect.ALLOW,
                    actions: ['s3:*'],
                    resources: [
                        `arn:aws:s3:::${props.artifactBucket}`,
                        `arn:aws:s3:::${props.artifactBucket}/*`
                    ],//deploy-azure-policies
                }),
            ],
        })

        /**PipelineRole */
        this.role = new iam.Role(this, props.roleName, {
            roleName: props.roleName,
            assumedBy: new iam.ServicePrincipal(cdkConstants.ServicePrincipals.CODE_PIPELINE),
            inlinePolicies: { pipelineIamPolicy: pipelinePolicies },
            permissionsBoundary: iam.ManagedPolicy.fromManagedPolicyArn(
                this, 
                'AdminBoundary', 
                `arn:aws:iam::${cdk.Stack.of(this).account}:policy/AdminPermissionsBoundary`
            )
        }).withoutPolicyUpdates()

    }
}