from functools import partial

import httpretty
import os
import pytest

from collections import namedtuple

from owlready2 import locstr

from fairtracks_augment.config import Config, ONTOLOGY_DIR
from fairtracks_augment.ontologies import OntologyHelper
from tests.common import FileId, TestFileCache, stage_file_and_get_url


@pytest.fixture
def get_new_ontology_helper(tmp_path):
    def _get_new_ontology_helper():
        return OntologyHelper(config=Config(user_data_dir=tmp_path.resolve()))

    return _get_new_ontology_helper


OwlMetadata = namedtuple('OwlMetadata', ('version_iri', 'etag'))

OWL_METADATA_FOR_ASSERTS = {
    FileId('omo.owl', 'old'):
        OwlMetadata('http://purl.obolibrary.org/obo/omo/2020-05-08/omo.owl',
                    '594585592bd65f374afdd8cafec151fa'),
    FileId('omo.owl', 'new'):
        OwlMetadata('http://purl.obolibrary.org/obo/omo/2020-06-08/omo.owl',
                    'a136b8434c8ca8b6deca03529b6f3a58'),
    FileId('omo.owl', 'maybe_newer'):
        OwlMetadata('http://purl.obolibrary.org/obo/omo/2020-06-08/omo.owl',
                    'a136b8434c8ca8b6deca03529b6f3a58'),
    FileId('hom.owl', 'old'):
        OwlMetadata('http://purl.obolibrary.org/obo/hom/releases/2015-01-07/hom.owl',
                    'd3f7a3aabf82ce1f5cfc2112875eeba9')
}


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

        ontology_helper.install_file_from_url(stage_owl_file_and_get_url(omo_id_old))
        ontology_helper.install_file_from_url(stage_owl_file_and_get_url(hom_id_old))
        ontology_helper.store()

        return [omo_id_old, hom_id_old]

    return _install_old_owl_files


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
    assert term_label == locstr("editor preferred term", "en")

    helper.update_file(stage_owl_file_and_get_url(FileId('omo.owl', 'new')))
    term_label = helper.search_all_ontologies_for_term_id(omo_term_id)
    assert term_label == locstr("what I like to call it", "en")


@httpretty.activate
def test_delete_ontologies(install_old_owl_files, get_new_ontology_helper, stage_owl_file_and_get_url):
    all_old_urls = _get_all_owl_mock_urls(install_old_owl_files())
    omo_url_old, hom_url_old = all_old_urls
    helper = get_new_ontology_helper()

    helper.delete_file(omo_url_old)
    helper = get_new_ontology_helper()

    hom_term_id = "http://www.geneontology.org/formats/oboInOwl#NamespaceIdRule"
    term_label = helper.search_ontology_for_term_id(hom_url_old, hom_term_id)
    assert term_label == "namespace-id-rule"

    with pytest.raises(KeyError):
        omo_term_id = "http://purl.obolibrary.org/obo/IAO_0000111"
        helper.search_ontologies_for_term_id(all_old_urls, omo_term_id)

    helper.delete_all_files()

    with pytest.raises(KeyError):
        hom_term_id = "http://www.geneontology.org/formats/oboInOwl#NamespaceIdRule"
        helper.search_ontology_for_term_id(hom_url_old, hom_term_id)



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



