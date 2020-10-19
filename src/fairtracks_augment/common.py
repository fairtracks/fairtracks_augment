from collections.abc import Iterable
from copy import copy

import json
import urllib.request


def get_paths_to_element(el_name, url=None, data=None, path=[], schemas={}):
    assert (url is not None or data is not None)

    if data is None:
        print(url)
        data = json.load(urllib.request.urlopen(url))
        schema_fn = url.split('/')[-1]
        schemas[schema_fn] = data

    if isinstance(data, dict):
        for key, val in data.items():
            new_path = copy(path)
            new_url = url

            if key == '$ref':
                if val in schemas:
                    data = schemas[val]
                else:
                    new_url = '/'.join([url.rsplit('/', 1)[0], val])
                    data = None
            else:
                new_path.append(key)
                data = val

            if key == el_name:
                yield url, new_path, val
            else:
                for _ in get_paths_to_element(el_name, new_url, data, new_path, schemas):
                    yield _

    elif isinstance(data, Iterable):
        for i, item in enumerate(data):
            for _ in get_paths_to_element(el_name, url, item, path + [i], schemas):
                yield _


def get_filename_from_url(url):
    return url.rsplit('/', 1)[-1]


def make_str_path_from_list(path, category):
    return '->'.join([category] + path)

