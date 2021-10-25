from functools import partial

import httpretty
import os
import pytest
import requests
import time

from collections import namedtuple
from http import HTTPStatus

from fairtracks_augment.config import Config, ONTOLOGY_DIR
from fairtracks_augment.ontologies import OntologyHelper
from tests.common import FileId, TestFileCache, stage_file_and_get_url


@pytest.fixture
def get_new_ontology_helper(tmp_path):
    def _get_new_ontology_helper():
        return OntologyHelper(config=Config(user_data_dir=tmp_path.resolve()))

    return _get_new_ontology_helper


OwlInfo = namedtuple('OwlInfo', ('version_iri', 'etag'))

OWL_METADATA_FOR_ASSERTS = {
    FileId('omo.owl', 'old'):
        OwlInfo('http://purl.obolibrary.org/obo/omo/2020-05-08/omo.owl',
                '594585592bd65f374afdd8cafec151fa'),
    FileId('omo.owl', 'new'):
        OwlInfo('http://purl.obolibrary.org/obo/omo/2020-06-08/omo.owl',
                'a136b8434c8ca8b6deca03529b6f3a58'),
    FileId('omo.owl', 'maybe_newer'):
        OwlInfo('http://purl.obolibrary.org/obo/omo/2020-06-08/omo.owl',
                'a136b8434c8ca8b6deca03529b6f3a58'),
    FileId('hom.owl', 'old'):
        OwlInfo('http://purl.obolibrary.org/obo/hom/releases/2015-01-07/hom.owl',
                'd3f7a3aabf82ce1f5cfc2112875eeba9')
}


def assert_helper_info_for_owl_file_id(helper, owl_file_id):
    assert helper.get_version_iri_for_ontology(_get_owl_mock_url(owl_file_id)) == \
           OWL_METADATA_FOR_ASSERTS[owl_file_id].version_iri
    assert helper.get_etag_for_ontology(_get_owl_mock_url(owl_file_id)) == \
           OWL_METADATA_FOR_ASSERTS[owl_file_id].etag


def assert_helper_info_for_all_owl_file_ids(helper, owl_file_id_list):
    assert helper.all_ontology_urls() == _get_all_owl_mock_urls(owl_file_id_list)
    for owl_file_id in owl_file_id_list:
        assert_helper_info_for_owl_file_id(helper, owl_file_id)


def _get_owl_testdata_path(test_dir, id):
    return os.path.join(test_dir, 'data', 'owl', id.version, id.filename)


def _get_owl_mock_url(id):
    return 'https://localhost/{}'.format(id.filename)


def _get_all_owl_mock_urls(id_list):
    return [_get_owl_mock_url(_) for _ in id_list]


@pytest.fixture
def stage_owl_file_and_get_url(stage_file_and_get_url):
    owl_file_cache = TestFileCache(_get_owl_testdata_path)
    return partial(stage_file_and_get_url,
                   file_cache=owl_file_cache,
                   get_mock_url_func=_get_owl_mock_url)


@pytest.fixture
def install_old_owl_files(stage_owl_file_and_get_url, get_new_ontology_helper):
    def _install_old_owl_files():
        ontology_helper = get_new_ontology_helper()
        omo_id_old = FileId('omo.owl', 'old')
        hom_id_old = FileId('hom.owl', 'old')

        ontology_helper.install_ontology(stage_owl_file_and_get_url(omo_id_old))
        ontology_helper.install_ontology(stage_owl_file_and_get_url(hom_id_old))
        ontology_helper.store()

        return [omo_id_old, hom_id_old]

    return _install_old_owl_files


@httpretty.activate
def test_install_ontology(stage_owl_file_and_get_url, get_new_ontology_helper, tmp_path):
    helper = get_new_ontology_helper()

    assert list(helper.all_ontology_urls()) == []
    assert os.path.exists(os.path.join(tmp_path.resolve(), ONTOLOGY_DIR))

    omo_id_old = FileId('omo.owl', 'old')
    helper.install_ontology(stage_owl_file_and_get_url(omo_id_old))
    assert_helper_info_for_all_owl_file_ids(helper, [omo_id_old])

    hom_id_old = FileId('hom.owl', 'old')
    helper.install_ontology(stage_owl_file_and_get_url(hom_id_old))
    assert_helper_info_for_all_owl_file_ids(helper, [omo_id_old, hom_id_old])


@httpretty.activate
def test_load_from_storage(install_old_owl_files, get_new_ontology_helper):
    owl_id_list_old = install_old_owl_files()
    helper = get_new_ontology_helper()

    assert_helper_info_for_all_owl_file_ids(helper, owl_id_list_old)


@httpretty.activate
def test_delete_ontology(install_old_owl_files, get_new_ontology_helper):
    omo_id_old, hom_id_old = install_old_owl_files()
    helper = get_new_ontology_helper()

    helper.delete_ontology(_get_owl_mock_url(omo_id_old))
    assert_helper_info_for_all_owl_file_ids(helper, [hom_id_old])

    new_helper = get_new_ontology_helper()
    assert_helper_info_for_all_owl_file_ids(new_helper, [hom_id_old])


@httpretty.activate
def test_delete_all_ontologies(install_old_owl_files, get_new_ontology_helper):
    install_old_owl_files()
    helper = get_new_ontology_helper()

    helper.delete_all_ontologies()
    assert_helper_info_for_all_owl_file_ids(helper, [])

    new_helper = get_new_ontology_helper()
    assert_helper_info_for_all_owl_file_ids(new_helper, [])


