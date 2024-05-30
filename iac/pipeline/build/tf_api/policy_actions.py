import sys
import json 
import time 
import requests 
import datetime
import traceback

from logger import base as base_log
from tf_api import connector,data_filter

global log 
log = base_log.Log(name="PolicyActions")

class policy(object):
    def __init__(self,payload):
        self.payload = payload
        self.tapi = connector.TfeWorkspace(self.payload)
    
    def create(self,org_name,**kwargs):
        log = base_log.Log(name="CreatePolicy")
        policy_create_successful = False
        # Enforcement Mode 
        # 1.) Sentinel: valid values are "hard-mandatory", "soft-mandatory", and "advisory". 
        # 2.) OPA: Valid values are "mandatory"and "advisory"
        var_payload = {
            "data":{
                "type": "policies",
                "attributes": {
                    "name": kwargs["name"],
                    "description": kwargs.get("description",""),
                    "kind": kwargs["policy_type"].lower(), # Sentinel or OPA
                    "enforcement-level": kwargs.get("enforcement_mode",kwargs.get("enforcement_level",kwargs.get("enforcement","advisory"))).lower()
                },
                "relationships": {
                    "policy-sets": {
                        "data":[]
                    }
                }
            }
        }
        if kwargs["policy_type"].lower() == "opa":
            # The OPA query to run. Only valid for OPA policies.
            var_payload["data"]["attributes"]["query"] = kwargs["query"] # Example: "terraform.main"
        pol_set_id = kwargs.get("policy_set_id",kwargs.get("set_id",""))
        if len(pol_set_id):
            var_payload["relationships"]["policy-sets"]["data"].append(
                {
                    "id":pol_set_id.lower(),
                    "type":"policy-sets"
                }
            )
        upload_policy = False
        try:
            resp = self.tapi.connect(
                api_call={
                    "endpoint":f"/organizations/{org_name}/policies",
                    "type":"post",
                    "params":var_payload
                }
            )
            upload_policy = True
            policy_create_successful = True
        except Exception:
            log.error(f"Failed to Create Policy: {traceback.format_exc()}")
            policy_create_successful = False
        # return key: 
        return_key = kwargs.get("return_key","")
        if upload_policy:
            rsp = resp.get("data",{})
            if rsp:
                policy_id = rsp.get("id","")
                if len(policy_id):
                    log.info(f"Successfully Created Policy: {policy_id} | Org: {org_name}")
                    policy_file_path = kwargs.get("policy_file_path","")
                    if len(policy_file_path):
                        log.info(f"Sleeping for 3 Seconds before uploading")
                        time.sleep(3)
                        upload_successful = self.upload(policy_id=policy_id,policy_file_path=policy_file_path)
                        if len(return_key):
                            return rsp[return_key.lower()],policy_create_successful,True
                        else:
                            return rsp,policy_create_successful,True
                    else:
                        if len(return_key):
                            return rsp[return_key.lower()],policy_create_successful,False
                        else:
                            return rsp,policy_create_successful,False
                else:
                    log.warning(f"Policy ID Not Returned | KeysFound: {list(rsp.keys())}")
                    return rsp,policy_create_successful,False
            else:
                log.error(f"Failed to Create Policy | Error: {traceback.format_exc()}")
                return resp,policy_create_successful,False
        else:
            return resp,policy_create_successful,False 

    def upload(self,policy_id,policy_file_path):
        log = base_log.Log(name="UploadPolicy")
        try:
            resp = self.tapi.connect(
                api_call={
                    "endpoint":f"policies/{policy_id}/upload",
                    "type":"put",
                    "upload_file":policy_file_path,
                    "headers":{"Content-Type": "application/octet-stream"},
                    "add_auth":True,
                    "expect_empty_return":True 
                }
            )
            log.info(f"Successfully Uploaded Policy: {policy_id}")
            return True 
        except Exception:
            log.error(f"Failed To Upload Policy {policy_id} | Error: {traceback.format_exc()}")
            return False 

    # Use to Update Policy Enforcement Mode 
    def update(self,policy_id,**kwargs):
        log = base_log.Log(name="UpdatePolicy")
        if "policy_file_path" in list(kwargs.keys()):
            upload_successful = self.upload(policy_id=policy_id,policy_file_path=policy_file_path)
            return upload_successful
        # else:
        mode = kwargs.get("enforcement_mode","")
        if len(mode): 
            var_payload = {
                "data":{
                    "type": "policies",
                    "attributes": {
                        "enforcement-level": mode.lower()
                    }
                }
            }
            for k in ["description","query"]:
                val = kwargs.get(k,"")
                if len(val):
                    var_payload["data"]["attributes"][k] = val
        try:
            resp = self.tapi.connect(
                api_call={
                    "endpoint":f"policies/{policy_id}",
                    "type":"patch",
                    "params":var_payload
                }
            )
            rsp = resp.get("data",{})
            update_successful = False
            if len(rsp):
                pid = rsp.get("id","")
                if len(pid):
                    if pid == policy_id:
                        log.info(f"Successfully updated Policy: {pid}")
                        update_successful = True
            if update_successful == False:
                log.warning(f"Request Did Not Return Error But Nothing Return | Failed to update Policy: {policy_id}")
            return resp, update_successful
        except Exception:
            log.error(f"Failed to Update Policy {policy_id} | Error: {traceback.format_exc()}")
            return {},False

    def delete(self,policy_id,**kwargs):
        log = base_log.Log(name="DeletePolicy")
        try:
            self.tapi.connect(
                api_call={
                    "endpoint":f"policies/{policy_id}",
                    "type":"delete",
                    "expect_empty_return":True 
                }
            )
            log.info(f"Successfully Deleted Policy: {policy_id}")
            return True 
        except Exception:
            log.error(f"Failed to Delete Policy: {policy_id} | Error: {traceback.format_exc()}")
            return False 
    
    def get(self,policy_id,**kwargs):
        log = base_log.Log(name="GetPolicy")
        try:
            resp = self.tapi.connect(
                api_call={
                    "endpoint":f"policies/{policy_id}",
                    "type":"get"
                }
            )
            return resp
        except Exception:
            log.error(f"Failed to Get Policy: {policy_id} | Error: {traceback.format_exc()}")
            return {} 

    def list_(self,policy_id,**kwargs):
        log = base_log.Log(name="GetPolicy")
        try:
            resp = self.tapi.connect(
                api_call={
                    "endpoint":f"organizations/{org_name}/policies",
                    "type":"get"
                }
            )
            return resp
        except Exception:
            log.error(f"Failed to Get Policy: {policy_id} | Error: {traceback.format_exc()}")
            resp = {}

