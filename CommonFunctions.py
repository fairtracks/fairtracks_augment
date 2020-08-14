from copy import copy

import os
from os.path import dirname
import json
import urllib.request

from Constants import SCHEMA_FOLDER_PATH, ONTOLOGY_FOLDER_PATH


def getFromDict(dataDict, pathList):
    for k in pathList:
        dataDict = dataDict[k]
    return dataDict


def getPathsToElement(elName, url=None, data=None, path=[]):
    assert (url is not None or data is not None)

    if data is None:
        data = json.load(urllib.request.urlopen(url))

    if isinstance(data, dict):
        for key, val in data.items():
            newPath = copy(path)
            newUrl = url

            if key == '$ref':
                newUrl = '/'.join([url.rsplit('/', 1)[0], val])
                data = None
            else:
                newPath.append(key)
                data = val

            if key == elName:
                yield url, newPath, val
            else:
                for _ in getPathsToElement(elName, newUrl, data, newPath):
                    yield _
    elif isinstance(data, list):
        for i, item in enumerate(data):
            for _ in getPathsToElement(elName, url, item, path + [i]):
                yield _

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
