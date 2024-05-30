import os 
import sys 
import json 
import traceback 

from logger import base 

def str_check(line,values):
    if isinstance(values,str):
        values = [values]
    found_values = False 
    for v in values:
        if line.lower().startswith(v):
            found_values = True 
            break 
    return found_values

def to_string(**kwargs):
    utils_path = kwargs.get("utils_path","../../../policies/helpers/common.utils.rego")
    lines_to_check = kwargs.get("lines_to_check",10)
    utils_str = ""
    with open(utils_path) as utils:
        line_counter = 0
        for uline in utils:
            line_counter+=1
            if line_counter < int(lines_to_check):
                # print(uline)
                skip_values = ["package ", "import "]
                skip_value = str_check(uline,skip_values)
                if skip_value == False:
                    utils_str+=uline
            else:
                utils_str+=uline
    # Add Header 
    dash_ctr = "--"*30
    header = f"\n#{dash_ctr}\n#Copied From Common Utils\n#{dash_ctr}\n"
    utils_str = header + utils_str
    return utils_str