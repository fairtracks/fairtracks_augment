from __future__ import unicode_literals

import hashlib
from functools import partial

import httpretty
import os
import pytest
import requests
import time

from collections import namedtuple
from email.utils import formatdate
from http import HTTPStatus
from httpretty import Response, HTTPretty
from pathlib import Path

from fairtracks_augment.constants import ONTOLOGY_DIR
from fairtracks_augment.ontologies import OntologyHelper, ArgBasedSingleton

OwlId = namedtuple('OwlId', ('name', 'version'))

OwlInfo = namedtuple('OwlInfo', ('version_iri', 'etag'))

OWL_METADATA_FOR_ASSERTS = {
    OwlId('omo', 'old'): OwlInfo('http://purl.obolibrary.org/obo/omo/2020-05-08/omo.owl',
                                 '594585592bd65f374afdd8cafec151fa'),
    OwlId('omo', 'new'): OwlInfo('http://purl.obolibrary.org/obo/omo/2020-06-08/omo.owl',
                                 '41acd68b664b6a605067e15c4cdb4d0b'),
    OwlId('omo', 'maybe_newer'): OwlInfo('http://purl.obolibrary.org/obo/omo/2020-06-08/omo.owl',
                                         '41acd68b664b6a605067e15c4cdb4d0b'),
    OwlId('hom', 'old'): OwlInfo('http://purl.obolibrary.org/obo/hom/releases/2015-01-07/hom.owl',
                                 'd3f7a3aabf82ce1f5cfc2112875eeba9')
}

OwlFile = namedtuple('OwlFile', ('path', 'contents', 'md5'))


class OwlFileCache:
    def __init__(self):
        self._owl_file_cache = dict()

    def load_owl_file(self, owl_id, test_dir):
        if owl_id not in self._owl_file_cache:
            owl_path = os.path.join(test_dir, 'data', 'owl', owl_id.version, owl_id.name + '.owl')
            owl_contents = open(owl_path).read()
            owl_md5 = hashlib.md5(owl_contents.encode('utf8')).hexdigest()
            self._owl_file_cache[owl_id] = OwlFile(owl_path, owl_contents, owl_md5)
        return self._owl_file_cache[owl_id]


OWL_FILE_CACHE = OwlFileCache()


def get_owl_url(owl_id):
    return 'https://localhost/{}.owl'.format(owl_id.name)


def get_all_owl_urls(owl_id_list):
    return [get_owl_url(_) for _ in owl_id_list]


def assert_helper_info_for_owl_id(helper, owl_id):
    assert helper.get_version_iri_for_ontology(get_owl_url(owl_id)) == \
           OWL_METADATA_FOR_ASSERTS[owl_id].version_iri
    assert helper.get_etag_for_ontology(get_owl_url(owl_id)) == \
           OWL_METADATA_FOR_ASSERTS[owl_id].etag


def assert_helper_info_for_all_owl_ids(helper, owl_id_list):
    assert helper.all_ontology_urls() == get_all_owl_urls(owl_id_list)
    for owl_id in owl_id_list:
        assert_helper_info_for_owl_id(helper, owl_id)


@pytest.fixture
def stage_owl_and_get_url(request):
    def _stage_owl_and_get_url(owl_id, max_age=0, respond_status=HTTPStatus.OK):
        test_dir = Path(request.module.__file__).parent
        owl_file = OWL_FILE_CACHE.load_owl_file(owl_id, test_dir)
        owl_url = get_owl_url(owl_id)

        headers = dict()
        headers['ETag'] = owl_file.md5
        if max_age is not None:
            headers['Cache-Control'] = 'max-age={}'.format(max_age)
            headers['Date'] = formatdate(usegmt=True)

        responses = list()

        def _add_response(body, status=respond_status):
            responses.append(Response(body=body, adding_headers=headers, status=status.value))

        if respond_status == HTTPStatus.OK:
            _add_response(owl_file.contents)

        elif respond_status == HTTPStatus.TOO_MANY_REQUESTS:
            _add_response('', status=HTTPStatus.TOO_MANY_REQUESTS)
            _add_response(owl_file.contents, status=HTTPStatus.OK)

        elif respond_status == HTTPStatus.NOT_MODIFIED:
            def _empty_assert_if_none_match(http_req, uri, response_headers):
                assert 'If-None-Match' in http_req.headers
                etag = http_req.headers['If-None-Match']
                assert etag == owl_file.md5
                return [respond_status.value, response_headers, '']

            _add_response(_empty_assert_if_none_match)

        else:
            _add_response('')

        httpretty.reset()
        httpretty.register_uri(
            HTTPretty.GET,
            owl_url,
            responses=responses
        )

        return owl_url

    return _stage_owl_and_get_url


@pytest.fixture
def get_new_ontology_helper(tmp_path):
    def _get_new_ontology_helper():
        return OntologyHelper(user_data_dir=tmp_path.resolve())

    return _get_new_ontology_helper


