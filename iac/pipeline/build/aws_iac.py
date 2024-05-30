import os 
import sys 
import json 
from textwrap import dedent

# Custom TFE Module
import tfe_deploy 

from logger import base 

# Custom Logger & Aws Helpers
from aws import build_helpers as helpers

class aws_resources(object):
    def __init__(self,payload):
        self.payload = payload

    # TODO: Lambda Packager & Required Variables

    def set_tfe_vars(self,file_name):
        tfe = dedent(f'''\
        account_env = "{self.payload['env']}"
        tfe_env = "{self.payload['tfe_env']}"
        account_region = "{self.payload['region']}"
        account_region_prefix = "{self.payload['region_prefix']}"
        account_id = "{self.payload['account_id']}"
        bucket_name = "{self.payload['s3']['bucket_name']}"
        bucket_data_class = "internal"
        bucket_data_type = "it-prevent-policies"
        kms_key_s3 = "{self.payload['kms']['s3']}"''')
        with open(file_name,"w") as fout:
            fout.write(tfe)
            fout.close()

    def tf_deployer(self):
        log = base.Log(name="TfeDeploy")
        tfe_env = self.payload["tfe_env"]
        # Get Workspace to Deploy to based on lifeceycle account 
        ws_id = self.payload["tfe"]["workspaces"][tfe_env]
        log.info(f"Terraform Workspace: {tfe_env} | {ws_id}")
        # Get Tf Var File Name
        tf_var_file = self.payload["tfe"]["var_file"]
        # Create TF Var File
        self.set_tfe_vars(file_name=tf_var_file)
        # Deploy to IAC To TF
        log.info(f"Terraform Workspace: {ws_id}")
        tfe_deploy.main_handler(
            workspace_id=ws_id,
            terraform_path="iac/terraform/aws",
            packaged_path="iac/tf_aws_code.tar.gz",
            variable_file=tf_var_file,
            # is_local=True,
            aws_config_file="/users/jsgl/.aws/credentials"
        )

def main_handler():
    log = base.Log(name="AwsIaC")
    main_dir = os.getcwd()
    env,tfe_env = helpers.iam().get_env()
    region = "us-east-1"
    reg_short = region.split("-")[1][0] + region.split("-")[-1]
    payload = {
        "env":env,
        "tfe_env":tfe_env,
        "region":region,
        "region_prefix":reg_short,
        "account_id":helpers.sts().get_acct_id(),
        "s3":{
            "bucket_name": f"opa-policies"
        },
        "kms":{
            "s3":helpers.kms().get_arn(sid="s3")
        },
        "tfe":{
            "var_file":f"aws-{env}.auto.tfvars",
            "workspaces":{
                "dev":"ws-XQp9EHDoBJGSA75K",
                "qa":"ws-56mjd6SvWSFWvntq",
                "prd":""
            }
        }
    }
    # Clsec-Prevent-Policy-Manager-Dev
    aws_resources(payload).tf_deployer()
    # tfe_deploy.main_handler(
    #     workspace_id=tfe_env_dict[tfe_env],
    #     terraform_path="iac/terraform_aws",
    #     packaged_path="iac/tf_aws_code.tar.gz",
    #     variable_file=tfe_var_file
    # )

if __name__ == "__main__":
    main_handler()
    #helpers.codestar().list_connections(item="connections",print_it=True)