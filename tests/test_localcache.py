from functools import partial

import httpretty
import os
import pytest
import requests
import time

from collections import namedtuple
from http import HTTPStatus

from fairtracks_augment.common import ensure_dir_exists
from fairtracks_augment.config import Config
from fairtracks_augment.localcache import LocalCache
from tests.common import FileId, TestFileCache, get_test_dir, stage_file_and_get_url


@pytest.fixture
def get_new_localcache(tmp_path):
    def _get_new_localcache():
        user_data_dir = tmp_path.resolve()
        filecache_dir_path = Config(user_data_dir=user_data_dir).filecache_dir_path
        data_dir_path = os.path.join(user_data_dir, 'data')
        ensure_dir_exists(data_dir_path)
        return LocalCache(filecache_dir_path=filecache_dir_path, data_dir_path=data_dir_path)

    return _get_new_localcache


TextMetadata = namedtuple('TextMetadata', ('first_line', 'etag'))

TEXT_METADATA_FOR_ASSERTS = {
    FileId('to_be_or_not_to_be.txt', 'old'):
        TextMetadata("To be, or not to be, that is the question,",
                     'fe08f05b578985c90e68bf6ebaa206ee'),
    FileId('to_be_or_not_to_be.txt', 'new'):
        TextMetadata("To be, or not to be, that is the Question:",
                     '554c7e6f12e10467828ec24adc6f4373'),
    FileId('to_be_or_not_to_be.txt', 'maybe_newer'):
        TextMetadata("To be, or not to be, that is the Question:",
                     '554c7e6f12e10467828ec24adc6f4373'),
    FileId('all_the_worlds_a_stage.txt', 'old'):
        TextMetadata("All the world's a stage,",
                     '584a0dfc09fbb9077acd42fce61cf74e')
}


def _assert_data_for_file_id(cache, file_id):
    file_stream = cache.get_file_stream(_get_mock_url(file_id))
    assert file_stream.readline().rstrip() == \
           TEXT_METADATA_FOR_ASSERTS[file_id].first_line


def _assert_metadata_for_file_id(cache, file_id):
    assert cache.get_etag_for_file(_get_mock_url(file_id)) == \
           TEXT_METADATA_FOR_ASSERTS[file_id].etag


def _assert_data_and_metadata_for_all_file_ids(cache, file_id_list, ignore_metadata=False):
    assert cache.all_file_urls() == _get_all_mock_urls(file_id_list)
    for file_id in file_id_list:
        _assert_data_for_file_id(cache, file_id)
        if not ignore_metadata:
            _assert_metadata_for_file_id(cache, file_id)


def _get_testdata_path(test_dir, id):
    return os.path.join(test_dir, 'data', 'text', id.version, id.filename)


def _get_mock_url(id):
    return 'https://localhost/{}'.format(id.filename)


def _get_all_mock_urls(id_list):
    return [_get_mock_url(_) for _ in id_list]


@pytest.fixture
def stage_text_file_and_get_url(stage_file_and_get_url):
    test_file_cache = TestFileCache(_get_testdata_path)
    return partial(stage_file_and_get_url,
                   file_cache=test_file_cache,
                   get_mock_url_func=_get_mock_url)


@pytest.fixture
def install_old_files(stage_text_file_and_get_url, get_new_localcache):
    def _install_old_files():
        file_cache = get_new_localcache()
        first_id_old = FileId('to_be_or_not_to_be.txt', 'old')
        second_id_old = FileId('all_the_worlds_a_stage.txt', 'old')

        file_cache.install_file_from_url(stage_text_file_and_get_url(first_id_old))
        file_cache.install_file_from_url(stage_text_file_and_get_url(second_id_old))
        file_cache.store()

        return [first_id_old, second_id_old]

    return _install_old_files


@httpretty.activate
def test_install_file(stage_text_file_and_get_url, get_new_localcache, tmp_path, get_test_dir):
    cache = get_new_localcache()

    assert list(cache.all_file_urls()) == []
    assert os.path.exists(os.path.join(tmp_path.resolve(), 'data'))

    first_id_old = FileId('to_be_or_not_to_be.txt', 'old')
    cache.install_file_from_url(stage_text_file_and_get_url(first_id_old))
    _assert_data_and_metadata_for_all_file_ids(cache, [first_id_old])

    second_id_old = FileId('all_the_worlds_a_stage.txt', 'old')
    url = _get_mock_url(second_id_old)
    file_path = _get_testdata_path(get_test_dir(), second_id_old)
    cache.install_file_from_path(url, file_path)
    _assert_data_and_metadata_for_all_file_ids(cache, [first_id_old, second_id_old],
                                               ignore_metadata=True)


