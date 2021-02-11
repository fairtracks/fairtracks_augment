from collections.abc import Iterable
from copy import copy

import json
import urllib.request

import requests
import urllib3
from cachecontrol import CacheControl, CacheControlAdapter
from cachecontrol.caches import FileCache

from fairtracks_augment.constants import NUM_DOWNLOAD_RETRIES, BACKOFF_FACTOR, REQUEST_TIMEOUT


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


def http_get_request(filecache_dir_path, url, callback_if_ok, require_etag=False):
    try:
        retry_strategy = urllib3.Retry(
            total=NUM_DOWNLOAD_RETRIES,
            read=NUM_DOWNLOAD_RETRIES,
            connect=NUM_DOWNLOAD_RETRIES,
            status_forcelist=(429, 500, 502, 503, 504),
            backoff_factor=BACKOFF_FACTOR
        )

        def _create_cache_control_adapter(*args, **kwargs):
            return CacheControlAdapter(*args, max_retries=retry_strategy, **kwargs)

        session = requests.Session()
        session = CacheControl(session, cache=FileCache(filecache_dir_path),
                               adapter_class=_create_cache_control_adapter)

        with session.get(url, stream=True, timeout=REQUEST_TIMEOUT) as response:
            response.raise_for_status()

            if require_etag and 'etag' not in response.headers:
                raise NotImplementedError('URL HTTP response without '
                                          '"ETag" header is not supported')

            return callback_if_ok(response)
    except requests.exceptions.RequestException:
        raise


class ArgBasedSingleton(type):
    _instances = dict()

    def __call__(cls, **kwargs):
        args_as_tuple = tuple(kwargs.items())
        if args_as_tuple not in cls._instances:
            cls._instances[args_as_tuple] = super(ArgBasedSingleton, cls).__call__(**kwargs)
        return cls._instances[args_as_tuple]
