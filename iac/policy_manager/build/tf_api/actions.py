import sys
import json 
import time 
import datetime
import traceback

from tf_api import connector,base_log,data_filter

class variables(object):
    def __init__(self,payload):
        self.payload = payload
        self.tapi = connector.TfeWorkspace(self.payload)
        self.log = base_log.Log(name="TfeVariables")

    def main_vars(self,params,is_sensitive=False):
        check_dict = {
            "category":"env",#"terraform",
            "hcl":False,
            "sensitive":is_sensitive
        }
        for i in check_dict:
            if i not in list(params.keys()):
                params[i] = check_dict[i]
        var_id = []
        if "var_id" in params:
            var_id.append(params["var_id"])
            del params["var_id"]
        base_vars = {
            "data":{
                "type":"vars",
                "attributes":params,
                "relationships": {
                    "workspace": {
                        "data": {
                        "id":self.payload["tfe"]["ws_id"],
                        "type":"workspaces"
                        }
                    }
                }
            }
        }
        if var_id:
            base_vars["data"]["id"] = var_id[0]

        return base_vars
    
    def get_vars(self):
        resp = self.tapi.connect(
            api_call={
                "endpoint":f"vars?filter[organization][name]={self.payload['tfe']['org_name']}&filter[workspace][name]={self.payload['tfe']['workspace_name']}",
                "type":"get"
            }
        )
        if len(resp):
            new_resp = {}
            for i in range(0,len(resp['data'])):
                key = resp['data'][i]
                new_resp[key["attributes"]["key"]] = key["id"]
            return new_resp
        else:
            return resp

    def add_str_vars(self,config):
        is_successful = self.upload_vars(config=config,is_sensitive=False)
        return is_successful

    def add_regular_vars(self,vars_dict):
        required_keys = list(vars_dict.keys())
        is_successful = self.upload_vars(config=vars_dict,is_sensitive=False,required_keys=required_keys)
        return is_successful

    def add_secret_vars(self,vars_dict,is_aws=False):
        if is_aws:
            for c in list(vars_dict.keys()):
                vars_dict[c.lower()] = vars_dict[c]
                required_keys = ["aws_access_key_id","aws_secret_access_key","aws_session_token"]
        else:
            required_keys = list(vars_dict.keys())
        is_successful = self.upload_vars(config=vars_dict,is_sensitive=True,required_keys=required_keys)
        return is_successful

    def upload_variable(self,vars_dict, is_sensitive, **kwargs):
        if is_sensitive:
            return self.add_secret_vars(vars_dict,is_aws=kwargs.get("is_aws",False))
        else:
            return self.add_regular_vars(vars_dict)

    def upload_vars(self,config,is_sensitive,required_keys=[]):
        tfe_vars = self.get_vars()
        if len(required_keys) == 0:
            required_keys = list(config.keys())
        is_aws = True if "aws" in required_keys[0] else False
        keys_updated = []
        for i in required_keys:
            if i in list(config.keys()):
                var_key = i.upper() if is_aws == True else i
                try:
                    my_vars = {
                        "key":var_key,
                        "value":config[i],
                        "description":f"AWS Details for {i}" if is_aws == True else f"Details for {i}"
                    } 
                    req_type = "post"
                    endpoint = "vars"
                    if len(tfe_vars):
                        if var_key in list(tfe_vars.keys()):
                            my_vars["var_id"] = tfe_vars[var_key]
                            req_type = "update"
                            endpoint = f"vars/{my_vars['var_id']}"
                    var_payload = self.main_vars(params=my_vars,is_sensitive=is_sensitive)
                    resp = self.tapi.connect(
                        api_call={
                            "endpoint":endpoint,
                            "type":req_type,
                            "params":var_payload
                        }
                    )
                    log_val = "Updated" if req_type.lower() == "update" else "Created"
                    self.log.info(f"Successfully {log_val} | {i}")
                    keys_updated.append(i)
                except Exception:
                    self.log.error(f"Error Updating Key {i} | {traceback.format_exc()}")
            else:
                self.log.error(f"Error - required key not found | {i}")
        
        if len(keys_updated) == len(required_keys):
            return True 
        else:
            return False 

    def delete_var(self,var_name):
        resp = self.tapi.connect(
            api_call={
                "endpoint":f"vars?filter[organization][name]={self.payload['tfe']['org_name']}&filter[workspace][name]={self.payload['tfe']['workspace_name']}",
                "type":"get"
            }
        )
        for i in resp['data']:
            if i['attributes']['key'].lower() == var_name:
                var_id = i['id']
                var_name = i['attributes']['key']
                break 
        self.log.info(f"Deleting Variable {var_id} - {var_name}")
        resp = self.tapi.connect(
            api_call={
                "endpoint":f"vars/{var_id}",
                "type":"delete"
            }
        )

