import os 
import json
import requests
import traceback 

from tf_api import base_log 
from tf_api import data_filter

class TfeWorkspace(object):
    def __init__(self,payload):
        self.payload = payload
        if "api_url" not in list(self.payload['tfe'].keys()):
            self.payload['tfe']['api_url'] = 'https://tfe.cguser.capgroup.com/api/v2/'
        self.debug_mode = False
        if "debug_mode" in list(self.payload.keys()):
            if isinstance(self.payload["debug_mode"], bool):
                self.debug_mode = self.payload["debug_mode"]
        # If debug mode is enabled - confirm debug_report directory is created else create
        self.debug_dir = "debug_reports"
        if self.debug_mode:
            if self.debug_dir not in os.listdir():
                os.mkdir(self.debug_dir)

    def url_encoding(self,url):
        encoding_dict = {
            "[":"%5B",
            "]":"%5D"
        }
        for k in list(encoding_dict.keys()):
            url = url.replace(k,encoding_dict[k])

        return url 

    def connect(self,api_call):
        log = base_log.Log(name="TFConnector")
        debug_mode = False 
        expect_empty_return = False
        print_response = api_call.get("print_response",False)
        if "expect_empty_return" in list(api_call.keys()):
            if isinstance(api_call["expect_empty_return"], bool):
                expect_empty_return = api_call["expect_empty_return"]
        if "params" in list(api_call.keys()):
            if isinstance(api_call["params"],dict):
                params = json.dumps(api_call["params"])
            else:
                params = api_call["params"]
        elif "upload_file" in list(api_call.keys()):
            expect_empty_return = True
            if not isinstance(api_call["upload_file"], bytes):
                params = open(api_call["upload_file"], 'rb').read()
            else:
                params = api_call["upload_file"]
        else:
            params = ""

        headers = {"Authorization":f"Bearer {self.payload['tfe']['conn']}","Content-Type":"application/vnd.api+json"}
        if "headers" in list(api_call.keys()):
            if isinstance(api_call["headers"],dict):
                headers = api_call["headers"]
                add_auth = api_call.get("add_auth",False)
                if add_auth:
                    if "Authorization" not in list(api_call["headers"].keys()):
                        headers = {**{"Authorization":f"Bearer {self.payload['tfe']['conn']}"},**headers}
            else:
                log.warning(f"Header must be a dict using default header | SuppliedHeaderType: {type(api_call['headers'])}")
            
 
        if "url" in list(api_call.keys()):
            url = api_call["url"]
        elif api_call["type"].lower() == "get":
            encoded_url = self.url_encoding(url=api_call["endpoint"])
            url = self.payload["tfe"]["api_url"] + encoded_url
        else:
            url = self.payload["tfe"]["api_url"] + api_call["endpoint"]
        # log.debug(f"URL: {url}")

        #verify_cert = self.payload["tfe"].get("verify",False)
        verify_cert = False

        if api_call["type"].lower() == "get":
            resp = requests.get(
                url = url,
                headers=headers,
                data=params,
                verify=verify_cert
            )
        elif api_call["type"].lower() == "post":
            resp = requests.post(
                url = url,
                headers=headers,
                data=params,
                verify=verify_cert
            )
        elif api_call["type"].lower() == "put":
            resp = requests.put(
                url = url,
                headers=headers,
                data=params,
                verify=verify_cert
            )
        elif api_call["type"].lower() in ["update","patch"]:
            resp = requests.patch(
                url = url,
                headers=headers,
                data=params,
                verify=verify_cert
            )
        elif api_call["type"].lower() in ["delete","remove"]:
            expect_empty_return = True
            resp = requests.delete(
                url = url,
                headers=headers,
                data=params,
                verify=verify_cert
            )
        else:
            raise Exception(f"ERROR - No HTTP Request Method Found for {api_call['type']}")

        self.error_check(resp,url)
        if expect_empty_return == True:
            return None 
        else:
            try:
                jresp = resp.json()
                if self.debug_mode:
                    ep = api_call.get("endpoint","no_endpoint_var_found")
                    if ep != "no_endpoint_var_found":
                        ep = ep.replace("/","_")
                    with open(f"{self.debug_dir}/{ep}.json","w") as fout:
                        fout.write(json.dumps(jresp)) 
                        fout.close()
                if print_response:
                    print(json.dumps(jresp,indent=4,default=str))
                return jresp
            except Exception as e:
                log.error(f"Failed to process request | {traceback.format_exc()}")
                return resp.text

    def error_check(self,resp,url):
        if resp.status_code == 401:
            raise Exception(f"ERROR: {resp.status_code}  Auth Failed - {resp.text} | {url}")
        elif 400 <= resp.status_code < 500:
            raise Exception(f"ERROR: {resp.status_code} Query to Terraform Failed - {resp.text} | {url}")
        elif 500 <= resp.status_code < 600:
            raise Exception(f"ERROR: {resp.status_code} Terraform Interanl Server Error - {resp.text} | {url}")