@pytest.fixture
def install_old_owl_files(stage_owl_and_get_url, get_new_ontology_helper):
    def _install_old_owl_files():
        ontology_helper = get_new_ontology_helper()
        omo_id_old = OwlId('omo', 'old')
        hom_id_old = OwlId('hom', 'old')

        ontology_helper.install_ontology(stage_owl_and_get_url(omo_id_old))
        ontology_helper.install_ontology(stage_owl_and_get_url(hom_id_old))
        ontology_helper.store()

        return [omo_id_old, hom_id_old]

    return _install_old_owl_files


@httpretty.activate
def test_install_ontology(stage_owl_and_get_url, get_new_ontology_helper, tmp_path):
    helper = get_new_ontology_helper()

    assert list(helper.all_ontology_urls()) == []
    assert os.path.exists(os.path.join(tmp_path.resolve(), ONTOLOGY_DIR))

    omo_id_old = OwlId('omo', 'old')
    helper.install_ontology(stage_owl_and_get_url(omo_id_old))
    assert_helper_info_for_all_owl_ids(helper, [omo_id_old])

    hom_id_old = OwlId('hom', 'old')
    helper.install_ontology(stage_owl_and_get_url(hom_id_old))
    assert_helper_info_for_all_owl_ids(helper, [omo_id_old, hom_id_old])


@httpretty.activate
def test_load_from_storage(install_old_owl_files, get_new_ontology_helper):
    owl_id_list_old = install_old_owl_files()
    helper = get_new_ontology_helper()

    assert_helper_info_for_all_owl_ids(helper, owl_id_list_old)


@httpretty.activate
def test_delete_ontology(install_old_owl_files, get_new_ontology_helper):
    omo_id_old, hom_id_old = install_old_owl_files()
    helper = get_new_ontology_helper()

    helper.delete_ontology(get_owl_url(omo_id_old))
    assert_helper_info_for_all_owl_ids(helper, [hom_id_old])

    new_helper = get_new_ontology_helper()
    assert_helper_info_for_all_owl_ids(new_helper, [hom_id_old])


@httpretty.activate
def test_delete_all_ontologies(install_old_owl_files, get_new_ontology_helper):
    install_old_owl_files()
    helper = get_new_ontology_helper()

    helper.delete_all_ontologies()
    assert_helper_info_for_all_owl_ids(helper, [])

    new_helper = get_new_ontology_helper()
    assert_helper_info_for_all_owl_ids(new_helper, [])


@httpretty.activate
def test_update_ontology(install_old_owl_files, get_new_ontology_helper, stage_owl_and_get_url):
    omo_id_old, hom_id_old = install_old_owl_files()
    helper = get_new_ontology_helper()

    #
    # Test update with same URL but different ETag
    #

    omo_id_new = OwlId('omo', 'new')
    omo_new_url = stage_owl_and_get_url(omo_id_new)
    updated = helper.update_ontology(omo_new_url)

    assert_helper_info_for_all_owl_ids(helper, [hom_id_old, omo_id_new])
    assert updated

    #
    # Test update with same URL and same ETag
    #

    omo_id_maybe_newer = OwlId('omo', 'maybe_newer')
    omo_maybe_newer_url = stage_owl_and_get_url(omo_id_maybe_newer)
    updated = helper.update_ontology(omo_maybe_newer_url)

    assert_helper_info_for_all_owl_ids(helper, [hom_id_old, omo_id_maybe_newer])
    assert not updated


@httpretty.activate
def test_install_retries(get_new_ontology_helper, stage_owl_and_get_url):
    helper = get_new_ontology_helper()
    omo_id_old = OwlId('omo', 'old')
    omo_old_url = stage_owl_and_get_url(omo_id_old, respond_status=HTTPStatus.TOO_MANY_REQUESTS)
    helper.install_ontology(omo_old_url)


@httpretty.activate
def test_cached_update(get_new_ontology_helper, stage_owl_and_get_url):
    helper = get_new_ontology_helper()
    omo_id_old = OwlId('omo', 'old')
    omo_old_url = stage_owl_and_get_url(omo_id_old, max_age=1, respond_status=HTTPStatus.OK)
    helper.install_ontology(omo_old_url)

    #
    # Test that cache is being used, assuming the new request is within the max_age range (1 sec)
    #

    omo_old_url = stage_owl_and_get_url(omo_id_old, respond_status=HTTPStatus.NOT_FOUND)
    updated = helper.update_ontology(omo_old_url)

    assert_helper_info_for_all_owl_ids(helper, [omo_id_old])
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

    omo_id_new = OwlId('omo', 'new')
    omo_new_url = stage_owl_and_get_url(omo_id_new, max_age=0, respond_status=HTTPStatus.OK)
    updated = helper.update_ontology(omo_new_url)

    assert_helper_info_for_all_owl_ids(helper, [omo_id_new])
    assert updated

    #
    # Test that ETag verification request is sent to mock server that responds with "Not Modified"
    #

    omo_new_url = stage_owl_and_get_url(omo_id_new, respond_status=HTTPStatus.NOT_MODIFIED)
    updated = helper.update_ontology(omo_new_url)

    assert_helper_info_for_all_owl_ids(helper, [omo_id_new])
    assert not updated