class workspaces(object):
    def __init__(self,payload):
        self.payload = payload
        self.tapi = connector.TfeWorkspace(self.payload)
        self.log = base_log.Log(name="TfeWorkspaces")
        self.ws_id = self.payload["tfe"].get("ws_id","")
    
    def list_all(self,org_name="banzai-dev",**kwargs):
        log = base_log.Log(name="ListWorkspaces")
        print_response = kwargs.get("print_it",kwargs.get("print_response",False))
        return_id_list = kwargs.get("return_id_list",False)
        return_all = kwargs.get("return_all",False)
        ws_list = []
        ws_id_list = []
        ws_all_list = []
        keep_calling = True 
        call_counter = 1
        error_counter = 0
        while keep_calling:
            try:
                rsp = self.tapi.connect(
                    api_call={
                        "endpoint":f"organizations/{org_name}/workspaces?page%5Bnumber%5D={call_counter}&page%5Bsize%5D=20",
                        "type":"get"
                    }
                )
                if print_response:
                    print(json.dumps(rsp,indent=4,default=str))
                ws_resp = rsp.get("data",[])
                meta = rsp["meta"].get("pagination",{})
                if len(ws_resp):
                    # refactor foc 
                    for w in ws_resp:
                        if return_all:
                            ws_all_list.append(w)
                        ws_list.append({
                            "id":w['id'],
                            "name":w['attributes']['name'],
                            "project":w.get("relationships",{}).get("project",{}).get("data",{}).get("id","none")
                        })
                        ws_id_list.append(w['id'])
                if len(meta):
                    current_page = meta["current-page"]
                    total_page = meta["total-pages"]
                    call_counter += 1 
                    if call_counter > total_page:
                        keep_calling = False 
                        break 
                else:
                    keep_calling = False 
                    break 
            except Exception:
                log.error(f"Failed List Workspaces | Error: {traceback.format_exc()}")
                error_counter += 1
                if error_counter > 3:
                    keep_calling = False 
                    break 
        if return_id_list:
            return ws_list,ws_id_list
        elif return_all:
            return ws_all_list
        else:
            return ws_list
        
    def list_all_orig(self,org_name="banzai-dev",**kwargs):
        print_it = kwargs.get("print_it",False)
        return_id_list = kwargs.get("return_id_list",False)
        resp = self.tapi.connect(
            api_call={
                "endpoint":f"organizations/{org_name}/workspaces",
                "type":"get"
            }
        )
        if print_it:
            print(json.dumps(resp,indent=4,default=str))
            print("\n")
        ws_list = []
        ws_id_list = []
        for d in resp["data"]:
            ws_list.append({"id":d['id'],"name":d['attributes']['name'],"project":d.get("relationships",{}).get("project",{}).get("data",{}).get("id","none")})
            ws_id_list.append(d['id'])
            #self.log.info(f"ID: {d['id']} | Name: {d['attributes']['name']}")
        if not ws_list:
            self.log.error(f"Failed to find any workspaces | {len(ws_list)}")
        if return_id_list:
            return ws_list,ws_id_list
        else:
            return ws_list

    def get_id(self,ws_name,org_name=""):
        self.log.info(f"Getting Workspace Id | Org: {org_name} | WsName: {ws_name}")
        if len(org_name) == 0:
            org_name = self.payload["tfe"]["org_name"]
        ws_list = self.list_all(org_name=org_name,print_it=False)
        if ws_list:
            ws_id = ""
            for w in ws_list:
                if ws_name.lower() == w["name"].lower():
                    ws_id = w["id"]
                    break 
            if ws_id:
                self.log.info(f"Found Workspace Id | WsName: {ws_name} | WsId: {ws_id}")
                return ws_id 
            else:
                self.log.error(f"Failed to find workspace id | WsName: {ws_name} | WorkspacesFound: {ws_list}")
                return ""
        else:
            self.log.error(f"[NoWorkspacesFound] Failed to find any workspaces for Org | {org_name}")
            return ""

    def get_ws_id(self,ws_id,caller,msg="ws_id='ws1234'"):
        log = base_log.Log(name="GetWsId")
        if len(ws_id) == 0:
            if len(self.ws_id):
                ws_id = self.ws_id
            else:
                error_resp = f"Missing workspace id parameter | Example: {caller}({msg}) or include as key in init payload['tfe'] | Supplied ws_id: {ws_id}"
                log.error(error_resp)
                raise Exception(error_resp)
        return ws_id

    def verify_access(self,ws_id=""):
        log = base_log.Log(name="VerifyWsId")
        ws_id = self.get_ws_id(ws_id=ws_id,caller="verify_access")
        try:
            resp = self.tapi.connect(
                api_call={
                    "endpoint":f"workspaces/{ws_id}",
                    "type":"get"
                }
            )
            log.info(f'Validated Workspace Access {resp["data"]["id"]} | {resp["data"]["attributes"]["name"]}')
            return {"workspace_name":resp["data"]["attributes"]["name"],"org_name":resp["data"]["relationships"]["organization"]["data"]["id"]}
        except Exception:
            log.error(f"Failed to Validate Workspace | {ws_id} | {traceback.format_exc()}")
            def_msg = "To see aviable workspaces add 'org_name' key to payload['tfe']"
            if "tfe" in list(self.payload.keys()):
                if "org_name" in list(self.payload["tfe"].keys()):
                    ws_list = self.list_all(org_name=self.payload["tfe"]["org_name"],print_it=False)
                    def_msg = f"The available workspaces are list above | WsCount: {len(ws_list)}"
            log.warning(def_msg)
            return {}