@httpretty.activate
def test_update_ontology(install_old_owl_files, get_new_ontology_helper, stage_owl_file_and_get_url):
    omo_id_old, hom_id_old = install_old_owl_files()
    helper = get_new_ontology_helper()

    #
    # Test update with same URL but different ETag
    #

    omo_id_new = FileId('omo.owl', 'new')
    omo_new_url = stage_owl_file_and_get_url(omo_id_new)
    updated = helper.update_ontology(omo_new_url)

    assert_helper_info_for_all_owl_file_ids(helper, [hom_id_old, omo_id_new])
    assert updated

    #
    # Test update with same URL and same ETag
    #

    omo_id_maybe_newer = FileId('omo.owl', 'maybe_newer')
    omo_maybe_newer_url = stage_owl_file_and_get_url(omo_id_maybe_newer)
    updated = helper.update_ontology(omo_maybe_newer_url)

    assert_helper_info_for_all_owl_file_ids(helper, [hom_id_old, omo_id_maybe_newer])
    assert not updated


@httpretty.activate
def test_install_retries(get_new_ontology_helper, stage_owl_file_and_get_url):
    helper = get_new_ontology_helper()
    omo_id_old = FileId('omo.owl', 'old')
    omo_old_url = stage_owl_file_and_get_url(omo_id_old, respond_status=HTTPStatus.TOO_MANY_REQUESTS)
    helper.install_ontology(omo_old_url)


@httpretty.activate
def test_cached_update(get_new_ontology_helper, stage_owl_file_and_get_url):
    helper = get_new_ontology_helper()
    omo_id_old = FileId('omo.owl', 'old')
    omo_old_url = stage_owl_file_and_get_url(omo_id_old, max_age=1, respond_status=HTTPStatus.OK)
    helper.install_ontology(omo_old_url)

    #
    # Test that cache is being used, assuming the new request is within the max_age range (1 sec)
    #

    omo_old_url = stage_owl_file_and_get_url(omo_id_old, respond_status=HTTPStatus.NOT_FOUND)
    updated = helper.update_ontology(omo_old_url)

    assert_helper_info_for_all_owl_file_ids(helper, [omo_id_old])
    assert not updated

    #
    # Test that cache is not used after expiration
    #

    time.sleep(1.2)

    with pytest.raises(requests.exceptions.HTTPError):
        helper.update_ontology(omo_old_url)

    #
    # Test standard update with new version of owl file
    #

    omo_id_new = FileId('omo.owl', 'new')
    omo_new_url = stage_owl_file_and_get_url(omo_id_new, max_age=0, respond_status=HTTPStatus.OK)
    updated = helper.update_ontology(omo_new_url)

    assert_helper_info_for_all_owl_file_ids(helper, [omo_id_new])
    assert updated

    #
    # Test that ETag verification request is sent to mock server that responds with "Not Modified"
    #

    omo_new_url = stage_owl_file_and_get_url(omo_id_new, respond_status=HTTPStatus.NOT_MODIFIED)
    updated = helper.update_ontology(omo_new_url)

    assert_helper_info_for_all_owl_file_ids(helper, [omo_id_new])
    assert not updated


@httpretty.activate
def test_search_ontology(install_old_owl_files, get_new_ontology_helper, stage_owl_file_and_get_url):
    all_old_urls = _get_all_owl_mock_urls(install_old_owl_files())
    omo_url_old, hom_url_old = all_old_urls
    helper = get_new_ontology_helper()

    hom_term_id = "http://www.geneontology.org/formats/oboInOwl#NamespaceIdRule"
    term_label = helper.search_ontology_for_term_id(hom_url_old, hom_term_id)
    assert term_label == "namespace-id-rule"

    omo_term_id = "http://purl.obolibrary.org/obo/IAO_0000111"
    term_label = helper.search_ontologies_for_term_id(all_old_urls, omo_term_id)
    assert term_label == "editor preferred term"

    helper.update_ontology(stage_owl_file_and_get_url(FileId('omo.owl', 'new')))
    term_label = helper.search_all_ontologies_for_term_id(omo_term_id)
    assert term_label == "what I like to call it"


@httpretty.activate
def test_search_ontology_error_cases(install_old_owl_files, get_new_ontology_helper):
    all_urls = _get_all_owl_mock_urls(install_old_owl_files())
    omo_url_old, hom_url_old = all_urls
    helper = get_new_ontology_helper()

    omo_term_id_missing = "http://purl.obolibrary.org/obo/IAO_0000110"
    term_label = helper.search_ontology_for_term_id(omo_url_old, omo_term_id_missing)
    assert term_label is None

    term_label = helper.search_ontologies_for_term_id(all_urls, omo_term_id_missing)
    assert term_label is None

    term_label = helper.search_all_ontologies_for_term_id(omo_term_id_missing)
    assert term_label is None

    hom_term_id_no_label = "http://www.geneontology.org/formats/oboInOwl#auto-generated-by"
    with pytest.raises(ValueError):
        helper.search_ontology_for_term_id(hom_url_old, hom_term_id_no_label)

    with pytest.raises(ValueError):
        helper.search_ontologies_for_term_id(all_urls, hom_term_id_no_label)

    with pytest.raises(ValueError):
        helper.search_all_ontologies_for_term_id(hom_term_id_no_label)