class policy_sets(object):
    def __init__(self,payload):
        self.payload = payload
        self.tapi = connector.TfeWorkspace(self.payload)

    def get_payload(self,item,**kwargs):
        log = base_log.Log(name="CreatePolicySetPayload")
        #item = kwargs.get("item","create")
        req_payload = {}
        if item.lower() == "create":
            req_payload = {
                "data": {
                    "type": "policy-sets",
                    "attributes": {
                        "name": kwargs["name"],
                        "description": kwargs.get("description",""),
                        "global": kwargs.get("is_global",True),
                        "kind": kwargs["policy_type"].lower(), # Sentinel or OPA
                    },
                    "relationships": {
                        "projects": {
                            "data":[]
                        },
                        "workspaces": {
                            "data": []
                        },
                        "workspace-exclusions": {
                            "data": []
                        }
                    }
                }
            }
            is_global = req_payload["data"]["attributes"]["global"] # True
            for rel_key in ["policies","projects","workspaces","exceptions"]:
                vals = kwargs.get(rel_key.lower(),[])
                if len(vals):
                    if isinstance(vals,str):
                        if "," in vals:
                            vals = vals.strip().split(",")
                        else:
                            vals = [vals]
                    if rel_key.lower() == "exceptions":
                        key_dict = {"key":"workspace-exclusions","type":"workspaces"}
                    else:
                        key_dict = {"key":rel_key,"type":rel_key}
                        if rel_key.lower() in ["projects","workspaces"]:
                            is_global = False if is_global == True else is_global
                    for v in vals:
                        req_payload["data"]["relationships"][key_dict["key"]]["data"].append({"id":v,"type":key_dict["type"]})
            req_payload["data"]["attributes"]["global"] = is_global
        elif item.lower() == "update":
            resources = kwargs.get("resources",[])
            resource_type = kwargs.get("resource_type")
            if len(resources):
                if isinstance(resources,str):
                    if "," in resources:
                        resources = resources.strip().split(",")
                    else:
                        resources = [resources]
                # TODO: Add Policy Validation | Verify policies exist prior to adding to set
                req_payload = {"data":[{"type":resource_type,"id":p} for p in resources]}
        elif item.lower() == "parameters":
            req_payload = {
                "data":{
                    "type":"vars",
                    "attributes":{
                        "key":kwargs["key"],
                        "value":kwargs["value"],
                        "category":"policy-set",
                        "sensitive":kwargs.get("is_sensitive",False)
                    }
                }
            }
            param_id = kwargs.get("id",kwargs.get("param_id",""))
            if len(param_id):
                req_payload["data"]["id"] = param_id
        else:
            log.error(f"Invalid Item | SuppliedItem: {item} | ValidItems: 'create' and 'update'")
            
        return req_payload 

    def create(self,organization,**kwargs):
        log = base_log.Log(name="CreatePolicySet")
        req_payload = self.get_payload(item="create",**kwargs)
        return_all = kwargs.get("return_all",False)
        try:
            resp = self.tapi.connect(
                api_call={
                    "endpoint":f"organizations/{organization}/policy-sets",
                    "type":"post",
                    "params":req_payload
                }
            )
            pol_set_id = resp.get("data",{}).get("id","")
            if return_all:
                log.info(f"Successfully Created Policy Set | ID: {pol_set_id} | Org: {organization}")
                return resp
            else:
                log.info(f"Successfully Created Policy Set | ID: {pol_set_id} | Org: {organization}")
                return pol_set_id 
        except Exception:
            log.error(f"Failed to Get Policy: {policy_id} | Org: {organization} | Error: {traceback.format_exc()}")
            if return_all:
                return {}
            else:
                return ""

    def full_update(self,policy_set_id,**kwargs):
        log = base_log.Log(name="UpdatePolicySet")
        req_payload = kwargs.get("req_payload","")
        #req_payload = self.get_payload(item="create",**kwargs)
        try:
            resp = self.tapi.connect(
                api_call={
                    "endpoint":f"policy-sets/{policy_set_id}",
                    "type":"patch",
                    "params":req_payload
                }
            )
            print(json.dumps(resp,indent=4,default=str))
            return resp
        except Exception:
            log.error(f"Failed to Get Policy: {policy_id} | Error: {traceback.format_exc()}")
            return {}

    def update(self,policy_set_id,item,action,resources,**kwargs):
        # Able To Add: Policies, Projects, Workspaces, workspace-exclusions
        log = base_log.Log(name=f"{action.title()}{item.title()}ToSet")
        if item.lower() in ["exceptions","exclusions"]:
            item = "workspace-exclusions"
        resource_type = "workspaces" if item.lower() == "workspace-exclusions" else item.lower()
        req_payload = self.get_payload(item="update",resources=resources,resource_type=resource_type)
        resp = {}
        if req_payload:
            if action.lower() in ["add","attach","post"]:
                http_action = "post"
            elif action.lower() in ["delete","remove"]:
                http_action = "delete"
            else:
                http_action = ""
            print_summary_only = kwargs.get("print_summary_only",False)
            print_summary = kwargs.get("print_summary",False)
            if print_summary_only == True or print_summary == True:
                print(f"1. Endpoint: policy-sets/{policy_set_id}/relationships/{item}")
                print(f"2. Resource To Update: {resource_type}")
                print(f"3. Http Action: {http_action}")
                print(f"4. Payload")
                print(json.dumps(req_payload,indent=4,default=str))
                if print_summary_only:
                    http_action = ""
            if len(http_action):
                if print_summary_only:
                    raise Exception(f"Error Print Summary Only set to {print_summary_only} but attempted to deploy")
                    sys.exit()
                try:
                    # headers = {
                    #     "Authorization":f"Bearer {self.payload['tfe']['conn']}",
                    #     "Content-Type":"application/vnd.api+json"
                    # }
                    # resp = requests.post(
                    #     url = f"https://tfe.cguser.capgroup.com/api/v2/policy-sets/{policy_set_id}/relationships/workspace-exclusions",#policy-sets/{policy_set_id}/relationships/{item}",
                    #     headers=headers,
                    #     data=json.dumps(req_payload),
                    #     verify=True
                    # )
                    # print(f"StatusCode: {resp.status_code}")
                    # print(resp.text)
                    # print(resp.json())
                    resp = self.tapi.connect(
                        api_call={
                            "endpoint":f"policy-sets/{policy_set_id}/relationships/{item}",
                            "type":http_action,
                            "params":json.dumps(req_payload)
                        }
                    )
                except Exception:
                    log.error(f"Failed to Update Policy Set: {policy_set_id} | Error: {traceback.format_exc()}")
            else:
                if print_summary_only == False:
                    log.error(f'Invalid Action | SuppliedAction: {action} | ValidActions -> Add to policy: "add","attach","post" | Remove from policy: "delete","remove"')
        else:
            log.error(f"Request Payload Returned Empty | Nothing to do")

        return resp 

    def delete(self,policy_set_id,**kwargs):
        log = base_log.Log(name="DeletePolicySet")
        try:
            resp = self.tapi.connect(
                api_call={
                    "endpoint":f"policy-sets/{policy_set_id}",
                    "type":"delete"
                }
            )
            return resp
        except Exception:
            log.error(f"Failed to Get Policy: {policy_id} | Error: {traceback.format_exc()}")
            return {}

    def versions(self,policy_set_id,action,**kwargs):
        log = base_log.Log(name=f"{action.title()}PolicySetVersion")
        process_request = True 
        get_items = kwargs.get("get_items",{})
        if action.lower() == "create":
            req_dict = {
                "endpoint":f"policy-sets/{policy_set_id}/versions",
                "type":"post",
                "print_response":kwargs.get("print_response",False)
            }
        elif action.lower() == "get":
            req_dict = {
                "endpoint":f"policy-set-versions/{kwargs['version_id']}",
                "type":"get",
                "print_response":kwargs.get("print_response",False)
            }
        elif action.lower() == "upload":
            upload_url = kwargs.get("upload_url","")
            if not upload_url:
                resp_dict = self.versions(policy_set_id=policy_set_id,action="create",get_items={"id":"data.id","status":"data.attributes.status","upload":"data.links.upload"})
                upload_url = resp_dict["upload"]
                version_id = resp_dict["id"]
                if resp_dict["status"].lower() != "ready":
                    keep_checking = True 
                    call_counter = 0
                    while keep_checking:
                        call_counter+=1
                        status = self.versions(policy_set_id=policy_set_id,action="get",version_id=version_id,get_items="data.attributes.status")
                        log.info(f"{call_counter} | VersionId: {version_id} | Status: {status}")
                        if status.lower() == "ready":
                            keep_checking = False 
                            break
                        elif call_counter > 60:
                            log.info(f"Calls Exceeded 60 | Calls Made: {call_counter} | Breaking and attempting upload")
                            keep_checking = False 
                            break 
                        else:
                            time.sleep(3)
            if len(upload_url):
                zip_file = kwargs.get("zip_file","")
                if len(zip_file):
                    req_dict = {
                        "url":upload_url,
                        "type":"put",
                        "upload_file":zip_file,
                        "headers":{"Content-Type": "application/octet-stream"},
                        "add_auth":False,
                        "expect_empty_return":True 
                    }
                else:
                    log.error(f"Created Version but failed to upload zip file | {policy_set_id}")
            else:
                log.error(f"Failed to Create Policy Set Version | {policy_set_id}")
        else:
            process_request = False
            log.error(f"InvalidAction | SuppliedAction: {action} | ValidActions: create, upload")
        if process_request:
            try:
                resp = self.tapi.connect(
                    api_call=req_dict
                )
                #filter_resp = data_filter.filter_results(resp,get_items)
                if action.lower() != "upload":
                    if resp:
                        if get_items:
                            return data_filter.filter_results(resp,get_items)
                        else:
                            return resp
                    else:
                        return resp 
                else:
                    return resp
            except Exception:
                log.error(f"Failed to {action.title()} Policy Set Version: {policy_set_id} | Error: {traceback.format_exc()}")
                return {}
        else:
            return {} 

    def parameters(self,policy_set_id,action,**kwargs):
        log = base_log.Log(name=f"{action.title()}PolicySetParemeters")
        if action.lower() == "create":
            params = kwargs.get("params",{})
            cresp = {}
            if params:
                create_key_list = list(params.keys())
                for pkey in create_key_list:
                    req_payload = self.get_payload(item="parameters",key=pkey,value=params[pkey],is_sensitive=kwargs.get("is_sensitive",False))
                    tresp = self.param_actions(policy_set_id=policy_set_id,action="post",req_payload=req_payload,params_to_dict=True)
                    cresp = {**cresp,**tresp}
            else:
                log.warning(f"'params' dict empty | Nothing to Create")
            return cresp 
        elif action.lower() == "list":
            return self.param_actions(policy_set_id=policy_set_id,action="get",params_to_dict=kwargs.get("params_to_dict",False))
        elif action.lower() == "update":
            params = kwargs.get("params",{})
            cresp = {}
            if params:
                param_id = kwargs.get("param_id","")
                if not param_id:
                    http_action = "patch"
                    tresp = self.param_actions(policy_set_id=policy_set_id,action="get",params_to_dict=True)
                    if len(tresp):
                        update_key_list = list(params.keys())
                        for pkey in update_key_list:
                            pid = ""
                            for ckey in list(tresp.keys()):
                                if ckey.lower() == pkey.lower():
                                    pid = tresp[ckey]["id"]
                                    break 
                            if not pid:
                                log.warning(f"Parameter Not Found for '{pkey}' | Creating as New")
                                http_action = "post"
                            req_payload = self.get_payload(item="parameters",key=pkey,value=params[pkey],param_id=pid,is_sensitive=kwargs.get("is_sensitive",False))
                            tresp = self.param_actions(policy_set_id=policy_set_id,action=http_action,req_payload=req_payload,params_to_dict=True)
                            cresp = {**cresp,**tresp}
                    else:
                        log.warning(f"No Parameters Found | To create change action='create'")
                else:
                    pkey = list(params.keys())
                    if pkey == 1:
                        req_payload = self.get_payload(item="parameters",key=pkey[0],value=params[pkey[0]],param_id=param_id,is_sensitive=kwargs.get("is_sensitive",False))
                        tresp = self.param_actions(policy_set_id=policy_set_id,action="patch",req_payload=req_payload,params_to_dict=True)
                        cresp = {**cresp,**tresp}
                    else:
                        log.error(f"Multiple Parameters Given but only 1 paremeter key found | {param_id}")
            else:
                log.warning(f"'params' dict empty | Nothing to Update")
            return cresp 
        elif action.lower() == "delete":
            process_request = True 
            name = kwargs.get("name","")
            param_id = kwargs.get("param_id","")
            if not name:
                if not param_id:
                    process_request = False 
                    log.error(f"Missing Required Parameter | 'param_id' OR 'name' parameter key to delete")
            if process_request:
                delete_id_list = []
                if not param_id:
                    tresp = self.param_actions(policy_set_id=policy_set_id,action="get",params_to_dict=True)
                    if len(tresp):
                        if isinstance("name",str):
                            if "," in name:
                                name = name.strip().split(",")
                            else:
                                name = [name]
                        for n in name:
                            pid = ""
                            for ckey in list(tresp.keys()):
                                if ckey.lower() == n.lower():
                                    pid = tresp[ckey]["id"]
                                    delete_id_list.append(pid)
                                    break 
                            if not pid:
                                log.warning(f"Parameter Not Found for '{n}' | Nothing to delete")
                    else:
                        log.warning(f"No Parameters in TFE Policy Set") 
                else:
                    delete_id_list.append(param_id)
                if len(delete_id_list):
                    for pid in delete_id_list:
                        self.param_actions(
                            policy_set_id=policy_set_id,
                            action="delete",
                            api_call={
                                "endpoint":f"policy-sets/{policy_set_id}/parameters/{pid}",
                                "type":"delete",
                                "expect_empty_return":True 
                            }
                        )
                else:
                    log.warning("Id List is Empty | Nothing to Delete")
        else:
            log.error(f"InvalidAction | SuppliedAction: {action} | ValidActions: create, update, delete, list, or get")

    def param_actions(self,policy_set_id,action,**kwargs):
        log = base_log.Log(name=f"{action.title()}PolicySetParemeters")
        api_call = kwargs.get("api_call",{})
        if not api_call:
            api_call={
                "endpoint":f"policy-sets/{policy_set_id}/parameters",
                "type":action
            }
            params = kwargs.get("req_payload",{})
            if len(params):
                api_call["params"] = params
        try:
            resp = self.tapi.connect(
                api_call=api_call
            )
            expect_empty = api_call.get("expect_empty_return",False)
            if expect_empty:
                return None
            else:
                if resp:
                    rdata = resp.get("data",[])
                    if isinstance(rdata,dict):
                        rdata = [rdata]
                    get_items = kwargs.get("get_items","")
                    params_to_dict = kwargs.get("params_to_dict",False)
                    #params_to_dict = kwargs.get("params_to_dict",False)
                    if rdata:
                        if get_items:
                            return data_filter.filter_results(resp,get_items)
                        elif params_to_dict:
                            ret_dict = {}
                            for rdict in rdata:
                                req_dict[rdict["attributes"]["key"]] = {
                                    "id":rdict["id"],
                                    "value":rdict["value"],
                                    "is_sensitive":rdict["sensitive"]
                                }
                        else:
                            return rdata
                    else:
                        return resp 
                else:
                    return resp 
        except Exception:
            log.error(f"Failed to {action.title()} Policy Set Version: {policy_set_id} | Error: {traceback.format_exc()}")
            return {}

    def get(self,policy_set_id,**kwargs):
        log = base_log.Log(name="GetPolicySet")
        return_key = kwargs.get("return_key","")
        print_it = kwargs.get("print_it",kwargs.get("print_response",False))
        try:
            resp = self.tapi.connect(
                api_call={
                    "endpoint":f"policy-sets/{policy_set_id}",
                    "type":"get"
                }
            )
            if print_it:
                print(json.dumps(resp,indent=4,default=str))
            rsp = resp.get("data",{})
            if len(rsp):
                if len(return_key)== 0:
                    return resp
                elif return_key.lower() == "includes_excludes":
                    dict_ = {"includes":[],"exceptions":[]}
                    includes = rsp["relationships"]["workspaces"]["data"]
                    if len(includes):
                        dict_["includes"] =  [l["id"].lower() for l in includes]
                    excludes = rsp["relationships"]["workspace-exclusions"]["data"]
                    if len(excludes):
                        dict_["exceptions"] =  [l["id"].lower() for l in excludes]
                    return dict_ 
                else:
                    return resp 
            else:
                log.warning(f"No Policy Set Found for | {policy_set_id}")
        except Exception:
            log.error(f"Failed to Get Policy: {policy_set_id} | Error: {traceback.format_exc()}")
            return {} 

# organizations/banzai-qa/policy-sets?include=current_version%2Cnewest_version&organization_name=banzai-qa&page%5Bnumber%5D=1&page%5Bsize%5D=50&search%5Bname%5D=