@httpretty.activate
def test_load_from_storage(install_old_files, get_new_localcache):
    owl_id_list_old = install_old_files()
    cache = get_new_localcache()

    _assert_data_and_metadata_for_all_file_ids(cache, owl_id_list_old)


@httpretty.activate
def test_delete_file(install_old_files, get_new_localcache):
    first_id_old, second_id_old = install_old_files()
    cache = get_new_localcache()

    cache.delete_file(_get_mock_url(first_id_old))
    _assert_data_and_metadata_for_all_file_ids(cache, [second_id_old])

    new_cache = get_new_localcache()
    _assert_data_and_metadata_for_all_file_ids(new_cache, [second_id_old])


@httpretty.activate
def test_delete_all_files(install_old_files, get_new_localcache):
    install_old_files()
    cache = get_new_localcache()

    cache.delete_all_files()
    _assert_data_and_metadata_for_all_file_ids(cache, [])

    new_cache = get_new_localcache()
    _assert_data_and_metadata_for_all_file_ids(new_cache, [])


@httpretty.activate
def test_update_file(install_old_files, get_new_localcache, stage_text_file_and_get_url):
    first_id_old, second_id_old = install_old_files()
    cache = get_new_localcache()

    #
    # Test update with same URL but different ETag
    #

    first_id_new = FileId('to_be_or_not_to_be.txt', 'new')
    omo_new_url = stage_text_file_and_get_url(first_id_new)
    updated = cache.update_file(omo_new_url)

    _assert_data_and_metadata_for_all_file_ids(cache, [second_id_old, first_id_new])
    assert updated

    #
    # Test update with same URL and same ETag
    #

    first_id_maybe_newer = FileId('to_be_or_not_to_be.txt', 'maybe_newer')
    omo_maybe_newer_url = stage_text_file_and_get_url(first_id_maybe_newer)
    updated = cache.update_file(omo_maybe_newer_url)

    _assert_data_and_metadata_for_all_file_ids(cache, [second_id_old, first_id_maybe_newer])
    assert not updated


@httpretty.activate
def test_install_retries(get_new_localcache, stage_text_file_and_get_url):
    cache = get_new_localcache()
    first_id_old = FileId('to_be_or_not_to_be.txt', 'old')
    omo_old_url = stage_text_file_and_get_url(first_id_old, respond_status=HTTPStatus.TOO_MANY_REQUESTS)
    cache.install_file_from_url(omo_old_url)


@httpretty.activate
def test_cached_update(get_new_localcache, stage_text_file_and_get_url):
    cache = get_new_localcache()
    first_id_old = FileId('to_be_or_not_to_be.txt', 'old')
    omo_old_url = stage_text_file_and_get_url(first_id_old, max_age=1, respond_status=HTTPStatus.OK)
    cache.install_file_from_url(omo_old_url)

    #
    # Test that cache is being used, assuming the new request is within the max_age range (1 sec)
    #

    omo_old_url = stage_text_file_and_get_url(first_id_old, respond_status=HTTPStatus.NOT_FOUND)
    updated = cache.update_file(omo_old_url)

    _assert_data_and_metadata_for_all_file_ids(cache, [first_id_old])
    assert not updated

    #
    # Test that cache is not used after expiration
    #

    time.sleep(1.2)

    with pytest.raises(requests.exceptions.HTTPError):
        cache.update_file(omo_old_url)

    #
    # Test standard update with new version of owl file
    #

    first_id_new = FileId('to_be_or_not_to_be.txt', 'new')
    omo_new_url = stage_text_file_and_get_url(first_id_new, max_age=0, respond_status=HTTPStatus.OK)
    updated = cache.update_file(omo_new_url)

    _assert_data_and_metadata_for_all_file_ids(cache, [first_id_new])
    assert updated

    #
    # Test that ETag verification request is sent to mock server that responds with "Not Modified"
    #

    omo_new_url = stage_text_file_and_get_url(first_id_new, respond_status=HTTPStatus.NOT_MODIFIED)
    updated = cache.update_file(omo_new_url)

    _assert_data_and_metadata_for_all_file_ids(cache, [first_id_new])
    assert not updated