class config_version(object):
    def __init__(self,payload):
        self.payload = payload
        self.tapi = connector.TfeWorkspace(self.payload)
        self.log = base_log.Log(name="TfeConfigVersion")
        self.ws_id = self.payload["tfe"]["ws_id"]
        #self.ws_id = workspaces(self.payload).get_ws_id(ws_id=ws_id,caller="upload_code")

    def create(self):
        '''
        Purpose: Create a configuration version
        Returns: 
            1. Configurataion Version Id (cv_id)
            2. Upload URL (upload_url) - URL to upload our code to - one time generated and not stored in terraform (if lost will need to generate new config version) 
        '''
        log = base_log.Log(name="TfeConfigVersion-Create")
        try:
            resp = self.tapi.connect(
                api_call={
                    "endpoint":f"workspaces/{self.ws_id}/configuration-versions",
                    "type":"post",
                    "params":{
                        "data":{
                            "type":"configuration-versions",
                            "attributes":{
                                "auto-queue-runs":False
                            }
                        }
                    }
                }
            )
            cv_id = resp["data"]["id"]
            upload_url = resp["data"]["attributes"]["upload-url"]
            log.info(f"Successfully Created Config Version | ConfigVersId: {cv_id} | UploadUrl: {upload_url}")
        except Exception:
            cv_id = ""
            upload_url = ""
            log.error(f"Failed to Created Config Version | ws_id: {self.ws_id} | {traceback.format_exc()}")

        return cv_id,upload_url

    def upload_code(self,upload_url,zip_path):
        log = base_log.Log(name="TfeConfigVersion-UploadCode")
        try:
            # Upload Code to workspace 
            self.tapi.connect(
                api_call={
                    "url":upload_url,
                    "type":"put",
                    "upload_file":zip_path,
                    "headers":{"Content-Type": "application/octet-stream"},
                    "add_auth":False,
                    "expect_empty_return":True 
                }
            )
            log.info(f"Successfully Uploaded TF Code | Sleeping for 5 seconds")
            time.sleep(5)
            return True 
        except Exception:
            upload_url = ""
            log.error(f"Failed to Upload TF Code | ws_id: {self.ws_id} | FileUploaded: {zip_path} | {traceback.format_exc()}")
            return False

    def create_and_upload(self,zip_path):
        cv_id,upload_url = self.create()
        if len(upload_url):
            is_successful = self.upload_code(upload_url,zip_path)
            return is_successful,cv_id
        else:
            return False,cv_id

