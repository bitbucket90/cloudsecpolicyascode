import os 
import sys
import json
import shutil
import tarfile
# import zipfile
import traceback

# Import Custom Classes 
from aws import build_helpers as helpers 
from tf_api import actions as tf_actions

class TfeActions(object):
    def __init__(self,payload):
        self.payload = payload
        self.log = helpers.Log(name="TfeActions") 

    def start(self,**kwargs):
        cloud = kwargs.get("cloud","aws")
        tfe_variables = kwargs.get("tfe_variables",{})
        is_run_successful = False 
        is_aws = True if cloud.lower() == "aws" else False
        if is_aws:
            creds = helpers.sts(self.payload).assume_role(role=self.payload["assume_role"])
        else:
            creds = kwargs.get("creds",{})
        if creds:
            tf_var_actions = tf_actions.variables(self.payload)
            is_successful = tf_var_actions.upload_variable(vars_dict=creds, is_sensitive=True ,is_aws=is_aws)
            if is_successful:
                self.log.info(f"Successfully updated config var")
                if tfe_variables:
                    is_successful = tf_var_actions.upload_variable(vars_dict=tfe_variables, is_sensitive=False)
                    if is_successful == False:
                        log.warning(f"Upload Regular TF Variables Failed")
                # Switch to working directory and Deploy 
                is_run_successful = self.tfe_builder()
            else:
                raise Exception(f"Failed to update {cloud.title()} Config Keys in Terraform | Cannot deploy")
        else:
            raise Exception(f"Failed to Assume Role | Cannot Deploy")
        # else:
        #     self.tfe_builder()
        return is_run_successful
    
    def tfe_builder(self):
        log = helpers.Log(name="TfeDeploy")
        # Get Terraform Meta 
        tfp = self.payload["tfe"]
        # Set terraform directory & confirm tfvars is included
        local_path = tfp["local_path"]
        #local_path = os.path.abspath("../../..")
        if local_path == "./":
            code_path = tfp["code_path"]
            zip_path = tfp["zip_path"]
        else:
            code_path = os.path.join(local_path, tfp["code_path"])
            zip_path = os.path.join(local_path, tfp["zip_path"])
        log.info(code_path)
        log.info(zip_path)
        org_dir = os.getcwd()
        tf_auto_vars = tfp["tf_auto_vars"]#f"{self.payload['env'].lower()}.auto.tfvars"
        # Move Tfvars file to terraform directory 
        if tf_auto_vars in os.listdir():
            # Remove any auto var file from path
            for tav in os.listdir(code_path):
                if os.path.isfile(os.path.join(code_path,tav)):
                    if tav.endswith(".tfvars"):
                        log.warning(f"Removing previous tfvar file | {tav}")
                        os.remove(os.path.join(code_path,tav))
                    else:
                        log.info(f"Not TFVar File | {tav}")
                else:
                    log.info(f"Not a File | {tav}")
            # Move latest auto tfvar file to terraform directory 
            shutil.copy(tf_auto_vars, os.path.join(code_path,tf_auto_vars))
        
        # Package TF Code | zip dir to tar.gz 
        with tarfile.open(zip_path, "w:gz") as fout:
            try:
                fout.add(code_path, arcname=os.sep)
            except Exception as e:
                log.error(f"Failed to Package TF Code | {traceback.format_exc()}")
                raise e

        # Initialize Workspace Object 
        tf_runs = tf_actions.runs(self.payload) 
        # Create File, upload, and run 
        is_run_successful = tf_runs.start(config={
            "upload_code":True,
            "zip_file":open(zip_path, 'rb').read(),
            "run_type":"apply",#Required 
            "run_message":"CLSEC TFE-API Run Trigger", 
            "finished_exit":True, # wait to exit until apply reaches termination stage: finished,canceled,unreachable,error: default False
            "seconds_per_check":5, # seconds to wait before checking status: default 20
            "return_success_status":tfp["return_success_status"]
        })
        # Delete Zip file 
        os.remove(zip_path)
        return is_run_successful
        

