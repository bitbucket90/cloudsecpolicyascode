

def payloads(item,**kwargs):
    if item.lower() == "policy_sets":
        req_payload = {
            "data":{
                "type": "policies",
                "attributes": {
                    "name": kwargs["name"],
                    "description": kwargs.get("description",""),
                    "kind": kwargs["type"].lower(), # Sentinel or OPA
                    "enforcement-level": kwargs.get("enforcement_mode","advisory").lower()
                },
                "relationships": {
                    "policy-sets": {
                        "data":[]
                    }
                }
            }
        }
    elif item.lower() == "policy":
        #"agent-enabled": true,
        #"policy-tool-version": "0.23.0",
        #"overridable": False,
        #"policies-path": "/policy-sets/foo",
        # "vcs-repo": {
        #     "branch": "main",
        #     "identifier": "hashicorp/my-policy-sets",
        #     "ingress-submodules": false,
        #     "oauth-token-id": "ot-7Fr9d83jWsi8u23A"
        # }
        req_payload = {
            "data": {
                "type": "policy-sets",
                "attributes": {
                    "name": kwargs["name"],
                    "description": kwargs.get("description",""),
                    "global": kwargs.get("is_global",True),
                    "kind": kwargs["type"].lower(), # Sentinel or OPA
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
        return req_payload 