class runs(object):
    def __init__(self,payload):
        self.payload = payload
        self.tapi = connector.TfeWorkspace(self.payload)
        self.log = base_log.Log(name="TfeRuns")
        self.ws_id = self.payload["tfe"]["ws_id"]

    def variable_format(self,tf_vars):
        log = base_log.Log(name="TfeFormatVariables")
        if isinstance(tf_vars,dict):
            tf_vars=[tf_vars]
        var_list = []
        arg_supplied = []
        failed_list = []
        for tindex in range(0,len(tf_vars)):
            if isinstance(tf_vars[tindex],dict):
                tkeys = tf_vars[tindex]
                for tv in list(tkeys.keys()):
                    if tv in arg_supplied:
                        log.warning(f"Variable already added | {tv}")
                    else:
                        var_list.append(f"{tv}={tkeys[tv]}")
                        arg_supplied.append(tv)
            elif isinstance(tf_vars[tindex],str):
                if "=" in tf_vars[tindex]:
                    var_list.append(tf_vars[tindex])
            else:
                failed_list.append(tf_vars[tindex])
                log.error(f"Not supported value type | Value in index {tindex} | value: {tf_vars[tindex]}")

        if failed_list:
            return False,var_list
        else:
            return True,var_list

    def run_payload(self,config):
        log = base_log.Log(name="TfeBuildRunPayload")
        #config={"ws_id":"","cv_id":"","message":""}
        ws_id = config["ws_id"] if "ws_id" in list(config.keys()) else self.ws_id
        rtype = config.get("run_type","")
        message = f'{config["run_message"]} - {rtype}' if "run_message" in list(config.keys()) else f"CLSEC TFE API Run Trigger - {rtype}"

        params = {
            "data":{
                "attributes":{
                    "message":message
                },
                "type":"runs",
                "relationships": {
                    "workspace": {
                        "data": {
                            "type":"workspaces",
                            "id":ws_id
                        }
                    },
                    "configuration-version":{
                        "data": {
                            "type":"configuration-versions",
                            "id":config["cv_id"]
                        }
                    }
                }
            }
        }
        cont = True 
        if "variables" in list(config.keys()):
            if isinstance(config["variables"],list):
                if isinstance(config["variables"][0],dict):
                    params["data"]["attributes"]["variables"] = config["variables"]
                else:
                    cont = False
                    log.error(f"Variables Expected dict in list but found {type(config['variables'])} | {config['variables']}")
            elif isinstance(config["variables"],dict):
                params["data"]["attributes"]["variables"] = [config["variables"]]
            else:
                cont = False
                log.error(f"unsupported data type supplied to variables key | supported types: str,list | supplied type: {type(config['variables'])}")

        if "run_type" in list(config.keys()):
            if config["run_type"].lower() == "plan":
                params["data"]["attributes"]["plan-only"] = True
            elif config["run_type"].lower() == "apply":
                params["data"]["attributes"]["auto-apply"] = True
            elif config["run_type"].lower() == "run_only":
                params["data"]["attributes"]["auto-apply"] = False
            elif config["run_type"].lower() == "destroy":
                params["data"]["attributes"]["is-destroy"] = True
            else:
                log.error(f"Failed to find a valid run_type | Supplied run_type: {run_type} | Available Run types: plan, apply, run_only, destroy")
                cont = False
 
        return cont,params

    def get_details(self,run_id,config={}):
        log = base_log.Log(name="RunDetails")
        add_on = config.get("add_on",None)
        try:
            ep = f"runs/{run_id}" if not add_on else f"runs/{run_id}/{add_on}"
            resp = self.tapi.connect(
                api_call={
                    "endpoint":ep,
                    "type":"get",
                    "params":""
                }
            )
            #print(json.dumps(resp,indent=4,default=str))
            if not add_on:
                apply_id = resp["data"]["relationships"]["apply"]["data"]["id"]
                attr = resp["data"]["attributes"]
                is_apply = attr["auto-apply"]
                is_plan = attr["plan-only"]
                is_destroy = attr["is-destroy"]
                status = attr["status"]
                log.info(f"RunId: {run_id} | status: {status}")#| apply_id: {apply_id}")
            get_items = "" 
            for git in ["return_item","get_item"]:
                if git in list(config.keys()):
                    get_items = config[git]
                    break 
                else:
                    if f"{git}s" in list(config.keys()):
                        get_items = config[f"{git}s"]
                        break 
            if len(get_items):
                filter_resp = data_filter.filter_results(resp,get_items)
                if filter_resp:
                    return filter_resp
                else:
                    def_resp = config.get("default_response","all")
                    if def_resp == "all":
                        log.error(f"Filter Response Returned Empty Result | Returning Full Response")
                        return resp
                    elif def_resp in ["empty","none","null"]:
                        log.error(f"Filter Response Returned Empty Result | Returning Nothing")
                        return None 
            else:
                #log.info(f"Not return_items or get_items in config | returning full response")
                return resp 
        except Exception:
            log.error(f"Failed to get run details | RunId: {run_id} | {traceback.format_exc()}")
            return None

    def get_applies(self,apply_id,wait_counter=0,**kwargs):
        log = base_log.Log(name="RunApply")
        return_status = kwargs.get("return_status",False)
        is_complete = True 
        try:
            resp = self.tapi.connect(
                api_call={
                    "endpoint":f"applies/{apply_id}",
                    "type":"get",
                    "params":""
                }
            )
            status = resp["data"]["attributes"]["status"]
            apply_successful = False 
            if status.lower() == "finished":
                log.info(f"Run has completed successfully | {status}")
                apply_successful = True 
            elif status.lower() in ["unreachable","finished","canceled","errored"]:
                log.info(f"Run has reached final state | {status}")
            else:
                log_msg = f"Run is still processing | {status}"
                if wait_counter > 0:
                    log_msg += f" | Counter: {wait_counter}"
                log.info(log_msg)
                is_complete = False 
        except Exception:
            log.error(f"Failed to get applied id | {apply_id}")
        if return_status:
            return apply_successful
        else:
            return is_complete

    def start(self,config):
        '''
            API-Driven Runs - https://developer.hashicorp.com/terraform/cloud-docs/run/api
            - Upload configurations as a .tar.gz file
            Step 1: Push a new configuration version to existing workspace (queue plans permission)
            1.1 Define Variables to perform an upload 
                1. "path_to_content_directory"
                2. "organization" org name (not Id)
                3. "workspace" ws name (not Id)
                4. "$TOKEN" api token (bearer token)
            Step 2: Create the file for upload 
            - package TF code directory | zip dir to tar.gz 
            Step 3: Get Workspace Id 
            Step 4: Create a New Configuration Version 
            4.1. Create a "configuration-version" to associate uploaded content with workspace 
                - create configuration-version
                - from above response -> extract upload URL to be used in following step (resp['data']['attributes']['upload-url'])
            Step 5: Upload Configuration content file (upload .tar.gz file)
            - if workspace not configured for auto-apply
                -> use "Run Apply Api" to trigger auto apply 
            Step 6: 6. Delete Temporary Files
            -> in Step 4 we created "./create_config_version.json" and its no longer needed so can delete 
        '''
        log = base_log.Log(name="TfeRun")
        # Get Workspace Id 
        ws_id = config["ws_id"] if "ws_id" in list(config.keys()) else self.ws_id
        if 'ws_id' not in list(config.keys()):
            config['ws_id'] = ws_id
        # Check if Code Needs to be packaged and uploaded 
        upload_code = config.get("upload_code",False)
        upload_successful = True # Default to True in case code already uploaded 
        if upload_code:
            if "zip_file" in list(config.keys()):
                upload_successful,cv_id = config_version(self.payload).create_and_upload(zip_path=config["zip_file"])
                config["cv_id"] = cv_id
            else:
                log.error(f"No zip_file key provided | if you want to upload your code add keys to config: upload_code:True, zip_file:'path/to/zip/file'")
                upload_successful = False 
        else:
            if "cv_id" not in list(config_keys):
                if "zip_file" in list(config.keys()):
                    upload_successful,cv_id = self.upload_code(zip_path=config["zip_file"],ws_id=ws_id)
                    config["cv_id"] = cv_id
                else:
                    log.error(f"No cv_id key provided | if you want to upload your code first include keys: upload_code=True, zip_path='path/to/zip/file'")
                    upload_successful = False 
            else:
                log.info(f"Found CV ID in config payload | {cv_id}")
        # Defualt run_is_successful to False & run_id to null 
        run_is_successful = False
        run_id = ""
        wait_until_finished = config.get("exit_on_finish",True)
        wait_secs = config.get("seconds_per_check",20)
        return_success_status = config.get("return_success_status",False)
        if not isinstance(wait_until_finished,bool):
            log.warning(f"[TypeWarning] finished_exit requires boolean but received {type(wait_until_finished)} | defaulting to True")
            wait_until_finished = True 
        if upload_successful: 
            is_successful,params = self.run_payload(config)
            if is_successful:
                try:
                    resp = self.tapi.connect(
                        api_call={
                            "endpoint":"runs",
                            "type":"post",
                            "params":params
                        }
                    )
                    run_id = resp["data"]["id"]
                    log.info(f"Successfully initiated Run | {run_id}")
                    run_is_successful = True 
                    if wait_until_finished:
                        log.info(f"Wait to Exit until deployment is completed")
                        is_complete = self.get_run_status(run_id,wait_secs)
                        if return_success_status:
                            apply_id = self.get_details(
                                run_id,
                                config = {"get_items":"data.relationships.apply.data.id","default_response":"empty"}
                            )
                            is_apply_successful = self.get_applies(apply_id,wait_counter=0,return_status=True)
                except Exception:
                    log.error(f"Failed to initiate run | {traceback.format_exc()}")
        else:
            log.error(f"Failed to upload code | cv_id: {cv_id}")
        if return_success_status:
            return is_apply_successful
        else:
            return run_is_successful

    def get_run_status(self,run_id,wait_secs):
        log = base_log.Log(name="GetRunStatus")
        apply_id = self.get_details(
            run_id,
            config = {"get_items":"data.relationships.apply.data.id","default_response":"empty"}
        )
        if apply_id:
            not_finished = True 
            wait_counter = 0
            while not_finished:
                wait_counter += 1
                is_complete = self.get_applies(apply_id,wait_counter)
                if is_complete:
                    not_finished = False 
                else:
                    if wait_counter > 60:
                        log.warning("Reached time limit exiting. Check TFE UI for deployment details")
                        not_finished = False
                    else:
                        time.sleep(int(wait_secs))
            self.get_details(run_id,config={})
            return True 
        else:
            log.error(f"Failed to get apply id | RunId: {run_id}")
            return False 

