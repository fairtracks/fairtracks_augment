import glob
import os
from functools import partial

import httpretty
import pytest

from pathlib import Path

from fairtracks_augment.config import Config, SCHEMA_DIR
from fairtracks_augment.schemas import SchemaHelper
from tests.common import FileId, TestFileCache, get_test_dir, stage_file_and_get_url


@pytest.fixture
def get_new_schema_helper(tmp_path):
    def _get_new_schema_helper():
        return SchemaHelper(config=Config(user_data_dir=tmp_path.resolve()))

    return _get_new_schema_helper


def _get_schema_version_url(schema_id):
    ASSERT_SCHEMA_URL = 'https://raw.githubusercontent.com/fairtracks/fairtracks_standard/v1/{}/' \
                        'json/schema/{}'
    return ASSERT_SCHEMA_URL.format(schema_id.version, schema_id.filename)


def _get_schema_testdata_path(test_dir, id):
    return os.path.join(test_dir, 'data', 'fairtracks', id.version, 'schema',
                        id.filename if id.filename else '')


def _get_schema_mock_url(schema_id):
    return 'https://localhost/{}/{}'.format(schema_id.version, schema_id.filename)


def _get_all_schema_mock_urls(schema_id_list):
    return [_get_schema_mock_url(_) for _ in schema_id_list]


@pytest.fixture
def stage_schema_file_and_get_url(stage_file_and_get_url):
    schema_file_cache = TestFileCache(_get_schema_testdata_path)
    return partial(stage_file_and_get_url,
                   file_cache=schema_file_cache,
                   get_mock_url_func=_get_schema_mock_url)


def assert_helper_info_for_schema_id(helper, schema_id):
    assert helper.get_version_url_for_schema(_get_schema_mock_url(schema_id)) == \
           _get_schema_version_url(schema_id)


def assert_helper_info_for_all_schema_ids(helper, schema_id_list):
    assert helper.all_file_urls() == _get_all_schema_mock_urls(schema_id_list)
    for schema_id in schema_id_list:
        assert_helper_info_for_schema_id(helper, schema_id)


@pytest.fixture
def add_schema_files_and_get_version_urls(get_test_dir, stage_schema_file_and_get_url,
                                          get_new_schema_helper):
    def _add_schema_files_and_get_version_urls(version, from_url):
        helper = get_new_schema_helper()
        all_schemas_path = _get_schema_testdata_path(get_test_dir(), FileId("*", version))
        schema_version_urls = []

        for filename in glob.glob(all_schemas_path):
            schema_path = os.path.join(all_schemas_path, filename)
            file_id = FileId(schema_path, version)
            schema_version_urls.append(_get_schema_version_url(file_id))

            if from_url:
                schema_mock_url = stage_schema_file_and_get_url(file_id)
                helper.install_file_from_url(schema_mock_url)
            else:
                schema_mock_url = _get_schema_mock_url(file_id)
                helper.install_file_from_path(schema_mock_url, schema_path)

        return schema_version_urls

    return _add_schema_files_and_get_version_urls


def _test_add_schemas(add_schema_files_and_get_version_urls, get_new_schema_helper,
                      tmp_path, get_test_dir, from_url):
    helper = get_new_schema_helper()

    assert list(helper.all_file_urls()) == []
    assert os.path.exists(os.path.join(tmp_path.resolve(), SCHEMA_DIR))

    add_schema_files_and_get_version_urls('v1.0.2', from_url=from_url)
    schemas_path = _get_schema_testdata_path(get_test_dir(), FileId("*", 'v1.0.2'))
    all_schemas_ids = (FileId(_, 'v1.0.2') for _ in glob.glob(schemas_path))
    assert_helper_info_for_all_schema_ids(helper, all_schemas_ids)


@httpretty.activate
def test_add_schemas_from_url(add_schema_files_and_get_version_urls, get_new_schema_helper,
                              tmp_path, get_test_dir):
    _test_add_schemas(add_schema_files_and_get_version_urls, get_new_schema_helper,
                      tmp_path, get_test_dir, from_url=True)


@httpretty.activate
def test_add_schemas_from_file(add_schema_files_and_get_version_urls, get_new_schema_helper,
                               tmp_path, get_test_dir):
    _test_add_schemas(add_schema_files_and_get_version_urls, get_new_schema_helper,
                      tmp_path, get_test_dir, from_url=False)
