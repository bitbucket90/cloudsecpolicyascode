import * as cdk from 'aws-cdk-lib'
import * as s3 from 'aws-cdk-lib/aws-s3'
import * as kms from 'aws-cdk-lib/aws-kms'
import { kebabCase } from 'lodash'
import { Construct } from 'constructs'

export interface S3Props {
    bucketName: string
    s3KmsAlias?: string
    accountAlias?: string
    expiration?: number
    deleteOnDestroy?: boolean
    noKebabCaseInBucketName?: boolean
    createBucketName?: boolean
    bucketLogPrefix?: string
    region?: string
    accountId?: string
    regionCode?: string
    kmsKeyAlias?: string
}

const defaultProps = {
    s3KmsAlias: 's3/0/kek',
    expiration: 30,
    deleteOnDestroy: false,
    noKebabCaseInBucketName: false,
    createBucketName: true,
    bucketLogPrefix: 'bucketLogPrefix'
}

/**
 * A generic CG-compliant S3 bucket construct that could be used in place of a direct AWS S3 `Bucket`
 */
export class S3Bucket extends Construct {
    public readonly bucket: s3.Bucket

    constructor(scope: Construct, id: string, props: S3Props) {
        super(scope, id)
        props = { ...defaultProps, ...props }

        let bucketName = props.bucketName
        let accessLogPrefix = props.bucketLogPrefix

        if (props.createBucketName){
            let bucketName = `${kebabCase(props.bucketName)}-${props.accountId}-${props.regionCode}`
            let accessLogPrefix = `${kebabCase(props.bucketName)}`
    
            if (props.noKebabCaseInBucketName) {
                bucketName = `${props.bucketName.toLowerCase()}-${props.accountId}-${props.regionCode}`
                accessLogPrefix = `${props.bucketName.toLowerCase()}`
            }
        }

        // const accessLogBucket = s3.Bucket.fromBucketName(this, 's3AccessLogBucket', `${props.accountId}-s3-access-logs-${props.regionCode}`)

        this.bucket = new s3.Bucket(this, id, {
            bucketName: bucketName,
            blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
            encryption: s3.BucketEncryption.KMS,
            encryptionKey: kms.Alias.fromAliasName(this, 'kmsKey', props.kmsKeyAlias!),
            serverAccessLogsBucket: s3.Bucket.fromBucketName(this, 's3AccessLogBucket', `${props.accountId}-s3-access-logs-${props.regionCode}`),
            serverAccessLogsPrefix: accessLogPrefix,
            versioned: true,
            lifecycleRules: [{ noncurrentVersionExpiration: cdk.Duration.days(props.expiration!) }],
            removalPolicy: (props.deleteOnDestroy ? cdk.RemovalPolicy.DESTROY : cdk.RemovalPolicy.RETAIN),
            // TODO: PermissionBoundary for auto-added role (https://github.com/aws/aws-cdk/issues/16459)
            // autoDeleteObjects: props.deleteOnDestroy
        })

        cdk.Tags.of(this.bucket).add('backup', 'not-required-temporary-s3');
    }
}