import io 
import os
import ast
import sys
import json
import boto3 
import base64
import random
import logging
import traceback
import subprocess
import configparser
#import pandas as pd 
from botocore.exceptions import ClientError

from logging import Logger
from logging.handlers import TimedRotatingFileHandler 

class Log(Logger):
    def __init__(
        self,
        event_level='event',
        host_type=None,
        log_format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        *args,
        **kwargs
    ):
        self.formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        Logger.__init__(self, *args, **kwargs)
        self.addHandler(self.get_console_handler())
        self.propagate = False

    def get_console_handler(self):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self.formatter)
        return console_handler

class helpers(object):
    def __init__(self,payload={}):
        self.payload = payload 
        self.log = base.Log(name="AwsHelpers")
    
    def check_region(self,**kwargs):
        log = base.Log(name="RegionCheck")
        region = kwargs.get("region",self.payload.get("region",""))
        save_to_disk = kwargs.get("save",True)
        bpath = '/' + ('/'.join([i for i in os.getcwd().split("/")[:3] if len(i) > 0]))
        bpath = os.path.join(bpath,".aws/config")
        if os.path.exists(bpath):
            conf = configparser.ConfigParser()
            conf.read(bpath)
            #set_region = conf.__dict__['_sections']['default'].get("region","")
            set_region = conf.get('default','region')
            updated_region=False
            if set_region != region:
                updated_region=True
                log.info(f"RegionsNoMatch | UpdatingRegionConfig | SetRegion: {set_region} | DesiredRegion: {region}")
                conf.set('default','region',region)
                if save_to_disk:
                    with open(bpath,'w') as configfile:
                        conf.write(configfile)
            else:
                log.info(f"RegionsMatch | SetRegion: {set_region} | DesiredRegion: {region}")
        else:
            log.error(f"PathNotFound | {bpath}")
        return updated_region,set_region

    def param_check(self,base,var):
        if len(var):
            for v in list(var.keys()):
                found_key = False
                for b in list(base.keys()):
                    if v.lower() == b.lower():
                        found_key = True
                        if var[v] != base[b]:
                            if type(var[v]) == type(base[b]):
                                self.log.info(f"Updating Key: {v} | OriginalValue: {base[b]} | NewValue: {var[v]}")
                                base[b] = var[v]
                            else:
                                self.log.error(f"InvalidType | Key: {v} | BaseValue: {base[b]} (Type: {type(base[b])}) | InputValue: {var[v]} (Type: {type(var[v])})")
                if found_key == False:
                    base[v] = var[v]
        return base 

    def dict_search(self,name,var_dict,**kwargs):
        log = base.Log(name="DictSearch")
        return_value = None
        found_name = False
        return_status = kwargs.get("return_status",False)
        if len(var_dict):
            match_exact = kwargs.get("match_exact",False)
            if match_exact == False:
                name = ''.join(n for n in name if n.isalnum())
            for k in list(var_dict.keys()):
                if match_exact == False:
                    tk = ''.join(n for n in k if n.isalnum())
                if tk.lower() == name.lower():
                    return_value = var_dict[k]
                    found_name = True 
                    break 
        #else:
        #    log.warning(f"'var_dict' Empty | Nothing to search")
        if return_status:
            return return_value,found_name
        else:
            return return_value

    def tag_check(self,tags,case_type="title"):
        log = base.Log(name="TagCheck")
        try:
            if len(tags):
                if isinstance(tags,dict):
                    tags = [tags]
                tag_list = []
                for tdict in tags:
                    key_list = list(tdict.keys())
                    if "Key" in [k for k in key_list]:
                        tag_list.append(tdict)
                    else:
                        for tkey in key_list:
                            if case_type.lower() == "lower":
                                tag_list.append({'key':tkey,'value':str(tdict[tkey])})
                            else:
                                tag_list.append({'Key':tkey,'Value':str(tdict[tkey])})
                if len(tag_list):
                    log.info(f"Successfully checked tags | {len(tag_list)}")
                    return tag_list
            else:
                log.warning(f"'tags' variable is empty | returning empty")
                return []
        except Exception:
            log.error(f"Failed to Check Tags | Error: {traceback.format_exc()}")
            return []

    def min_to_secs(self,value):
        return int(value) * 60

