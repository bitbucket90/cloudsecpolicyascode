import os 
import sys 
import json 
import uuid
import shutil
import hashlib 
import datetime
import traceback

import rego_utils
from logger import base 
from tf_api import data_filter

class policies(object):
    def __init__(self,payload):
        self.payload = payload
        self.set_tracker = []
        self.policy_tracker = []

    def key_search(self,key_list,config_dict,desired_key,default_val=""):
        log = base.Log(name="KeySearch")
        key = ""
        val = ""
        key_found = False 
        if isinstance(key_list,str):
            if "," in key_list:
                key_list = key_list.strip().split(",")
            else:
                key_list = [key_list]
        if desired_key not in key_list:
            key_list.insert(0,desired_key)
        for k in key_list:
            found_key = False
            for i in list(config_dict.keys()):
                if i.lower() == k.lower():
                    key = k
                    if isinstance(config_dict[k],str):
                        val = config_dict[k].strip()
                    else:
                        val = config_dict[k]
                    found_key = True 
                    break 
            if found_key:
                key_found = True 
                break
        if not val:
            if len(key):
                config_dict[desired_key] = config_dict.pop(key)
            config_dict[desired_key] = default_val
        else:
            if isinstance(default_val,list):
                if isinstance(val,str):
                    if len(val):
                        if "," in val:
                            val = [i.strip() for i in val.strip().split(",")]
                        else:
                            val = [val]
                    else:
                        val = []
                if val:
                    vlist = []
                    for v in val:
                        v = v.strip()
                        if len(v):
                            vlist.append(v)
                    config_dict[key] = vlist
                else:
                    config_dict[key] = default_val
            if key != desired_key:
                config_dict[desired_key] = config_dict.pop(key)#val
                if key in list(config_dict.keys()):
                    log.error(f"KeyNotReplace | key: {key} | newKey: {desired_key}")
        return config_dict,val

    def organize_resources(self,items,**kwargs):
        log = base.Log(name="ManageTfResources")
        tracker = []
        return_dict = {}
        unknown_resource = []
        return_status = kwargs.get("return_status",False)
        tf_mapping = kwargs.get("mapping_dict",{"org":"organization","ws":"workspace","prj":"project"})
        tkeys = list(tf_mapping.keys())
        for t in tkeys:
            return_dict[tf_mapping[t].lower()] = []
        if "project_name" not in list(tf_mapping.keys()):
            return_dict["project_name"] = []
        if len(items):
            for i in items:
                rtype = ""
                for rkey in tkeys:
                    if i.lower().startswith(rkey.lower()):
                        rtype = tf_mapping[rkey]
                if len(rtype):
                    return_dict[rtype.lower()].append(i.lower())
                    tracker.append(i)
                else:
                    #log.error(f"Unknown Resourc Found | {i}")
                    #unknown_resource.append(i)
                    return_dict["project_name"].append(i.lower())
        if return_status:
            found_items = False if len(tracker) == 0 else True
            return return_dict,unknown_resource,found_items
        else:
            return return_dict,unknown_resource

    def validate_policies(self,jfin,path_dict,rego_common_utils,policy_holder,failed_list):
        log = base.Log(name="PolicyValidator")
        parent_path = path_dict["parent_path"]
        config_file_path = path_dict["config_path"]
        service_name = path_dict["service"]
        if isinstance(jfin,dict):
            jfin = [jfin]
        config_hash = hashlib.sha256(json.dumps(jfin).encode("utf-8")).hexdigest()
        # 3rd Iteration: Requires 2 iterations: policy set then policies attached to set 
        for pdx,pdict in enumerate(jfin):
            # Noramlize Keys for Policy Set
            cont_processing = True 
            # Validate Required Keys 
            pdict,set_name = self.key_search(key_list=["set_name","name"],config_dict=pdict,desired_key="policy_set_name",default_val=f"") #{svc.title()} {dom.title()}
            if len(set_name) == 0:
                set_name = "unknown_not_set"
                cont_processing = False
                log.error(f"Missing Required Key 'policy_set_name'")
            else:
                set_name = set_name.replace(" ","-")
                pdict["policy_set_name"] = set_name
                if set_name.lower() in [st.lower() for st in self.set_tracker]:
                    cont_processing = False
                    log.error(f"Policy Set Name is Already Used: {set_name} | Cannot create duplicate Set name")
            is_set_active = pdict.get("is_active",True)
            if is_set_active == False:
                log.warning(f"{pdx+1} | Policy Set is Not Active | {set_name}")
                cont_processing = False
            if cont_processing:
                pdict,set_description = self.key_search(key_list=["set_description","description"],config_dict=pdict,desired_key="policy_set_description",default_val="")
                pdict,policy_engine_type = self.key_search(key_list=["policy_engine_type","policy_type","engine_type"],config_dict=pdict,desired_key="policy_engine",default_val="")
                pdict,policy_exceptions = self.key_search(key_list=["policy_exceptions","exclusion","exclusions","exception","exclude","excludes"],config_dict=pdict,desired_key="exceptions",default_val=[])
                pdict,policy_include = self.key_search(key_list=["include_organizations","include_orgs","orgs_to_include","inclusions","includes"],config_dict=pdict,desired_key="include",default_val=[])
                # Push Empty: Deploy policy and policy set but don't apply to any workspaces 
                push_empty = pdict.get("push_empty",False)
                if not isinstance(push_empty,bool):
                    push_empty = False
                cust_set_name = set_name.replace("_","")
                cust_set_name = cust_set_name.replace("-","")
                pdict["psid"] = f"{service_name}_{cust_set_name.strip().lower()}"
                pdict["push_empty"] = push_empty
                pdict["policy_set_directory"] = parent_path
                pdict["policy_set_config_file"] = config_file_path
                pdict["policy_set_config_file_hash"] = config_hash
                tmp_dict = {}
                for t in list(pdict.keys()):
                    if t.lower() != "policies":
                        tmp_dict[t] = pdict[t]
                #policy_engine_type = "opa" if policy_engine_type.lower() == "rego" else policy_engine_type
                if policy_engine_type.lower().startswith("reg"):
                    policy_engine_type = "opa" 
                else:
                    if policy_engine_type.lower().startswith("sen"):
                        policy_engine_type = "sentinel"
                policies = pdict.get("policies",pdict.get("policy",[]))
                # Format Include/Exclude TF Orgs,Ws,Prjs
                for tfr in ["exceptions","include"]:
                    res_items = pdict[tfr]
                    #if len(res_items):
                    tf_res_dict,unknown_resource,found_items = self.organize_resources(items=res_items,return_status=True)
                    pdict[tfr] = tf_res_dict
                    if unknown_resource:
                        log.warning(f"{pdx+1} | Unknown {tfr.title()} Resources | {unknown_resource}")
                        if tfr.lower() == "include":
                            if found_items == False:
                                log.error(f"{pdx+1} | Include Items Returned Empty | Not Able To Process Policies for '{set_name}'")
                                pdict["error"] = "Invalid Resource Type for Include Policy | No Orgs to Deploy To"
                                pdict["original_include"] = policy_include
                                failed_list.append(pdict)
                                policies = []
            else:
                policies = []
            # 4th Iteration: Policies 
            if len(policies):
                log.info(f"{pdx+1} | Processing Policies for Policy Set {set_name} | PolicyCount: {len(policies)}")
                policy_type_list = []
                policy_failed_list = []
                tmp_policy_hash_list = []
                policy_processed_list = []
                # Iterate Policies for Policy Set
                for pxt,pc in enumerate(policies):
                    process_policy = True
                    policy_error_list = []
                    # if len(policy_path.split("/")) == 1:
                    pc,policy_path = self.key_search(key_list=["path","policy_file_path"],config_dict=pc,desired_key="policy_path",default_val=f"") 
                    # Generate Policy File Path and store as new key 
                    policy_file_path = os.path.join(parent_path,policy_path)
                    pc["policy_file_path"] = policy_file_path
                    # Policy Name
                    pc,policy_name = self.key_search(key_list=["name"],config_dict=pc,desired_key="policy_name",default_val="")
                    # Policy Description
                    pc,policy_description = self.key_search(key_list=["description"],config_dict=pc,desired_key="policy_description",default_val=f"")
                    # runbook_requirement_id
                    pc,runbook_requirement_id = self.key_search(key_list=["requirement_id","requirement_uid"],config_dict=pc,desired_key="runbook_requirement_id",default_val=[])
                    # Policy Enforcment Mode 
                    pc,enforcement_mode = self.key_search(key_list=["enforcement_level","mode"],config_dict=pc,desired_key="enforcement_mode",default_val="advisory")
                    # Add 
                    pc["pid"] = policy_file_path.split("/")[-1].split(".")[0].replace(" ","_").lower()
                    # Validate Policy Name is included or calculated
                    policy_name = pc["policy_name"] 
                    if len(policy_name) == 0:
                        policy_name = policy_file_path.split("/")[-1].split(".")[0].replace(" ","_").title()
                        # policy_name = policy_name.replace("_"," ").title()
                        # process_policy = False 
                        #policy_error_list.append(f"PolicyNameIsEmpty | PolicySet: {set_name} | PolicyName: {policy_name} | is_active: {is_policy_active}")
                    # Check if Policy Is Active:
                    pc["policy_name"] = policy_name.replace(" ","-")
                    if service_name.lower() not in pc["policy_name"].lower():
                        pc["policy_name"] = f"{service_name}-{policy_name}"
                    if "_" in pc["policy_name"]:
                        pc["policy_name"] = policy_name.replace("_","-")
                    is_policy_active = pc.get("is_active",True)
                    if is_policy_active == False:
                        process_policy = False 
                        policy_error_list.append(f"Policy-Not-Active: PolicySet: {set_name} | PolicyName: {policy_name} | is_active: {is_policy_active}")
                    # Set Policy Engine 
                    engine_type = policy_file_path.split("/")[-1].split(".")[-1].lower().strip()
                    if engine_type.lower().startswith("reg"):
                        engine_type = "opa" 
                    else:
                        if engine_type.lower().startswith("sen"):
                            engine_type = "sentinel"
                    # Should Policy Include Common Utils 
                    add_rego_common_utils = pc.get("include_utils", True)
                    if engine_type.lower() == "sentinel":
                        add_rego_common_utils = False 
                    # Is Policy a valid policy rule for supplied policy type 
                    if len(policy_engine_type):
                        if policy_engine_type.lower() != engine_type.lower():
                            policy_error_list.append(f"Policy-Engine-Type-Mismatch: PolicySetEngine: {policy_engine_type} | PolicyFileEngineType: {engine_type}")
                    # Enforcement advisory if warn or warning set to advisory
                    if enforcement_mode.lower().startswith("warn"):
                        enforcement_mode = "advisory"
                    else:
                        if enforcement_mode.lower().startswith("adv"):
                            enforcement_mode = "advisory"
                    # OPA Specific Checks
                    if engine_type.lower() == "opa":
                        #Check opa query key is supplied 
                        opa_query = pc.get("opa_query",pc.get("query",""))
                        if len(opa_query) == 0:
                            policy_error_list.append(f"OPA Policy Missing Required Key 'opa_query'")
                        # Check Enforcement Level 
                        if "mandatory" in enforcement_mode.lower():
                            enforcement_mode = "mandatory"
                        elif enforcement_mode.lower().startswith("man"):
                            enforcement_mode = "mandatory"
                        else:
                            for eml in ["hard","soft"]:
                                if enforcement_mode.lower().startswith(eml.lower()):
                                    enforcement_mode = "mandatory"
                                    break
                        # Validate Enforcement Values 
                        mode_is_valid = False 
                        for vm in ["advisory","mandatory"]:
                            if vm.lower() == enforcement_mode.lower():
                                mode_is_valid = True 
                                break 
                        if mode_is_valid == False:
                            policy_error_list.append(f"Invalid Enforcement Mode For {engine_type.upper()} | SuppliedValue: {enforcement_mode} | ValidValues: 'advisory','mandatory'")
                    else:
                        #"hard-mandatory", "soft-mandatory",
                        if enforcement_mode.lower() == "mandatory":
                            enforcement_mode = "hard-mandatory"
                        elif enforcement_mode.lower().startswith("man"):
                            enforcement_mode = "hard-mandatory"
                        else:
                            for eml in ["hard","soft"]:
                                if enforcement_mode.lower().startswith(eml.lower()):
                                    enforcement_mode = f"{eml}-mandatory"
                                    break 
                        # Validate Enforcement Values 
                        mode_is_valid = False 
                        for vm in ["advisory","hard-mandatory","soft-mandatory"]:
                            if vm.lower() == enforcement_mode.lower():
                                mode_is_valid = True 
                                break 
                        if mode_is_valid == False:
                            policy_error_list.append(f"Invalid Enforcement Mode For {engine_type.upper()} | SuppliedValue: {enforcement_mode} | ValidValues: 'advisory','hard-mandatory','soft-mandatory'")
                    # Store updated Enforcement Mode in dict
                    pc["enforcement_mode"] = enforcement_mode.lower()
                    # Check for Validation Errors 
                    if len(policy_error_list):
                        for pel in policy_error_list:
                            log.error(f"{pdx+1}.{pxt+1} | Name: {policy_name} | {pel} | Path: {policy_file_path}")
                        pc["error"] = policy_error_list
                        process_policy = False
                    if process_policy:
                        policy_type_list.append(engine_type)
                        try:
                            # TODO: Add Integration Test to Validate OPA/Rego Rule is Valid
                            pfile = open(policy_file_path, 'rb').read()
                            policy_hash = hashlib.sha256(pfile).hexdigest()
                            pc["policy_hash"] = policy_hash
                            if policy_hash in self.policy_tracker:
                                add_policy = False 
                            elif policy_hash in tmp_policy_hash_list:
                                add_policy = False 
                            else:
                                add_policy = True 
                            if add_policy:
                                tmp_policy_hash_list.append(policy_hash)
                                rule_code = open(policy_file_path, 'r').read()
                                if add_rego_common_utils:
                                    if "data.utils." in rule_code:
                                        rule_code=rule_code.replace("data.utils.","")
                                        rule_code+=rego_common_utils
                                pc["policy_code"] = rule_code
                                psize = os.path.getsize(policy_file_path)
                                psize_mb = psize >> 20
                                pc["policy_size"] = psize
                                pc["policy_size_mb"] = psize_mb
                                if psize_mb > 10:
                                    log.warning(f"Policy is larger than 10 mb | PolicySize: {psize_mb}")
                                policy_processed_list.append(pc)
                            else:
                                log.warning(f"Duplicated Policy Found | Not Processing Duplicate | Name: {policy_name} | ConfigPath: {config_file_path} | Path: {policy_file_path} | DuplicateHash: {policy_hash}")
                        except Exception:
                            log.error(f"Failed to Hash Policy | PolicyName: {policy_name} | Path: {policy_file_path} | Error: {traceback.format_exc()}")
                            pc["error"] = traceback.format_exc()
                            policy_failed_list.append(pc)
                # Check for Successfully processed policies and store in processing list 
                if len(policy_processed_list):
                    log.info(f"Successfully Processed Policies | SetName: {set_name} | PolicyCount: {len(policy_processed_list)}")
                    add_policies = True
                    log_error = []
                    # Override Policies list in Pdict with processed policies
                    pdict["policies"] = policy_processed_list
                    # Validate Policy Engine Type
                    if len(policy_engine_type) == 0:
                        tmp_ptype_list = []
                        for p in policy_type_list:
                            if p.lower() not in tmp_ptype_list:
                                tmp_ptype_list.append(p.lower())
                        if len(tmp_ptype_list) == 1:
                            tmp_ptype = tmp_ptype_list[0].lower()
                            policy_engine_type = tmp_ptype
                            log.info(f"{pdx+1} | Setting Policy Engine Based on Rules Found: {policy_engine_type}")
                            #pdict["policy_engine"] = tmp_ptype
                        else:
                            log_error.append(f"Found Multiple Engine Types in 'policies' | FoundPolicyTypes: {', '.join(tmp_ptype_list)}")
                    # Confirm Policy Engine Type is of valid value 
                    if policy_engine_type.lower() not in ["opa","sentinel"]:
                        log_error.append(f"Invalid Policy Engine Type | FoundEngineType: {policy_engine_type} | ValidEngineType: 'opa' or 'sentinel'")
                    if len(log_error):
                        for ple in log_error:
                            log.error(f"{pdx+1} | PolicySet: {set_name} | {ple}")
                        for p in policy_processed_list:
                            p["error"] = log_error
                            policy_failed_list.append(p)
                        add_policies = False 
                    if add_policies:
                        # Set or Override policy engine type with detected engine type 
                        pdict["policy_engine"] = policy_engine_type
                        # Add Policy Set name to Policy Set Tracker 
                        self.set_tracker.append(set_name.lower())
                        # Add policy Hashes to Policy Hash Tracker 
                        for tph in tmp_policy_hash_list:
                            self.policy_tracker.append(tph)
                        policy_holder.append(pdict)
                else:
                    log.warning(f"{pdx+1} | PolicySet: {set_name} | No Policies To Process")

                # Check & Log Any Failures 
                if len(policy_failed_list):
                    log.warning(f"{pdx+1} | Policy Failures Found | SetName: {set_name} | Count: {len(policy_failed_list)}")
                    tmp_dict["policies"] = policy_failed_list
                    failed_list.append(tmp_dict)
            else:
                if cont_processing:
                    log.warning(f"{pdx+1} | No Policies Found or is Missing Key Word 'policies' | Policy Set '{set_name}'")
        return policy_holder,failed_list

    def get(self,policies_path):
        log = base.Log(name="PolicyConfig")
        valid_policy_config_files = ["policy_set.json","policy_sets.json"]
        policy_holder = []
        failed_list = []
        exclude_items = []
        if len(exclude_items):
            exclude_items = [e.lower() for e in exclude_items]
        # Get & Parse Rego Utils
        rego_common_utils = rego_utils.to_string()
        # 1st iteration: Cloud Directories 
        # log.debug(f"CWD: {os.getcwd()}")
        for clx, cld in enumerate(os.listdir(policies_path)):
            cont_iterating = False 
            if cld.lower() not in exclude_items:
                cloud_path = os.path.join(policies_path,cld)
                if os.path.isdir(cloud_path):
                    cont_iterating = True 
            if cont_iterating: 
                # 2nd iteration: Service Directories
                for stx,svc in enumerate(os.listdir(cloud_path)):
                    # log.debug(f"{clx+1}.{stx+1} | {cld} | {svc}")
                    if svc.lower() not in exclude_items:
                        # 2nd Iteration: Security Domain  
                        service_path = os.path.join(cloud_path,svc)
                        service_configs = {"file":[],"directory":[]}
                        if os.path.isdir(service_path):
                            # log.debug(f"is_directory | {service_path}")
                            service_items = os.listdir(service_path)
                            for dtx,dom in enumerate(os.listdir(service_path)):
                                dom_policy_path = os.path.join(service_path,dom)
                                # Check if Policy Set is added in service root directory 
                                if os.path.isfile(dom_policy_path):
                                    if dom.lower() in valid_policy_config_files:
                                        service_configs["file"].append({
                                            "config_path":dom_policy_path,
                                            "parent_path":service_path
                                        })
                                elif os.path.isdir(dom_policy_path):
                                    config_file = ""
                                    for p in os.listdir(dom_policy_path):
                                        for v in valid_policy_config_files:
                                            if v.lower() == p.lower():
                                                config_file = p
                                                break 
                                    if len(config_file):
                                        config_file_path = os.path.join(dom_policy_path,config_file)
                                        service_configs["directory"].append({
                                            "config_path":config_file_path,
                                            "parent_path":dom_policy_path
                                        })
                                else:
                                    log.warning(f"UnknownFileItemType | Path: {dom_policy_path} ")
                            for ikey in ["file","directory"]:
                                svc_items = service_configs.get(ikey,[])
                                if len(svc_items):
                                    for sdict in svc_items:
                                        jfin = json.loads(open(sdict["config_path"],'r').read())
                                        try:
                                            policy_holder,failed_list = self.validate_policies(
                                                jfin,
                                                path_dict={"parent_path":sdict["parent_path"],"config_path":sdict["config_path"],"service":svc},
                                                rego_common_utils=rego_common_utils,
                                                policy_holder=policy_holder,
                                                failed_list=failed_list
                                            )
                                        except Exception:
                                            log.error(f"{clx+1}.{stx+1} | PolicyValidationErrored | location:{ikey} | FilePath: {sdict['config_path']} | Error: {traceback.format_exc()}")
                                            failed_list.append({"cloud":cld,"service":svc,"meta":svc_items,"error":traceback.format_exc()})
                                    
                           
        if len(failed_list):
            log.warning(f"Failures Found: Count: {len(failed_list)}")
            # TODO: Upload Failed List to S3
        else:
            log.info(f"No Failures Found")
        if len(policy_holder):
            log.info(f"Successfully validated {len(policy_holder)} Policy Sets")
            # TODO: Upload Policies to Deploy to S3 
        else:
            log.error(f"Policy Holder Empty | No Policy Sets to Deploy")
        return policy_holder

def main_handler(policy_path,print_response=False):
    policy_list = policies(payload={}).get(policies_path=policy_path)
    if print_response:
        print(json.dumps(policy_list,indent=4,default=str))
    return policy_list 

#if __name__ == "__main__":
   #main_handler(policy_path="/Users/jsgl/Desktop/pipelines/tfe_opa_policies/policies",print_response=True)
    # resp = json.loads(open("/Users/jsgl/Desktop/pipelines/tfe_opa_policies/src/tf_api/org_list_all_response.json","r").read())
    # get_items = {"id":"attributes.external-id","name":"attributes.name"}
    # #rsp = data_filter.filter_results(resp,get_items)
    # orgs = resp.get("data",[])
    # org_id_list = []
    # for o in orgs:
    #     # org_id_list
    #     org_id_list.append({
    #         "id":o.get("attributes",{}).get("external-id",""),
    #         "name":o.get("attributes",{}).get("name","")
    #     })
    # print(json.dumps(org_id_list,indent=4,default=str))
