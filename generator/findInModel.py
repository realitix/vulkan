# a simple python script to find an element in 
# the json file, which represents the Vulkan model

# Usage: python findInModel.py search_term

import sys
import json
with open("model.json", "r") as f:
    modelDict = json.loads(f.read())

def find_path(indict, path, search_term):
    for k, v in indict.items():
        this_path = path + "->" + k
        #print("trying " + this_path)
        if search_term in k:
            print("FOUND " + this_path)
            #yield patr
        elif type(v) is dict:
            #print("recursing")
            find_path(v, this_path, search_term)

print(type(modelDict))
find_path(modelDict, "root", sys.argv[1])
