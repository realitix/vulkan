import sys
import json
with open("model.json", "r") as f:
    modelDict = json.loads(f.read())

def findPath(indict, path, searchTerm):
    for k, v in indict.items():
        thispath = path + "->" + k
        #print("trying " + thispath)
        if searchTerm in k:
            print("FOUND " + thispath)
            #yield patr
        elif type(v) is dict:
            #print("recursing")
            findPath(v, thispath, searchTerm)

print(type(modelDict))
findPath(modelDict, "root", sys.argv[1])