class codestar(object):
    def __init__(self,payload={}):
        self.cli = boto3.client('codestar-connections')
        self.log = Log(name='codestar')

    def list_connections(self,item,**kwargs):
        log = Log(name="codestar_connections")
        if item.lower() == "connections":
            rsp = self.cli.list_connections()
            key = "Connections"
        elif item.lower().startswith("repo"):
            rsp = self.cli.list_repository_links()
            key = "RepositoryLinks"
        else:
            rsp = {}
            key = ""
            log.error(f"Invalid Item | SuppliedItem: {item} | ValidItems: connections or rep")
        if len(key):
            print_response = kwargs.get("print_response",kwargs.get("print_it",False))
            if print_response:
                print(json.dumps(rsp,indent=4,default=str))
            conn_list = rsp.get(key,[])
            if len(conn_list):
                log.info(f"Found {len(conn_list)} CodeStar-{key}")
            else:
                log.warning(f"No CodeStar-{key} Found")
            return conn_list
        else:
            return []

class ecr(object):
    def __init__(self,kms_arn=None):
        self.cli = boto3.client('ecr') 
        self.log = Log(name='ecr')
        self.kms_arn = kms_arn

    def is_repo(self,name,add_repo=False):
        try:
            rsp = self.cli.describe_repositories()
            repo_found = False
            for r in rsp["repositories"]:
                if r["repositoryName"] == name:
                    self.log.info(f"Found Repository | {name}")
                    repo_found = True 
                    break
            if repo_found == False:
                if add_repo:
                    return self.create_repo(name)
                else:
                    self.log.warning(f"Repository Not Found | {name}")
                    return repo_found
            else:
                return True
        except Exception:
            self.log.error(f"Failed to List Repositories | Name: {name} | {traceback.format_exc()}")
            return False
        
    def create_repo(self,name):
        try:
            log.info(f"Creating Repository | Name: {name}")
            kms_key = self.kms_arn if self.kms_arn else kms().get_arn(sid="common")
            if kms_key:
                rsp=self.cli.create_repository(
                    repositoryName=name,
                    encryptionConfiguration={
                        'encryptionType':'KMS',
                        'kmsKey':kms_key
                    }
                )
                return True
            else:
                self.log.error(f"Create Repo Failure | Failed to Get KMS Key | KMS Response: {kms_key} | RepoName: {name}")
                return False
        except Exception:
            self.log.error(f"Failed to Create Repository | Name: {name} | {traceback.format_exc()}")
            return False
    
    def list_imgs(self,name):
        try:
            rsp = self.cli.list_images(repositoryName=name)
            return rsp["imageIds"]
        except Exception:
            self.log.error(f"Failed to list images | Name: {name} | {traceback.format_exc()}")
            return []

    def generate_tag(self,name):
        try:
            img = self.list_imgs(name)
            if img:
                img_count = len(img)+1
                tag_exist = True
                cter = 0 
                tag = ""
                while tag_exist:
                    cter+=1
                    found_match = False
                    for t in img:
                        self.log.info(f'{t["imageTag"]} - {str(img_count)}')
                        if t["imageTag"] == str(img_count):
                            found_match = True 
                            break 
                    if found_match:
                        img_count+=1
                    else:
                        tag = str(img_count)
                        self.log.info(f"Found Tag: {tag}")
                        tag_exist = False
                    if len(img) == cter:
                        tag_exist = False
                        tag = "".join([str(i) for i in random.sample(range(0,9),5)])
            self.log.info(f"Tag To Use: {tag}")
            return tag
        except Exception:
            self.log.error(f"Failed to list images | Name: {name} | {traceback.format_exc()}")
            return "".join([str(i) for i in random.sample(range(0,9),5)])

    def get_login(self):
        rsp = self.cli.get_authorization_token()
        token = {}
        if "authorizationData" in list(rsp.keys()):
            if rsp["authorizationData"]:
                rid = rsp['authorizationData'][0]
                bauth = base64.b64decode(rid['authorizationToken']).decode().split(':')
                token = {
                    "username":bauth[0],
                    "password":bauth[1],
                    "registry":rid['proxyEndpoint']
                }
        if token:
            self.log.info(f"Retrieved Auth Token")
        return token 

