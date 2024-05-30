import * as cdk from 'aws-cdk-lib'
import * as iam from 'aws-cdk-lib/aws-iam'
import { Construct, IConstruct } from 'constructs'

export abstract class AspectsPermissionsBoundary {
    public static add(stack: Construct, boundaryName?: string) {
        cdk.Aspects.of(stack).add(new PermissionsBoundary(stack, boundaryName || 'AdminPermissionsBoundary'))
    }
}

export class PermissionsBoundary implements cdk.IAspect {
    private readonly permissionsBoundaryArn: string

    constructor(scope: Construct, boundaryName: string) {
        this.permissionsBoundaryArn = iam.ManagedPolicy.fromManagedPolicyName(
            scope, 'Boundary', boundaryName
        ).managedPolicyArn
    }

    public visit(node: IConstruct): void {
        if (node instanceof iam.Role) {
            const roleResource = node.node.findChild('Resource') as iam.CfnRole
            if (!node.permissionsBoundary) {
                cdk.Annotations.of(node).addInfo("Add required permissions boundary")
                roleResource.addPropertyOverride('PermissionsBoundary', this.permissionsBoundaryArn)
            }
        }
    }
}