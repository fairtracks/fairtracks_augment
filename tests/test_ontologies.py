from __future__ import unicode_literals

import hashlib
import os

from collections import namedtuple
from pathlib import Path
from pytest import fixture

from fairtracks_augment.constants import ONTOLOGY_DIR
from fairtracks_augment.ontologies import OntologyHelper


OwlId = namedtuple('OwlId', ['name', 'version'])

OwlInfo = namedtuple('OwlInfo', ['version_iri', 'etag'])

OWL_METADATA_FOR_ASSERTS = {
    OwlId('omo', 'old'): OwlInfo('http://purl.obolibrary.org/obo/omo/2020-05-08/omo.owl',
                                 '594585592bd65f374afdd8cafec151fa'),
    OwlId('omo', 'new'): OwlInfo('http://purl.obolibrary.org/obo/omo/2020-06-08/omo.owl',
                                 '41acd68b664b6a605067e15c4cdb4d0b'),
    OwlId('omo', 'maybe_newer'): OwlInfo('http://purl.obolibrary.org/obo/omo/2020-06-08/omo.owl',
                                         '41acd68b664b6a605067e15c4cdb4d0b'),
    OwlId('cdao', 'old'): OwlInfo('http://purl.obolibrary.org/obo/cdao/2019-06-26/cdao.owl',
                                  '0d8919eaa1c64d6a051e4d665fc71368')
}

MD5_HASH_FOR_FILE_DICT = {}


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


def get_md5_hash_for_owl_file(owl_path):
    if owl_path not in MD5_HASH_FOR_FILE_DICT:
        with open(owl_path, 'rb') as owl_file:
            MD5_HASH_FOR_FILE_DICT[owl_path] = hashlib.md5(owl_file.read()).hexdigest()
    return MD5_HASH_FOR_FILE_DICT[owl_path]


@fixture
def stage_owl_and_get_url(request, requests_mock):
    def _stage_owl_and_get_url(owl_id):
        test_dir = Path(request.module.__file__).parent
        owl_path = os.path.join(test_dir, 'data', 'owl', owl_id.version, owl_id.name + '.owl')
        owl_url = get_owl_url(owl_id)
        md5_hash = get_md5_hash_for_owl_file(owl_path)
        requests_mock.get(owl_url, text=open(owl_path).read(), headers={'ETag': md5_hash})
        return owl_url

    return _stage_owl_and_get_url


@fixture
def get_new_ontology_helper(tmp_path):
    def _get_new_ontology_helper():
        return OntologyHelper(user_data_dir=tmp_path.resolve())

    return _get_new_ontology_helper


@fixture
def install_old_owl_files(stage_owl_and_get_url, get_new_ontology_helper):
    ontology_helper = get_new_ontology_helper()
    omo_id_old = OwlId('omo', 'old')
    cdao_id_old = OwlId('cdao', 'old')

    ontology_helper.install_ontology(stage_owl_and_get_url(omo_id_old))
    ontology_helper.install_ontology(stage_owl_and_get_url(cdao_id_old))
    ontology_helper.store()

    return [omo_id_old, cdao_id_old]


def test_install_ontology(stage_owl_and_get_url, get_new_ontology_helper, tmp_path):
    helper = get_new_ontology_helper()

    assert list(helper.all_ontology_urls()) == []
    assert os.path.exists(os.path.join(tmp_path.resolve(), ONTOLOGY_DIR))

    omo_id_old = OwlId('omo', 'old')
    helper.install_ontology(stage_owl_and_get_url(omo_id_old))
    assert_helper_info_for_all_owl_ids(helper, [omo_id_old])

    cdao_id_old = OwlId('cdao', 'old')
    helper.install_ontology(stage_owl_and_get_url(cdao_id_old))
    assert_helper_info_for_all_owl_ids(helper, [omo_id_old, cdao_id_old])


def test_load_from_storage(install_old_owl_files, get_new_ontology_helper):
    owl_id_list_old = install_old_owl_files
    helper = get_new_ontology_helper()

    assert_helper_info_for_all_owl_ids(helper, owl_id_list_old)


def test_delete_ontology(install_old_owl_files, get_new_ontology_helper):
    omo_id_old, cdao_id_old = install_old_owl_files
    helper = get_new_ontology_helper()

    helper.delete_ontology(get_owl_url(omo_id_old))
    assert_helper_info_for_all_owl_ids(helper, [cdao_id_old])

    new_helper = get_new_ontology_helper()
    assert_helper_info_for_all_owl_ids(new_helper, [cdao_id_old])


def test_delete_all_ontologies(install_old_owl_files, get_new_ontology_helper):
    helper = get_new_ontology_helper()

    helper.delete_all_ontologies()
    assert_helper_info_for_all_owl_ids(helper, [])

    new_helper = get_new_ontology_helper()
    assert_helper_info_for_all_owl_ids(new_helper, [])


def test_update_ontology(install_old_owl_files, get_new_ontology_helper, stage_owl_and_get_url):
    omo_id_old, cdao_id_old = install_old_owl_files
    helper = get_new_ontology_helper()

    omo_id_new = OwlId('omo', 'new')
    omo_new_url = stage_owl_and_get_url(omo_id_new)
    updated = helper.update_ontology(omo_new_url)

    assert_helper_info_for_all_owl_ids(helper, [cdao_id_old, omo_id_new])
    assert updated

    omo_id_maybe_newer = OwlId('omo', 'maybe_newer')
    omo_maybe_newer_url = stage_owl_and_get_url(omo_id_maybe_newer)
    updated = helper.update_ontology(omo_maybe_newer_url)

    assert_helper_info_for_all_owl_ids(helper, [cdao_id_old, omo_id_maybe_newer])
    assert not updated