class ecs(object):
    def __init__(self,payload={}):
        self.payload = payload 
        self.cli = boto3.client('ecs')
        self.log = Log(name="ECS")

    def list_parser(self,**kwargs):
        name = kwargs.get("name",None)
        rlist = kwargs.get("resource_list",[])
        if not rlist:
            rlist = kwargs.get("rlist",[])
        if rlist:
            found_list = []
            if name:
                if isinstance(name,str):
                    name = [name]
                for n in name:
                    for i in rlist:
                        if n.lower() in i.lower():
                            self.log.info(f"{n} | {i}")
                            found_list.append(i)
                return found_list
            else:
                self.log.warning(f"Key Variable Name not Provided | returning rlist")
                return rlist
        else:
            self.log.warning(f"Resource List provided is empty | returning empty list")
            return rlist
        
    def list_clusters(self,**kwargs):
        name = kwargs.get("name",[])
        desc_cluster = kwargs.get("describe_cluster",False)
        return_list = kwargs.get("return_list",True)
        list_tasks = kwargs.get("list_tasks",False)
        rsp = self.cli.list_clusters()#describe_clusters()
        clist = []
        if name:
            clist = self.list_parser(name=name,resource_list=rsp["clusterArns"])
            if clist:
                if desc_cluster:
                    self.desc_cluster(cluster_list=clist)
                if list_tasks:
                    self.list_tasks(cluster_list=clist)
                if return_list:
                    return clist 
            else:
                self.log.warning(f"No clusters matched for | {name}")
        else:
            return rsp["clusterArns"]

    def desc_cluster(self,**kwargs):
        cluster_list = kwargs.get("cluster_list",[])
        include = kwargs.get("include",['ATTACHMENTS','CONFIGURATIONS','SETTINGS','STATISTICS','TAGS'])
        if cluster_list:
            rsp = self.cli.describe_clusters(clusters=cluster_list,include=include)
        else:
            rsp = self.cli.describe_clusters()
        print(json.dumps(rsp,indent=4,default=str))
    
    def list_tasks(self,**kwargs):
        cluster_list = kwargs.get("cluster_list",[])
        cluster = kwargs.get("cluster",None)
        desc_task = kwargs.get("desc_task",False)
        if cluster:
            cluster_list.append(cluster)
        if cluster_list:
            clist = []
            tdict = {}
            for c in cluster_list:
                if c not in clist:
                    clist.append(c)
                    cname = c.split("/")[-1] if c.startswith("arn") else c
                    rsp = self.cli.list_tasks(cluster=c)
                    tdict["cname"] = rsp['taskArns']
            print(json.dumps(rsp,indent=4,default=str))
            return tdict
        else:
            return self.cli.list_tasks()

    def list_task_families(self,**kwargs):
        rsp = self.cli.list_task_definition_families()
        # print(json.dumps(rsp,indent=4,default=str))
        name = kwargs.get("name",None)
        if name:
            flist = self.list_parser(name=name,resource_list=rsp["families"])
            get_defs = kwargs.get("get_defs",False)
            if get_defs:
                flist = self.list_task_defs(family=flist)
                self.desc_task_def(task_def=flist)
            else:
                return flist
        else:
            return rsp["families"]

    def list_task_defs(self,**kwargs):
        family = kwargs.get("family",None)
        if family:
            if isinstance(family,str):
                family = [family]
            fdict = {}
            flist = []
            for f in family:
                rsp = self.cli.list_task_definitions(familyPrefix=f)
                tdef = rsp.get('taskDefinitionArns',[])
                if tdef:
                    fdict[f] = tdef
                    for t in tdef:
                        flist.append(t)
            print(json.dumps(fdict,indent=4,default=str))
            return flist
        else:
            rsp = self.cli.list_task_definitions()
            print(json.dumps(rsp,indent=4,default=str))
            return rsp['taskDefinitionArns']

    def desc_task_def(self,**kwargs):
        task_def = kwargs.get("task_def",[])
        if task_def:
            if isinstance(task_def,str):
                task_def = [task_def]
        tlist = []
        for tdef in task_def:
            rsp = self.cli.describe_task_definition(taskDefinition=tdef)
            tlist.append(rsp['taskDefinition'])
        if len(tlist) == 1:
            print(json.dumps(rsp,indent=4,default=str))
            return tlist[0]
        else:
            return tlist
    
    def run_task(self,**kwargs):
        cluster = kwargs["cluster"]
        network_config = kwargs["network_config"]
        task_count = kwargs.get("task_count",1)
        task_def = kwargs.get("task_definition",None)
        if not task_def:
            task_def = kwargs.get("task_def",None)
        tags = kwargs.get("tags",[])
        if tags:
            if isinstance("tags",dict):
                tags = [tags]
        if task_def:
            account_id = kwargs.get("account_id",None)
            if not account_id:
                account_id = sts().get_acct_id()
            cluster = cluster if cluster.startswith("arn") else f'arn:aws:ecs:us-east-1:{account_id}:cluster/{cluster}'
            task_def = task_def if task_def.startswith("arn") else f'arn:aws:ecs:us-east-1:{account_id}:task-definition/{task_def}'
            rsp = self.cli.run_task(
                cluster=cluster,
                count=int(task_count),
                enableECSManagedTags=False,
                enableExecuteCommand=False,
                launchType='FARGATE',
                networkConfiguration=network_config,
                propagateTags='TASK_DEFINITION',
                startedBy='boto3-local-test',
                #tags=tags,
                taskDefinition=task_def
            )
            print(json.dumps(rsp,indent=4,default=str))
        else:
            self.log.error(f"Failed to find task_definition")

