# PreReqs
# Blocker 1: List All Orgs
# Blocker 2: Exc

# Step 1: Create Policy Set 
# Step 2: Add Policies to Policy Set 
# Step 3: Check for exceptions 
#   --> Identify resource type: org == organization || prj == project || ws == workspaces 
#   --> Separate branch for exceptions. Skip packaging triggers 

# Deletion Queue: If any marked for deletion --> Categorize with new column 
# After Policies process - next run delete queue 

# TODO: Updates. How to accurately track PolicySets. policies  
# Policy Set Scenarios
# - Issue: Unique ID, How to address updates
# - Issues: Exceptions
#       :: New Exception - Does Resource (WS or PRJ) Exist in this organization 
#       :: Deleted Exceptions - If Exception is Applied but no longer in "abc"
# Policy Scenarios
# - Policy Creates BUT Policy Update Failed 
# - Policy Updates - Name: Would need to reprocess 


import os 
import sys 
import json 
import uuid
import shutil
import hashlib 
import datetime
import traceback
#import pandas as pd 
from textwrap import dedent

# Custom Logger 
from logger import base 

# TFE Policy Actions  
from tf_api import actions

# Aws Helper Classes 
from aws import build_helpers

# Validate & Aggregate policy configs & deploy policies via TF deployer
import policy_configs,tfe_deploy

