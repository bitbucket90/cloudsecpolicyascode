#!/usr/bin/env node
import 'source-map-support/register'
import * as cdk from 'aws-cdk-lib'

import { AppProps } from '../lib/props'
import { TfePipelineIacStack } from '../lib/stacks'
import { AspectsPermissionsBoundary } from '../lib/constructs/boundary-roles'
import { AwsTag } from '../lib/constructs/aws-tags'


const app = new cdk.App()
const env = AppProps.targetEnvironment
const pipeline = `${AppProps.pipelineName}-${env.split(" ").map((l: string) => l[0].toUpperCase() + l.substr(1)).join(" ")}`

/**Account to Deploy Into */
console.log(AppProps.accountId)

/** Create Pipeline Stack */
const stack = new TfePipelineIacStack(app, pipeline, {
    env: {
        account: AppProps.accountId,
        region: AppProps.awsRegion
    },
    pipeline: pipeline,
    ...AppProps
})


/**Add Permission Boundary to Stack */
AspectsPermissionsBoundary.add(stack)

/**Add Tags to stack*/
AwsTag.add(stack, AppProps.resourceTags)