class iam(object):
    def __init__(self,payload={}):
        self.payload = payload 
        self.cli = boto3.client('iam')
        self.log = Log(name="IAM")
    
    def get_env(self,**kwargs):
        acct_aliases = self.cli.list_account_aliases()['AccountAliases'][0]
        env = acct_aliases.split("-")[-1].lower().strip()
        env = "prod" if env.lower() == "prd" else env.lower()
        tfe_env_dict = {
            "dev":"dev",
            "tst":"qa",
            "prod":"prd"
        }
        azr_mgt_grps = {
            "dev":"CG-Dev",
            "tst":"CG-NonProd",
            "prod":"CG-Production"
        }
        return_azure_groups = kwargs.get("return_azure_groups",False)
        if return_azure_groups:
            self.log.info(f"AccountAlias: {acct_aliases} | Soteria Env: {env} | Terraform Env: {tfe_env_dict[env]} | AzureMgntGroup: {azr_mgt_grps[env]}")
            return env,tfe_env_dict[env],azr_mgt_grps[env]
        else:
            self.log.info(f"AccountAlias: {acct_aliases} | Soteria Env: {env} | Terraform Env: {tfe_env_dict[env]}")
            return env,tfe_env_dict[env]

class kms(object):
    def __init__(self):
        self.cli = boto3.client('kms') 
        self.log = Log(name='kms')
    
    def list_kms_keys(self,key_id):
        resp = self.cli.list_keys()
        key_arn = ""
        for i in resp["Keys"]:
            if key_id == i["KeyId"]:
                key_arn = i["KeyArn"]
                break
        return key_arn

    def list_kms_aliases(self,alias_endswith):
        resp = self.cli.list_aliases()
        key_id = ""
        for i in resp['Aliases']:
            #if i["AliasName"] == f"alias/soteria-{self.payload['env']}/useast1/s3/0/kek":
            if i["AliasName"].endswith(alias_endswith):
                self.log.info(f"Fund Alias | {i['AliasName']}")
                key_id = i['TargetKeyId']
                break 
        if key_id:
            self.log.info(f"Found Key Id - {key_id} - Getting ARN")
            key_arn = self.list_kms_keys(key_id)
            if len(key_arn):
                self.log.info(f"Found Key Arn - {key_arn}")
                return key_arn
            else:
                self.log.error(f"Error - No Key Arn Found for {key_id}")
                return ""
        else:
            self.log.error(f"Error - No Key Id Found for AliasEndsWith | {alias_endswith}")
            return ""
    
    def get_arn(self,sid="common"):
        return self.list_kms_aliases(alias_endswith=f"/useast1/{sid}/0/kek")