class tfe_policies(object):
    def __init__(self,payload):
        self.payload = payload
        self.delete_queue = [] 

    # Check if value in item list
    def resource_check(self,val,items):
        if len(items):
            item_found = False
            for i in items:
                if i.lower() == val.lower():
                    item_found = True
                    break 
            return item_found
        else:
            return True

    def policy_set(self,pset,prj_to_ws_mapping):#org_id,org_name,ws_id_list
        log = base.Log(name="PolicySet")
        log_exceptions = base.Log(name="PolicyExceptions")
        # Default continue processing to True 
        cont_processing = True 
        # Get Organization Name
        org_name = pset["organization"]
        # Get Organization ID 
        org_id = pset["organization_id"]
        # Get Workspace Id List
        ws_id_list = pset["workspace_ids"]
        # Policy Sets: Policy Set Name OR Policy Set Path
        policy_set_name = pset["policy_set_name"]
        # Set Hanlder for Include Object 
        include = pset["include"]
        # Set Handler for Exclude Object
        exceptions = pset["exceptions"]

        # --------------------------------------
        # Organization Check: Include & Exclude 
        # --------------------------------------
        # Get Include Orgs
        include_orgs = include.get("organization",[]) 
        if len(include_orgs):
            include_org = self.resource_check(val=org_id.lower(),items=include_orgs)
            if include_org == False:
                log.info(f"Not Including Org in Policy | Name: {policy_set_name} | Org: {org_name} | Id: {org_id} | OrgsToInlcude: {include_orgs}")
                cont_processing = False
        # Get Exclude Orgs
        exclude_orgs = exceptions.get("organization",[])
        if len(exclude_orgs):
            exclude_org = self.resource_check(val=org_id.lower(),items=exclude_orgs)
            if exclude_org:
                log_exceptions.info(f"Exception Found. Excluding Org from Policy | Name: {policy_set_name} | Org: {org_name} | Id: {org_id} | OrgsToExclude: {exclude_orgs}")
                cont_processing = False

        # --------------------------------------
        # Workspace Check: Include & Exclude 
        # --------------------------------------
        # Check for include ws 
        include_ws = include.get("workspace",[])
        include_ws_list = []
        if len(include_ws):
            for iws in include_ws:
                inc_ws = self.resource_check(val=iws.lower(),items=ws_id_list)
                if inc_ws:
                    include_ws_list.append(iws)
            # If Include Workspace List is Empty. No Workspace to Deploy To THIS Org. Don't Add Policy 
            if len(include_ws_list) == 0:
                log.info(f"Not Including Policy | No WS in include list in org | Name: {policy_set_name} | Org: {org_name} | Id: {org_id} | OrgsToInlcude: {include_ws}")
                cont_processing = False
            else:
                log.info(f"Include Workspaces Only Found | Name: {policy_set_name} | Org: {org_name} | Id: {org_id} | WorkspacesIncluded: {len(include_ws_list)} | TotalWorkspaces: {len(ws_id_list)} | ValidationCheck: {len(ws_id_list) - len(include_ws_list)}")
                pset["workspace_ids"] = include_ws_list
                pset["workspace_inclusions"] = include_ws_list
                pset["is_global"] = False 
        # No include found - Processing all workspaces 
        #else:
        #    pset["workspace_ids"] = ws_id_list
        # Get Latest Workspaces 
        ws_id_list = pset["workspace_ids"]
        if len(ws_id_list):
            # Check for Exclude/Exception Workspaces 
            exclude_ws = exceptions.get("workspace",[])
            # Check for project name exclusions 
            atm_exclusion = exceptions.get("project_name",[])
            if len(atm_exclusion):
                for ae in atm_exclusion:
                    for pj in list(prj_to_ws_mapping.keys()):
                        if pj.strip().lower() == ae.strip().lower(): 
                            pj_ws_list = prj_to_ws_mapping[pj].get("workspaces",[])
                            if len(pj_ws_list):
                                log_exceptions.info(f"Found Exception For Project | PolicySetName: {policy_set_name} | PrjName: {pj} | WsCountToExclude: {len(pj_ws_list)}")
                                for pj_ws in pj_ws_list:
                                    exclude_ws.append(pj_ws)
                            break 
            exclude_ws_list = []
            if len(exclude_ws):
                for ews in exclude_ws:
                    is_excluded = self.resource_check(val=ews.lower(),items=ws_id_list)
                    if is_excluded:
                        exclude_ws_list.append(ews)
                # Exceptions found process in org. Add only valid ws
                # Re-architected to add exception in TFE rather than assign to specific workspaces with no exceptions making below redundant 
                validated_exception_list = []
                if len(exclude_ws_list):
                    updated_ws_list = []
                    for cws in ws_id_list:
                        exception_found = False
                        for ews in exclude_ws_list:
                            if ews.lower() == cws.lower():
                                exception_found = True 
                                validated_exception_list.append(cws)
                                break 
                        if exception_found == False:
                            updated_ws_list.append(cws)
                if len(validated_exception_list):
                    pset["workspace_exclusions"] = validated_exception_list
                    # Exceptions Found and Workspaces in Org - Remove WS with exception from Policy Set
                    if len(updated_ws_list):
                        log_exceptions.info(f"Exceptions Found | Name: {policy_set_name} | Org: {org_name} | Id: {org_id} | WorkspacesExcluded: {len(exclude_ws_list)} | TotalWorkspaces: {len(ws_id_list)} | WorkspacesToAdd: {len(updated_ws_list)} | ValidationCheck: {len(ws_id_list) - len(exclude_ws_list)}")
                        pset["workspace_ids"] = updated_ws_list
                    # Exceptions Found for all WS's in Org - Not Adding Policy Set 
                    else:
                        log_exceptions.info(f"Exceptions Found for all Workspaces in Org Not including Policy Set in Org | Name: {policy_set_name} | Org: {org_name} | Id: {org_id}")
                        cont_processing = False 
                # Exceptions found but workspaces are not part of org 
                # else:
                #    pset["workspace_ids"] = ws_id_list
            # No Exceptions Found 
            # else:
            #    pset["workspace_ids"] = ws_id_list
        else:
            if cont_processing:
                log.warning(f"Continue Processing set to {cont_processing} but Workspace ID is Empty | No adding policy set | Name: {policy_set_name} | Org: {org_name} | Id: {org_id}")
                cont_processing = False

        if len(pset["workspace_ids"])==0:
            #pset["workspace_ids"] = [{"ws_id":wid} for wid in pset["workspace_ids"]]
        #else:
            cont_processing = False 
            log.error(f"workspace_ids is empty | nothing to deploy to")
        
        policy_set_config = {} 
        if cont_processing:
            policy_set_config = {
                "organization": pset["organization"],
                "organization_id": pset["organization_id"],
                "policy_set_name": pset["policy_set_name"],
                "policy_set_description": pset["policy_set_description"],
                "policy_engine": pset["policy_engine"],
                "workspace_ids":pset["workspace_ids"],
                "is_global":pset.get("is_global",True),
                "workspace_exclusions":pset.get("workspace_exclusions",[]),
                "workspace_inclusions":pset.get("workspace_inclusions",[])
                #"policies":[]#{}
            }
            set_policy_list = []#{}
            for pkx,pkey in enumerate(pset["policies"]):
                is_active = pkey.get("is_active",True)
                if is_active:
                    pol_dict = {
                        "organization": pset["organization"],
                        "organization_id": pset["organization_id"],
                        "policy_set_name": pset["policy_set_name"],
                        "policy_set_description": pset["policy_set_description"],
                        "policy_engine": pset["policy_engine"],
                        "workspace_ids":pset["workspace_ids"],
                        "policy_name": pkey["policy_name"],
                        "policy_description": pkey["policy_description"],
                        #"policy_engine":pset["policy_engine"],
                        "opa_query": pkey["opa_query"],
                        "enforcement_mode": pkey.get("enforcement_mode","advisory"),
                        # "policy_path": "s3_bucket_encryption.rego",
                        "policy_code":pkey["policy_code"],
                        #"organization":pset["organization"]
                    }
                    set_policy_list.append(pol_dict)#{**policy_set_config,**
                    #set_policy_list[f"policy_{pkx}"] = pol_dict
            if len(set_policy_list):
                #policy_set_config["policies"] = set_policy_list
                #set_policy_list = policy_set_config
                return set_policy_list,cont_processing
            else:
                log.error(f"No Policies Found To Process | PolicySet: {pset['policy_set_name']}")
                policy_set_config = {}
                return policy_set_config,cont_processing

    def deployer(self,organization,policy_list,policy_holder,**kwargs):
        log = base.Log(name="PolicyDeployer")
        # Extract Org Id from Organization dict
        org_id = organization["id"]
        # Extract Org Name from Organization dict
        org_name = organization["name"]
        # Get Workspaces in Organization
        ws_list,ws_id_list = actions.workspaces(self.payload).list_all(org_name=org_name,return_id_list=True)
        prj_list,prj_id_list = actions.projects(self.payload).list_all(org_name=org_name,return_id_list=True,print_it=False)
        prj_to_ws_mapping = actions.helpers().map_prj_to_ws(ws_list,prj_list)
        # Begin Iterating Policy Config Sets 
        for psx,pset in enumerate(policy_list):
            # Validate policies have Policy Set  
            policies = pset.get("policies",[])
            if len(policies):
                # Add Org Id, Org Name, & Workspace Id List to payload 
                pset["organization_id"] = org_id
                pset["organization"] = org_name 
                pset["workspace_ids"] = ws_id_list
                # Get or Create Policy Set + Include/Exclude Actions
                policy_set_config,cont_processing = self.policy_set(pset,prj_to_ws_mapping)
                if cont_processing:
                    # Policy Set Passed Validation Adding to Queue
                    for psc in policy_set_config: 
                        policy_holder.append(psc)
                else:
                    log.warning(f"Policy Validation Failed or is Excluded by Include or Exceptions. Check logs above | Name: {pset['policy_set_name']} | Org: {org_name} | Id: {org_id}")
            else:
                log.error(f"No Policies Exist for Policy Set: {pset['policy_set_name']} | Org: {org_name} | Id: {org_id}")

        return policy_holder

    def start(self):
        log = base.Log(name="Start") 
        failed_list = []
        deploy_policies = False 
        tf_var_path = ""
        # Get Policy Sets and associated Policies to deploy 
        policy_list = policy_configs.main_handler(policy_path=self.payload["policy_path"])
        if len(policy_list):
            # Get list of organizations to deploy to 
            org_list = self.payload["tfe"]["org_list"]
            if self.payload["env"].lower() == "dev":
                org_found = False 
                for o in org_list:
                    if o.lower() == self.payload["tfe"]["testing_org"].lower():
                        org_found = True 
                        org_list = [o]
                        break 
                if org_found == False:
                    org_list = []
            if len(org_list):
                for oix,org in enumerate(org_list):
                    policies_to_deploy = []
                    self.payload["tfe"]["conn"] = self.payload["tfe"]["org_details"][org]["token"]
                    oid = actions.organizations(self.payload).get(org_id=org)
                    if len(oid["id"]):
                        log.info(f"{oix+1} | Processing Policies | Id: {oid['id']} | Name: {oid['name']}")
                        try:
                            policies_to_deploy = self.deployer(
                                organization=oid,
                                policy_list = policy_list,
                                policy_holder=policies_to_deploy
                            )
                        except Exception:
                            log.error(f"Organization Failed Policy | Id: {org} | Error: {traceback.format_exc()}")
                            failed_list.append(oid)
                    else:
                        log.error(f"Empty Organization ID Found | Id: {org}")

                    if len(failed_list):
                        log.warning(f"{oix+1} | Policy Failures Found for {len(failed_list)} Organizations")
                    else:
                        log.info(f"No Policy Failures Found")

                    if len(policies_to_deploy):
                        log.info(f"{oix+1} | {org} | Found {len(policies_to_deploy)} to Deploy")
                        print(json.dumps(policies_to_deploy,indent=4,default=str))
                        tf_var_path = self.tfe_set_vars(policies=policies_to_deploy)
                        deployed_successfully = tfe_deploy.main_handler(
                            workspace_id=self.payload["tfe"]["org_details"][org]["workspace"],
                            terraform_path="iac/terraform/policies",
                            packaged_path="iac/tf_policy_code.tar.gz",
                            variable_file=tf_var_path,
                            cloud="policies",
                            secret_vars = {"TFE_TOKEN":self.payload["tfe"]["conn"]},
                            regular_vars = {"TFE_HOSTNAME":self.payload["tfe"]["url"].split("//")[-1]},
                            # is_local=True,
                            return_success_status=True 
                        )
                        log.info(f"{oix+1} | {oid} | Is deployment Successful: {deployed_successfully}")
                    else:
                        log.warning(f"{oix+1} | {oid} | Policies to deploy Returned Empty | Nothing to process")
            else:
                log.warning(f"Organizations returned empty | Nothing to deploy to | Env: {self.payload['env']}")
        else:
            log.warning("Policy List Returned Empty | Nothing to process")
        #return deploy_policies,tf_var_path

    def tfe_set_vars(self,policies,**kwargs):
        file_name = kwargs.get("file_name",f"{self.payload['tfe_env']}_tfe.auto.tfvars")
        output_directory = kwargs.get("output_directory","")
        output_location = os.path.join(output_directory,file_name)
        tfe = dedent(f'''\
        policy_keys = []
        policy_list = {json.dumps(policies)}''')
        with open(output_location,"w") as fout:
            fout.write(tfe)
            fout.close()
        return output_location

