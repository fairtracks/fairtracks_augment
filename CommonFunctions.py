
def getFromDict(dataDict, pathList):
    for k in pathList:
        dataDict = dataDict[k]
    return dataDict


def getPathsToElement(data, key, path=[]):
    if isinstance(data, dict):
        for k,v in data.items():
            newPath = path + [k]
            if k == key:
                yield newPath
            else:
                for el in getPathsToElement(v, key, newPath):
                    yield el
    elif isinstance(data, list):
        for i in data:
            for el in getPathsToElement(i, key, path):
                yield el


def setInDict(dataDict, pathList, value):
    getFromDict(dataDict, pathList[:-1])[pathList[-1]] = value


def getFilenameFromUrl(url):
    fn = url.rsplit('/', 1)[-1]

    return fn
