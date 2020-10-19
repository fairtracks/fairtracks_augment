from collections.abc import Iterable
from copy import copy

import json
import urllib.request


def getPathsToElement(elName, url=None, data=None, path=[], schemas={}):
    assert (url is not None or data is not None)

    if data is None:
        print(url)
        data = json.load(urllib.request.urlopen(url))
        schemaFn = url.split('/')[-1]
        schemas[schemaFn] = data

    if isinstance(data, dict):
        for key, val in data.items():
            newPath = copy(path)
            newUrl = url

            if key == '$ref':
                if val in schemas:
                    data = schemas[val]
                else:
                    newUrl = '/'.join([url.rsplit('/', 1)[0], val])
                    data = None
            else:
                newPath.append(key)
                data = val

            if key == elName:
                yield url, newPath, val
            else:
                for _ in getPathsToElement(elName, newUrl, data, newPath, schemas):
                    yield _
    elif isinstance(data, Iterable):
        for i, item in enumerate(data):
            for _ in getPathsToElement(elName, url, item, path + [i], schemas):
                yield _


def getFilenameFromUrl(url):
    return url.rsplit('/', 1)[-1]


def makeStrPathFromList(path, category):
    return '->'.join([category] + path)