def main_handler(workspace_id,**kwargs):
    log = helpers.Log(name="TfeMain") 
    env = kwargs.get("env","")
    tfe_env = kwargs.get("tfe_env","")
    if len(env) == 0:
        env,tfe_env = helpers.iam().get_env()
    if len(tfe_env) == 0:
        tfe_env = env
    # ws-XQp9EHDoBJGSA75K
    account_id = kwargs.get("account_id",helpers.sts().get_acct_id())
    local_path = kwargs.get("local_path","../../..")
    terra_path = kwargs.get("terraform_path","iac/terraform")
    terra_zip_path = kwargs.get("packaged_path","iac/tf_code.tar.gz")
    tf_auto_vars = kwargs.get("variable_file",f"{env.lower()}.auto.tfvars")
    secret_name = kwargs.get("secret_name",f"terraform-{env}")
    secret_key = kwargs.get("secret_key","token")
    secret_variables = kwargs.get("secret_vars",kwargs.get("secret_variables",{}))
    tfe_variables = kwargs.get("regular_vars",kwargs.get("regular_variables",{}))
    cloud = kwargs.get("cloud","aws")
    return_success_status = kwargs.get("return_success_status",False)
    log.info(f"TerraformPath: {terra_path}")
    log.info(f"TerraformZipPath: {terra_zip_path}")
    log.info(f"TerraformVarFile: {tf_auto_vars}")
    # if len(creds) == 0:
    # if len(tfe_variables):
    #     for c in ["regular","normal"]:
    #         if len(tfe_variables.get(c,{})):
    #             tfe_variables = tfe_variables[c]
    #             break 

    # Update parameter store with list of clusters 
    payload = {
        "env":env,
        "tfe_env":tfe_env,
        "get_secret_name":{"tfe_creds": secret_name},
        "assume_role":"StandardPipelineRole",#f"arn:aws:iam::{account_id}:role/StandardPipelineRole",
        "account_id":account_id,
        "tfe":{
            "url":"https://tfe.cgftdev.com" if tfe_env.lower() == "ftdev" else "https://tfe.cguser.capgroup.com",
            "workspaces":{
                "ftdev":"",
                "dev":"",
                "qa":"",
                "prod":""
            },
            "local_path":local_path,
            "code_path":terra_path,
            "zip_path":terra_zip_path,
            "tf_auto_vars":tf_auto_vars,
            "return_success_status":return_success_status
        },
        "aws":{
            "config_file":kwargs.get("aws_config_file","")
        }
    }
    ws_env = "qa" if env.lower() == "tst" else env
    payload["tfe"]["workspaces"] = {ws_env:workspace_id}
    payload = helpers.secrets_manager(payload).get_secret()
    cont = False 
    if env in list(payload["tfe"]["workspaces"].keys()):
        payload["tfe"]["ws_id"] = payload["tfe"]["workspaces"][env]
        payload["tfe"]["api_url"] = payload["tfe"]["url"] + "/api/v2/" 
        payload["tfe"]["conn"] = payload["tfe_creds"][secret_key]
        del payload["tfe_creds"]["token"]
        ws_meta = tf_actions.workspaces(payload).verify_access()
        if ws_meta:
            payload["tfe"]["org_name"] = ws_meta["org_name"]
            payload["tfe"]["workspace_name"] = ws_meta["workspace_name"]
            cont = True
        else:
            raise Exception(f'WorkspaceAccessError | Invalid Workspace ID: {payload["tfe"]["ws_id"]}')
    else:
        raise Exception(f'Failed to find workspace Id for env {env} | EnvIdsFound: {list(payload["tfe"]["workspaces"].keys())}')
    if cont:
        payload["is_local"] = kwargs.get("is_local",False) 
        payload["debug_mode"] = kwargs.get("debug_mode",False)  
        is_run_successful = TfeActions(payload).start(cloud=cloud,creds=secret_variables,tfe_variables=tfe_variables)
        #if return_success_status:
        return is_run_successful
    else:
        log.error(f"Failed to find Workspace Id from Environment | Stopping Deployment")
        #if return_success_status:
        return False 
    

if __name__ == "__main__":
    main_handler()