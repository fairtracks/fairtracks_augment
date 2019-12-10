import os
from os.path import dirname

from Constants import SCHEMA_FOLDER_PATH, ONTOLOGY_FOLDER_PATH


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


def makeStrPathFromList(path, category):
    return '->'.join([category] + path)


def getSchemaFilePath(category):
        path = os.path.join(SCHEMA_FOLDER_PATH, category + '.json')
        if not os.path.exists(dirname(path)):
            os.makedirs(os.path.dirname(path))

        return path


def getOntologyFilePath(url):
    path = os.path.join(ONTOLOGY_FOLDER_PATH, getFilenameFromUrl(url))
    if not os.path.exists(dirname(path)):
        os.makedirs(os.path.dirname(path))

    return path