def main_handler():
    log = base.Log(name="PolicyMain")
    env,tfe_env = build_helpers.iam().get_env()
    region = "us-east-1"
    reg_short = region.split("-")[1][0] + region.split("-")[-1]
    payload = {
        "env": env, 
        "tfe_env": tfe_env,
        "region": region,
        "get_secret_name":{"tfe_creds": f"terraform-{env}","tfe_orgs":f"tfe/policy_manager/{env.lower()}"},
        "policy_path":"../../../policies",
        "s3":{
            "bucket":f"pac-opa-policies-{env}-{reg_short}",
            "objects":{
                "policy_tracker":"tfe/trackers/policy_tracker.csv",
                "policy_set_tracker":"tfe/trackers/policy_set_tracker.csv",
                "exception_tracker":"tfe/trackers/policy_exception_tracker.csv",
                "policy_configs":"tfe/policies/policy_configs.json"
            }
        },
        "tfe":{
            "url":"https://tfe.cgftdev.com" if tfe_env.lower() == "ftdev" else "https://tfe.cguser.capgroup.com",
            "testing_org": "org-1zGSHHZHJU29Lugt",
            "local_path":"../../terraform/policies"
        }
    }
    payload = build_helpers.secrets_manager(payload).get_secret()
    tfe_org_dict = {}
    for okey in list(payload["tfe_orgs"].keys()):
        oname = okey.split("_")[0]
        nkey = okey.split("_")[-1]
        if nkey.lower().startswith("work"):
            nkey = "workspace"
        elif nkey.lower().startswith("tok"):
            nkey = "token"
        else:
            log.warning(f"Secret Keys Found Unknown identifier: {nkey}")
        vcheck = tfe_org_dict.get(oname,{})
        if len(vcheck) == 0:
            tfe_org_dict[oname] = {nkey:payload["tfe_orgs"][okey]}
        else:
            tfe_org_dict[oname][nkey] = payload["tfe_orgs"][okey]
    payload["tfe"]["org_list"] = list(tfe_org_dict.keys())
    payload["tfe"]["org_details"] = tfe_org_dict
    tfe_policies(payload).start()

if __name__ == "__main__":
    main_handler()


                        