class organizations(object):
    def __init__(self,payload):
        self.payload = payload
        self.tapi = connector.TfeWorkspace(self.payload)

    def get(self,**kwargs):
        log = base_log.Log(name="GetOrganizations")
        org_list = []
        org_id_list = []
        single_org_only = {}
        org_id = kwargs.get("org_id","")
        return_id_list = kwargs.get("return_id_list",False)
        get_items = kwargs.get("get_items",{})
        print_response = kwargs.get("print_response",kwargs.get("print_all",kwargs.get("print_it",False)))
        #get_items={"id":"attributes.external-id","name":"attributes.name"}
        keep_calling = True 
        call_counter = 1
        error_counter = 0
        while keep_calling:
            try:
                rsp = self.tapi.connect(
                    api_call={
                        "endpoint":f"organizations?page%5Bnumber%5D={call_counter}&page%5Bsize%5D=20",
                        "type":"get"
                    }
                )
                if print_response:
                    print(json.dumps(rsp,indent=4,default=str))
                orgs = rsp.get("data",[])
                meta = rsp["meta"].get("pagination",{})
                cont_calling = True 
                if len(orgs):
                    # refactor foc 
                    for o in orgs:
                        tmp_dict = {
                            "id":o.get("attributes",{}).get("external-id",""),
                            "name":o.get("attributes",{}).get("name","")
                        }
                        if len(org_id):
                            if tmp_dict["id"].lower() == org_id.lower():
                                single_org_only = tmp_dict
                                cont_calling = False 
                                break 
                        elif return_id_list == True:
                            # org_id_list
                            org_id_list.append(tmp_dict)
                        else:
                            org_list.append(o)
                if cont_calling == False:
                    keep_calling = False 
                    break 
                elif len(meta):
                    current_page = meta["current-page"]
                    total_page = meta["total-pages"]
                    call_counter += 1 
                    if call_counter > total_page:
                        keep_calling = False 
                        break 
                else:
                    keep_calling = False 
                    break 
            except Exception:
                log.error(f"Failed List Orgs | Error: {traceback.format_exc()}")
                error_counter += 1
                if error_counter > 3:
                    keep_calling = False 
                    break 
        if len(org_id):
            return single_org_only
        if return_id_list:
            return org_id_list
        else:
            return org_list

