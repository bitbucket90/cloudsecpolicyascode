import sys
import json 
import traceback

from tf_api import base_log
    
def filter_engine(resp,get_items):
    log = base_log.Log(name="FilterResults")
    ret = {}
    get_item_keys = list(get_items.keys())
    try:
        for ik in get_item_keys:
            search_path = get_items[ik].split(".")
            resp_key_list = list(resp.keys())
            if len(resp_key_list) == 1:
                first_item = resp_key_list[0]
                if search_path[0] != first_item:
                    search_path.insert(0,first_item)
            holder = None 
            for sx,si in enumerate(search_path):
                if sx == 0:
                    if si in list(resp.keys()):
                        holder = resp[si]
                    else:
                        log.error(f"Failed to find root Key | {si}")
                        break 
                else:
                    if si in list(holder.keys()):
                        holder = holder[si]
                    else:
                        log.error(f"Failed to find child key | {si} | returning everything before error occurred")
            if holder:
                ret[ik] = holder 
            else:
                log.error(f"Failed to Find Search Path | {get_items[ik]}")
    except Exception:
        log.error(f"Failed to filter results | {traceback.format_exc()}")
    if ret:
        returned_keys = list(ret.keys())
        count_test = len(get_item_keys) - len(returned_keys)
        log.info(f"[CountTest] Get Item Key Count: {len(get_item_keys)} | Keys Found: {len(returned_keys)} | Found All: {True if count_test == 0 else False}")
        failed_counter = 0
        for gik in get_item_keys:
            if gik not in returned_keys:
                failed_counter+=1
                log.error(f"{failed_counter}. Failed to Find path for {gik}")
        if count_test > 0:
            log.info(f"[KeySearchTest] Returning Keys: {list(ret.keys())} | KeyCountNotFound: {failed_counter}")
        return ret 
    else:
        return {}

def filter_results(resp,get_items):
    log = base_log.Log(name="FormatSearchFilters")
    try:
        resp_data = resp.get("data",{})
        if isinstance(resp_data,dict):
            resp_attr = resp_data.get("attributes",{})
        if isinstance(get_items, str):
            if "." in get_items:
                filtered_resp = filter_engine(resp,get_items={"def_key":get_items})
                return filtered_resp.get("def_key",{})
            else:
                if get_items.lower() == "all":
                    return resp 
                elif get_items.lower() == "data":
                    return resp_data
                elif get_items in list(resp_data.keys()):
                    return resp_data[get_items]
                elif get_items in list(resp_attr.keys()):
                    return resp_attr[get_items]
                else:
                    log.error(f"[KeyNotFoundError] String Search Value found but key does not exist for | {get_items}")
                    return {} 
        elif isinstance(get_items,dict):
            log.info(f"Get Item | type: {type(get_items)}")
            if isinstance(resp_data,list):
                filtered_resp = []
                for r in resp_data:
                    tmp_resp = filter_engine(resp=r,get_items=get_items)
                    if len(tmp_resp):
                        filtered_resp.append(tmp_resp)
            else:
                filtered_resp = filter_engine(resp,get_items=get_items)
            return filtered_resp
        elif isinstance(get_items,list):
            log.info(f"Get Item | type: {type(get_items)}")
            filtered_resp = []
            filtered_dict = {}
            for ix,i in enumerate(get_items):
                if isinstance(i,dict):
                    filtered_resp.append(filter_engine(resp,get_items=i)) 
                elif isinstance(i,str):
                    if "." in i:
                        key_name = "_".join((i.split(".")))
                        run_filter = filter_engine(resp,get_items={key_name:i})
                        if run_filter: 
                            filtered_resp.append(run_filter)
                    else:
                        if i in list(resp.keys()):
                            kin = f"{i}_{ix+1}" if i in list(filtered_dict.keys()) else i
                            filtered_dict[kin]=resp[i]
                        elif i in list(resp_data.keys()):
                            kin = f"{i}_{ix+1}" if i in list(filtered_dict.keys()) else i
                            filtered_dict[kin]=resp_data[i]
                        elif i in list(resp_attr.keys()):
                            kin = f"{i}_{ix+1}" if i in list(filtered_dict.keys()) else i
                            filtered_dict[kin]=resp_attr[i]
                        else:
                            log.error(f"[KeyNotFoundError] List Search Value found but key at index {ix} does not exist for | {i}")
                            return {}
            if len(filtered_dict):
                filtered_resp.append(filtered_dict)
            if filtered_resp:
                #if len(filtered_resp) == 1:
                #    filtered_resp = filtered_resp[0]
                return filtered_resp
            else:
                return {}
    except Exception:
        log.error(f"Failed to format search filters | {traceback.format_exc()}")
        return {}