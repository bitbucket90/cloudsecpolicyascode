import * as cdk from 'aws-cdk-lib'
import { Construct } from 'constructs'

import { StackProperties } from './props'
import { CodePipeline } from './constructs/pipeline'
// import { PipelineRoles } from './constructs/pipeline-roles'
// export { PipelineRoles }

export class TfePipelineIacStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props: StackProperties) {
        super(scope, id, props)

        /**Title Case Environment */
        // const env = props.targetEnvironment.split(" ").map((l: string) => l[0].toUpperCase() + l.substr(1)).join(" ") //slice

        /**Create Pipeline Role and Build Role */
        // const pipelineRole  = new PipelineRoles(this, `${env}`, {
        //     artifactBucket: props.artifactBucket,
        //     appName: props.appName,
        //     codeStarArn: props.codeStarArn
        // })

        /**Deploy Pipeline For Develop Branch */
        new CodePipeline(this, id, {
            // env: env,
            // pipelineRole: pipelineRole.role,
            // buildRole: pipelineRole.buildRole,
            ...props
        }).pipeline
    }
}