class projects(object):
    def __init__(self,payload):
        self.payload = payload
        self.tapi = connector.TfeWorkspace(self.payload)
        self.log = base_log.Log(name="TfeProjects")

    def list_all(self,org_name,**kwargs):
        log = base_log.Log(name="ListProjects")
        return_id_list = kwargs.get("return_id_list",False)
        get_items = kwargs.get("get_items",{})
        return_all = kwargs.get("return_all",False)
        print_response = kwargs.get("print_response",kwargs.get("print_it",False))
        #get_items={"id":"attributes.external-id","name":"attributes.name"}
        prj_list = []
        prj_id_list = []
        prj_all_list = []
        keep_calling = True 
        call_counter = 1
        error_counter = 0
        while keep_calling:
            try:
                rsp = self.tapi.connect(
                    api_call={
                        "endpoint":f"/organizations/{org_name}/projects?page%5Bnumber%5D={call_counter}&page%5Bsize%5D=20",
                        "type":"get"
                    }
                )
                if print_response:
                    print(json.dumps(rsp,indent=4,default=str))
                prjs = rsp.get("data",[])
                meta = rsp["meta"].get("pagination",{})
                if len(prjs):
                    # refactor foc 
                    for p in prjs:
                        if return_all:
                            prj_all_list.append(p)
                        prj_list.append({
                            "id":p['id'],
                            "name":p['attributes']['name']
                        })
                        prj_id_list.append(p['id'])
                if len(meta):
                    current_page = meta["current-page"]
                    total_page = meta["total-pages"]
                    call_counter += 1 
                    if call_counter > total_page:
                        keep_calling = False 
                        break 
                else:
                    keep_calling = False 
                    break 
            except Exception:
                log.error(f"Failed List Projects | Error: {traceback.format_exc()}")
                error_counter += 1
                if error_counter > 3:
                    keep_calling = False 
                    break 
        if return_id_list:
            return prj_list,prj_id_list
        elif return_all:
            return prj_all_list
        else:
            return prj_list