class s3(object):
    def __init__(self,payload):
        self.payload = payload
        self.log = Log(name="S3")
        self.client = boto3.client('s3')
        if "region_name" in list(payload.keys()):
            self.region_name = payload["region_name"]
        elif "region" in list(payload.keys()):
            self.region_name = payload["region"]
        else:
            self.region_name = "us-east-1"
        self.kms_arn = ""
        self.bucket_name = ""
        if "s3" in list(self.payload.keys()):
            self.kms_arn = self.payload["s3"].get("kms_arn")
            self.bucket_name = self.payload["s3"].get("bucket","")
        if len(self.kms_arn) == 0:
            self.kms_arn = kms().get_arn(sid="s3")
        if len(self.bucket_name) == 0:
            self.bucket_name = self.payload["s3"].get("bucket_name","")
        else:
            for b in ["bucket","bucket_name"]:
                if b in list(self.payload.keys()):
                    bname = self.payload.get("bucket","")
                    if len(bname):
                        if isinstance(bname,str):
                            self.bucket_name = bname 
                            break
    def list_buckets(self,**kwargs):
        log = base.Log(name="ListBuckets")
        bucket_name = kwargs.get("bucket_name","")
        # Check if bucket already exists 
        brsp = self.client.list_buckets()
        bucket_list = [bucket['Name'] for bucket in brsp['Buckets']]
        for bc in bucket_list:
            if bc.lower() == bucket_name.lower():
                bucket_exists = True 
                bucket_name = bc 
                break 
        if bucket_exists:
            process_request = False 
            log.info(f"Bucket Already Exists | Not Creating | Name: {bucket_name}")

    def search_params(self,name,kdict,is_required=True):
        log = base.Log(name="SearchParams")
        if not isinstance(name,list):
            name = [name]
        found_value = False
        for nm in name:
            returned_value,found_item = helpers().dict_search(name=nm,var_dict=kdict,return_status=True)
            if found_item == False:
                returned_value,found_item = helpers().dict_search(name=nm,var_dict=self.payload,return_status=True)
                if found_item == False:
                    returned_value,found_item = helpers().dict_search(name=nm,var_dict=self.payload.get("s3",{}),return_status=True)
                    if found_item == True:
                        found_value=True
                        break
                else:
                    found_value=True
                    break 
            else:
                found_value=True
                break 
        if found_value == False: 
            if is_required:
                log.error(f"'{name}' not found | please include in parameters")
        return returned_value,found_item

    def put_tags(self,**kwargs):
        log = base.Log(name="S3TagBucket")
        process_request = True
        # Check for bucket name
        bucket_name,found_bucket = self.search_params(name="bucketname",kdict=kwargs)
        if found_bucket == False:
            process_request = False
        # check for tags 
        tags,tags_found = self.search_params(name=["tags"],kdict=kwargs)
        if tags_found:
            tags = helpers().tag_check(tags=tags)
        else:
            process_request = False
        if process_request:
            tag_rsp = self.client.put_bucket_tagging(
                Bucket=bucket_name,
                Tagging={
                    'TagSet':tags
                }
            )

    def list_objects(self,bucket_name,**kwargs):
        log = base.Log(name="ListBucketObjects")
        rsp = {}
        get_key = kwargs.get("return_key","")
        print_response = kwargs.get("print_response",False)
        rsp = self.client.list_objects_v2(Bucket=bucket_name)
        if print_response:
            print(json.dumps(rsp,indent=4,default=str))
        if len(get_key):
            if get_key in list(rsp.keys()):
                rsp = rsp[get_key]
            else:
                if get_key.lower() == "contents":
                    log.warning(f"Bucket '{bucket_name}' Is Empty | returned_keys: {list(rsp.keys())}")
                    rsp = {}
                else:
                    log.error(f"Key Not Found in Resposne | return_key: {get_key} | returned_keys: {list(rsp.keys())}")

        return rsp 

    # def get_object(self,bucket_name,bucket_key,**kwargs):
    #     try:
    #         dtype = kwargs.get("dtype","")
    #         rtype = kwargs.get("rtype","df")
    #         if len(dtype) == 0:
    #             dtype = bucket_key.split(".")[-1].lower().strip()
    #         resp = self.client.get_object(Bucket=bucket_name, Key=bucket_key)
    #         if "Body" in list(resp.keys()):
    #             if dtype.lower() == "csv":
    #                 df = pd.read_csv(resp["Body"])
    #             elif dtype.lower() == "json":
    #                 jbody = resp["Body"].read().decode('utf-8')
    #                 jbody = json.loads(jbody)
    #                 if rtype.lower() == "json":
    #                     df = jbody 
    #                 else:
    #                     df = pd.read_json(resp["Body"])
    #             elif dtype.lower() == "gz":
    #                 df = pd.read_json(resp["Body"],lines=True,compression='gzip')
    #             elif dtype.lower() == "parquet":
    #                 df = pd.read_parquet(io.BytesIO(resp['Body'].read()), engine='pyarrow')
    #             else:
    #                 return resp["Body"]
    #             self.log.info(f'Successfully loaded {bucket_name}/{bucket_key} into DataFrame')
    #             return df,True
    #         else:
    #             self.log.error(f'Failed Getting Report {bucket_name}/{bucket_key}')
    #             return pd.DataFrame(),False
    #     except Exception:
    #         self.log.error(f'Global Failure Getting S3 Report | {bucket_name}/{bucket_key} | {traceback.format_exc()}')
    #         return pd.DataFrame(),False

    def get_bucket_attribs(self,config={}):
        vconf = {} 
        fndlist = []
        notfndlist = []
        for v in ["bucket_name","bucket_key","upload_type"]:
            fk = False
            if config:
                if v in list(config.keys()):
                    if len(config[v]):
                        fndlist.append(v)
                        vconf[v] = config[v]
            if v not in fndlist:
                if v in list(self.payload["s3"].keys()):
                    if len(self.payload["s3"][v]):
                        fndlist.append(v)
                        vconf[v] = self.payload["s3"][v]
            if v not in fndlist:
                self.log.error(f"[GetBucketAttrib] Key Not Found Error | Key: {v} | Must be in config or payload['s3'] | Config: {config} | Payload: {self.payload['s3']}")
                notfndlist.append(v)
        if len(notfndlist):
            self.log.error(f"[GetBucketAttrib] Items not found in config or payload | ItemsMissingCount: {len(notfndlist)} | ItemsMissing: {notfndlist}")
            return False, "", "", ""
        else:
            return True, vconf["bucket_name"], vconf["bucket_key"], vconf["upload_type"]

    def upload_df(self,df,config={}):
        try:
            found_keys,bucket_name,bucket_key,upload_type = self.get_bucket_attribs(config)
            if found_keys:
                self.log.info(f"Uploading {bucket_key} to {bucket_name}")
                found_buffer = True
                if upload_type.lower() == "csv":
                    self.log.info(f"Upload Type Found | {upload_type}")
                    with io.StringIO() as file_buffer:
                        df.to_csv(file_buffer, index=False)
                        self.upload_actions(bucket_key,bucket_name,file_buffer)
                elif upload_type.lower() == "parquet":
                    #["snappy","gzip","brotli",None] 
                    # Default: snappy 
                    # None: No compression applied
                    comp_type = "snappy"
                    if "comp_type" in list(config.keys()):
                        if config["comp_type"]:
                            comp_type = config["comp_type"]
                    else:
                        dtype = bucket_key.split(".")[-1]
                        if dtype:
                            if dtype.lower() == "gzip":
                                comp_type = "gzip"
                            elif dtype.lower() == "brotli":
                                comp_type = "brotli"
                            else:
                                comp_type = "snappy"
                    self.log.info(f"Upload Type Found | Type: {upload_type} | CompressionType: {comp_type}")
                    with io.BytesIO() as file_buffer:
                        df.to_parquet(file_buffer,compression=comp_type,index=False)
                        self.upload_actions(bucket_key,bucket_name,file_buffer)
                else:
                    found_buffer = False 
                    self.log.error(f"Buffer Not Found | upload_type: {upload_type}")
            else:
                self.log.error(f"Failed to Find Bucket Attributes | FoundKeys: {found_keys}")
        except Exception:
            self.log.error(f"Error Uploading - {traceback.format_exc()}")

    def upload_actions(self,bucket_key,bucket_name,file_buffer,**kwargs):
        try:
            data_type = kwargs.get("data_type","df")
            if data_type.lower() == "json":
                response = self.client.put_object(
                    ACL='private',
                    Body=file_buffer,
                    Bucket=bucket_name,
                    ContentType='application/json',
                    Key=bucket_key,
                    ServerSideEncryption='aws:kms',
                    SSEKMSKeyId=self.kms_arn
                )
            else:
                response = self.client.put_object(
                    ACL='private',
                    Body=file_buffer.getvalue(),
                    Bucket=bucket_name,
                    Key=bucket_key,
                    ServerSideEncryption='aws:kms',
                    SSEKMSKeyId=self.kms_arn
                )
            status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status == 200:
                self.log.info(f"Successfully Uploaded {bucket_key} to {bucket_name}")
            else:
                self.log.error(f"Failed to Upload {bucket_key} to {bucket_name}") 
        except Exception:
            self.log.error(f"Upload Actions Failure | BucketName: {bucket_name} | BucketKey: {bucket_key} \n {traceback.format_exc()}")

    def get_bucket_tags(self,**kwargs):
        log = Log(name="S3GetBucketTags")
        bucket_name = kwargs.get("bucket_name",self.bucket_name)
        if len(bucket_name):
            rsp = self.client.get_bucket_tagging(Bucket=bucket_name)
            if 'TagSet' in list(rsp.keys()):
                return rsp['TagSet']
            else:
                keys_returned = "Not a Dictionary - No Keys"
                if isinstance(rsp,dict):
                    keys_returned = list(rsp.keys())
                log.warning(f"Key Not Found: 'TagSet' | TypeReturned: {type(rsp)} | KeysReturned: {keys_returned}")
                return rsp 
        else:
            log.error(f"Missing Variable 'bucket_name'")
            return []

    def put_object_tags(self,bucket_key,tags,**kwargs):
        log = Log(name="S3TagObject")
        bucket_name = kwargs.get("bucket_name",self.bucket_name)
        use_bucket_tags = kwargs.get("use_bucket_tags",True)
        if len(bucket_name):
            if use_bucket_tags:
                base_tag_list = self.get_bucket_tags(bucket_name=bucket_name)
            else:
                base_tag_list = []
            if isinstance(tags,dict):
                for t in list(tags.keys()):
                    base_tag_list.append({
                        "Key":t,
                        "Value":tags[t]
                    }) 
            if len(base_tag_list):
                if len(base_tag_list) > 10:
                    tag_list = []
                    for t in base_tag_list:
                        if t["Key"].lower() not in ["exp-date","iac","toc","cloud-dependency","ppmc-id"]:
                            tag_list.append(t)
                else:
                    tag_list = base_tag_list
                try:
                    rsp = self.client.put_object_tagging(
                        Bucket=bucket_name,
                        Key=bucket_key,
                        Tagging={
                            'TagSet':tag_list
                        }
                    )
                except Exception:
                    log.error(f"Failed to Tag Objects | {bucket_name} | {bucket_key}")
            else:
                log.warning(f"'tag_list' Empty no tags to update with | {bucket_name} | {bucket_key}")
        else:
            log.error(f"Missing Variable 'bucket_name' | Unable to Tag Bucket Key: {bucket_key}")

