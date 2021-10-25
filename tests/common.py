import hashlib

import pytest
from collections import namedtuple
from email.utils import formatdate
from http import HTTPStatus
from pathlib import Path

import httpretty
from httpretty import HTTPretty, Response


FileId = namedtuple('FileId', ('filename', 'version'))

CachedFile = namedtuple('CachedFile', ('path', 'contents', 'md5'))


class TestFileCache:
    def __init__(self, get_testdata_path_func):
        self._file_cache = dict()
        self._get_testdata_path_func = get_testdata_path_func

    def load_file(self, test_dir, file_id):
        if file_id not in self._file_cache:
            path = self._get_testdata_path_func(test_dir, file_id)
            contents = open(path).read()
            md5 = hashlib.md5(contents.encode('utf8')).hexdigest()
            self._file_cache[file_id] = CachedFile(path, contents, md5)
        return self._file_cache[file_id]


def register_mock_uri(max_age, uri, contents, respond_status, etag=None):
    headers = dict()
    if etag:
        headers['ETag'] = etag
    if max_age is not None:
        headers['Cache-Control'] = 'max-age={}'.format(max_age)
        headers['Date'] = formatdate(usegmt=True)
    responses = list()

    def _add_response(body, status=respond_status):
        responses.append(Response(body=body, adding_headers=headers, status=status.value))

    if respond_status == HTTPStatus.OK:
        _add_response(contents)

    elif respond_status == HTTPStatus.TOO_MANY_REQUESTS:
        _add_response('', status=HTTPStatus.TOO_MANY_REQUESTS)
        _add_response(contents, status=HTTPStatus.OK)

    elif respond_status == HTTPStatus.NOT_MODIFIED:
        def _empty_assert_if_none_match(http_req, uri, response_headers):
            assert 'If-None-Match' in http_req.headers
            assert http_req.headers['If-None-Match'] == etag
            return [respond_status.value, response_headers, '']

        _add_response(_empty_assert_if_none_match)

    else:
        _add_response('')

    httpretty.reset()
    httpretty.register_uri(
        HTTPretty.GET,
        uri,
        responses=responses
    )


@pytest.fixture
def stage_file_and_get_url(request):

    def _stage_file_and_get_url(file_id, file_cache=None, get_mock_url_func=None,
                                max_age=0, respond_status=HTTPStatus.OK):
        assert file_cache is not None
        assert get_mock_url_func is not None

        test_dir = Path(request.module.__file__).parent
        cached_file = file_cache.load_file(test_dir, file_id)
        url = get_mock_url_func(file_id)

        register_mock_uri(max_age, url, cached_file.contents, respond_status, etag=cached_file.md5)

        return url

    return _stage_file_and_get_url