class helpers(object):
    def __init__(self,payload={}):
        self.payload = payload 
        self.log = base_log.Log(name="TfeHelpers")

    def map_prj_to_ws(self,ws_list,prj_list):
        # Response Returned
        # {"PROJECT_NAME":{"PROJECT_IDS":[],"WORKSPACES":[]}} 
        log = base_log.Log(name="MapPrjToWs")
        cont_ = True 
        for i in [ws_list,prj_list]:
            if len(i) == 0:
                cont_ = False
                break
        return_dict = {}
        prj_mapping = {}
        if cont_:
            for prj in prj_list:
                add_prj = True 
                pid = prj.get("id","")
                pname = prj.get("name","")
                pname = pname.strip()
                for p in [pid,pname]:
                    if len(p.strip()) == 0:
                        search_ws = False 
                        break 
                if add_prj:
                    tmp_list = prj_mapping.get(pname,{})
                    if len(tmp_list):
                        prj_mapping[pname]["projects"].append(pid.strip().lower())
                    else:
                        prj_mapping[pname] = {"projects":[pid.strip().lower()],"workspaces":[]}
            for prj_name in list(prj_mapping.keys()):
                for pid in prj_mapping[prj_name]["projects"]:
                #if search_ws: 
                    for ws in ws_list:
                        ws_prj = ws.get("project","")
                        ws_prj = ws_prj.strip()
                        if len(ws_prj):
                            if ws_prj.lower() == pid.strip().lower():
                                prj_mapping[prj_name]["workspaces"].append(ws["id"])

        return prj_mapping

    # def get_workspaces(self):
    #     log = base.Log(name="GetWorkSpaces")
    #     # Get list of organizations to deploy to 
    #     org_list = actions.organizations(self.payload).get(return_id_list=True)
    #     if self.payload["env"].lower() == "dev":
    #         org_found = False 
    #         for o in org_list:
    #             if o["id"].lower() == self.payload["tfe"]["testing_org"].lower():
    #                 org_found = True 
    #                 org_list = [o]
    #                 break 
    #         if org_found == False:
    #             org_list = []

    #     if len(org_list):
    #         org_name = org_list[0]["name"]
    #         # Get Workspaces in Organization
    #         ws_list,ws_id_list = actions.workspaces(self.payload).list_all(org_name=org_name,return_id_list=True,print_it=False)
    #         prj_list,prj_id_list = actions.projects(self.payload).list_all(org_name=org_name,return_id_list=True,print_it=False)
    #         print(json.dumps(ws_list,indent=4,default=str))
    #         print(json.dumps(prj_list,indent=4,default=str))
    #     mapping = actions.helpers().map_prj_to_ws(ws_list,prj_list)
    #     print(json.dumps(mapping,indent=4,default=str))


