# BOR: Confluence Table -> [{"Organization Name":"", "Atm_Id":"" , "WorkspaceName":"", "PolicySetName":""}] 
#  |
#  LAMBDA INPUT (First iterate table and organize policy sets and exceptions then perform below actions to make bulk requests instead of individual requests)
#  |
#  If Policy Set is Global -> Add Workspace Exclusion 
#  |
#  Else Remove Workspace Id from Workspaces attached to Policy  
#  |
#  OUTPUT -> Single Layer JSON File with Policy Exceptions to S3 Bucket 
#tfe/policy_manager/banzai-qa

import os 
import sys 
import json 
import datetime
import traceback
#import pandas as pd 

from logger import base 
from tf_api import policy_actions,actions

class exceptions(object):
    def __init__(self,payload):
        self.payload = payload 
        self.policy_sets = policy_actions.policy_sets(payload)

    def start(self,exception_list):
        log = base.Log(name="PolicyExceptions")
        for ex,edict in enumerate(exception_list):
            is_active = edict.get("is_active",True)
            if is_active:
                log.info(f"{ex+1} | Processing Exception | Name: {edict['workspace']} | Org: {edict['organization']} | PolicySet: {edict['policy_set']}")
                #rsp = self.policy_sets.get(policy_set_id=edict["policy_set_id"],print_response=True)
                self.update_policy(
                    policy_set_id=edict["policy_set_id"],
                    ws_to_exclude=edict["workspace_id"]
                )
                #rsp = actions.list_all(item="policy-sets",org_name=edict["organization"],payload=self.payload,return_all=True,print_response=False)
                #print(json.dumps(rsp,indent=4,default=str))
                #https://tfe.cguser.capgroup.com/api/v2/policy-sets/polset-RXb4Qzhnoden7gc2/relationships/workspace-exclusions
                # https://app.terraform.io/      api/v2/policy-sets/polset-3yVQZvHzf5j3WRJ1/relationships/workspace-exclusions
                # self.policy_sets.update(
                #     policy_set_id=edict["policy_set_id"],
                #     item="exceptions",
                #     action="add",
                #     resources="prj-gedCWBXARXKofp7K",#edict["workspace_id"],
                #     print_summary = True,
                #     print_summary_only = False
                # )
            else:
                log.warning(f"{ex+1} | Not Processing Exception | Active: {is_active} | Name: {edict['workspace']} | Org: {edict['organization']} | PolicySet: {edict['policy_set']}")
    
    def update_policy(self,policy_set_id,ws_to_exclude):
        log = base.Log(name="PolicyExceptions")
            #"id": "polset-RXb4Qzhnoden7gc2",
            # "type": "policy-sets",
        workspaces_to_include = []
        resp = self.policy_sets.get(policy_set_id=policy_set_id,print_response=True)
        org_name = resp["data"]["relationships"]["organization"]["data"]["id"]
        ws_list,ws_id_list = actions.workspaces(self.payload).list_all(org_name=org_name,return_id_list=True)
        if isinstance(ws_to_exclude,str):
            ws_to_exclude = [ws_to_exclude]
        for ws in ws_id_list:
            exclude_ws = False 
            for wte in ws_to_exclude: 
                if wte.lower() == ws.lower():
                    exclude_ws = True 
                    break 
            if exclude_ws == False:
                workspaces_to_include.append({"id":ws,"type":"workspaces"})
        
        #workspaces_to_include=[{"id":i,"type":"workspaces"} for i in ws_id_list]

        params = {
            "type": "policy-sets",
            "attributes": {
                #"name": resp["data"]["attributes"]["name"],
                #"description": resp["data"]["attributes"]["description"],
                "global": False,
                #"kind": resp["data"]["attributes"]["kind"],
                # "overridable": false,
                # "policy-count": 1,
                # "versioned": false
            },
            "relationships": {
                # "policies": {
                #     "data": resp["data"]["relationships"]["policies"]["data"]
                #     #     {
                #     #         "id": "pol-rD8Kf6S7TezxfUt4",
                #     #         "type": "policies"
                #     #     }
                #     # ]
                # },
                "workspaces":{
                    "data":workspaces_to_include
                }
                # "workspace-exclusions":{
                #     "data": [
                #         {
                #             "id": "ws-CoLUfqDa3bPCDR8a",
                #             "type": "workspaces"
                #         }
                #     ]
                # }
                # "workspaces": {
                #     "data": [
                #         {
                #             "id": "ws-XQp9EHDoBJGSA75K",
                #             "type": "workspaces"
                #         },
                #         {
                #             "id": "ws-xAS8aEXtnk9namB2",
                #             "type": "workspaces"
                #         },
                #         {
                #             "id": "ws-CoLUfqDa3bPCDR8a",
                #             "type": "workspaces"
                #         }
                #     ]
                # }
            }
        }
        params = {"data":params}
        print(json.dumps(params,indent=4,default=str))
        log.info(f"Policy Exception: total workspaces: {len(ws_id_list)} | to exclude: {len(ws_to_exclude)} | NewWsCount: {len(workspaces_to_include)} | offset: {len(ws_id_list) - len(ws_to_exclude)}")
        self.policy_sets.full_update(policy_set_id=policy_set_id,req_payload=params)

# {
#         "workspace":"zscaler_dlp_iac",
#         "organization":"banzai-qa",
#         "policy_set":"broad_policies"
# }

        


def main_handler():
    env,tfe_env = "dev","dev"
    payload = {
        "env":env,
        "tfe_env":tfe_env,
        "tfe":{
            "url":"https://tfe.cgftdev.com" if tfe_env.lower() == "ftdev" else "https://tfe.cguser.capgroup.com",
            "conn":""
        }
    }
    exception_list = json.loads(open("exceptions.json","r").read())
    exceptions(payload).start(exception_list)
    #exceptions(payload).test()

if __name__ == "__main__":
    main_handler()