class secrets_manager(object):
    def __init__(self,payload):
        self.payload = payload
        self.region = self.payload.get("region","us-east-1")

    def get(self,secret_name):
        session = boto3.session.Session()
        secret = session.client(
            service_name='secretsmanager',
            region_name=self.region
        ).get_secret_value(
            SecretId=secret_name
        )
        return json.loads(secret['SecretString']) 

    def get_secret(self):
        for i in self.payload["get_secret_name"]:
            val = self.get(self.payload["get_secret_name"][i])
            if i.lower() != "wiz":
                if i.lower() == "github":
                    for t in val:
                        val = val[t].split(",")
                elif i.lower() == "confluence_pages":
                    val = [val["serviceName"],val["password"]]
                if i not in list(self.payload.keys()):
                    self.payload[i] = {}
                #self.payload[i]["meta"] = val
                self.payload[i] = val
            else:
                for i in list(val.keys()):
                    self.payload[i] =  val[i]

        return self.payload

class ssm(object):
    def __init__(self,param_value={}):
        self.cli = boto3.client('ssm') 
        self.log = Log(name='sts')
        self.param_value = param_value

    def put(self,param_name,param_value):
        try:
            if not isinstance(param_value,str):
                param_value = str(param_value)
            self.cli.put_parameter(Name=param_name,Value=param_value,Type="String",Overwrite=True)
            self.log.info(f"Successfully Created Parameter | {param_name}")
        except Exception:
            self.log.error(f"Failed to create parameter | {traceback.format_exc()}")

    def get(self,param_name):
        try:
            rsp = self.cli.get_parameter(Name=param_name)
            print(type(rsp['Parameter']['Value']))
            rsp = ast.literal_eval(rsp['Parameter']['Value'])
            if self.param_value:
                param_key = list(self.param_value.keys())[0]
                self.log.info(f"Found {param_name} | Value: {rsp[param_key]} | NewValue: {param_dict[param_key]}")
                return True if rsp[param_key] == param_dict[param_key] else False
            else:
                return rsp
        except ClientError as e:
            if e.response['Error']['Code'] == 'ParameterNotFound':
                self.log.warning(f"[SSM] ParameterNotFound [{param_name}] - Creating and updating parameter")
            return False

    def list_params(self):
        rsp = self.cli.describe_parameters()
        print(rsp)

class sts(object):
    def __init__(self,payload={}):
        self.cli = boto3.client('sts') 
        self.log = Log(name='sts')
        self.payload = payload 
        self.is_local = False
        if "is_local" in list(self.payload.keys()):
            if isinstance(self.payload["is_local"],bool):
                self.is_local = self.payload["is_local"]

    def get_acct_id(self):
        rsp = self.cli.get_caller_identity()
        account_id = ""
        if rsp:
            if 'Account' in list(rsp.keys()):
                account_id = rsp["Account"]
        if account_id:
            self.log.info(f"Found Account ID | {account_id}")
        else:
            self.log.error(f"Failed to Find Account ID")
        return account_id

    def assume_role(self,role,account_id=""):
        if self.is_local:
            self.log.info(f"Running Local | Getting from aws config file")
            creds = configparser.RawConfigParser()
            creds.read(self.payload["aws"]["config_file"])
            creds = creds.__dict__['_sections']['default']
            return creds
        else:
            self.log.info(f"Running Codebuild | Assuming Role to get creds")
            if not account_id:
                account_id = self.payload["account_id"] if "account_id" in list(self.payload.keys()) else self.get_acct_id()
            role = 'arn:aws:iam::' + account_id + ':role/' + role
            self.log.info(f"Attempt Assume Role | Role: {role}")
            try:
                rsp = self.cli.assume_role(
                    RoleArn=role,
                    RoleSessionName="PipelineRole")
                return {
                    'aws_access_key_id': rsp['Credentials']['AccessKeyId'],
                    'aws_secret_access_key': rsp['Credentials']['SecretAccessKey'],
                    'aws_session_token': rsp['Credentials']['SessionToken'],
                    'AssumedRoleId': rsp['AssumedRoleUser']['AssumedRoleId'],
                    'Role_arn': rsp['AssumedRoleUser']['Arn']
                }
            except Exception:
                self.log.error(f'Assume Role Failed | {traceback.format_exc()}')
                return {}