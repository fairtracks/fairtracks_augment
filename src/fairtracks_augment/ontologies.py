import functools
import os
import owlready2

from fairtracks_augment.constants import EDAM_ONTOLOGY, DOAP_VERSION, VERSION_IRI
from fairtracks_augment.localcache import LocalCache, FileMetadata


class OntologyMetadata(FileMetadata):
    yaml_tag = '!OntologyMetadata'

    def __init__(self, data_dir_path, filename, etag=None, version_iri=None):
        super().__init__(data_dir_path, filename, etag=etag)
        self.version_iri = version_iri

    def get_db_path(self):
        return os.path.join(self._file_dir_path,
                            self._filename.replace('.owl', '.sqlite3'))


class OntologyHelper(LocalCache):
    def __init__(self, config):
        self._ontologies = {}
        super().__init__(filecache_dir_path=config.filecache_dir_path,
                         data_dir_path=config.ontology_dir_path)

    def _get_metadata_cls(cls):
        return OntologyMetadata

    def _load_data_from_stored(self):
        for url, file_metadata in self._file_metadata_dict.items():
            self._ensure_file_db(url)

    def _install_data_from_file(self, url):
        self._ensure_file_db(url)
        self._parse_owl_file_into_db(url)

    def _ensure_file_db(self, url):
        file_metadata = self._file_metadata_dict[url]
        self._ontologies[url] = owlready2.World(filename=file_metadata.get_db_path())

    def _parse_owl_file_into_db(self, url):
        self._ontologies[url].get_ontology(self._get_file_path(url)).load()

    def _store_data(self):
        for world in self._ontologies.values():
            world.save()

    def _data_contains_url(self, url):
        return url in self._ontologies

    def _update_metadata_from_file(self, url):
        self._update_version_iri_from_owl_file(url)

    def _update_version_iri_from_owl_file(self, url):
        version_iri = self._extract_version_iri_from_owl_file(url)
        if not version_iri:
            raise ValueError('Unable to extract versionIRI from owl file for ontology: ' + url)
        self._file_metadata_dict[url].version_iri = version_iri

    def _extract_version_iri_from_owl_file(self, url):
        edam = False
        if EDAM_ONTOLOGY in url:
            edam = True

        with open(self._get_file_path(url), 'r') as owlFile:
            for line in owlFile:
                # TODO: parse owl content for improved robustness
                if edam:
                    if DOAP_VERSION in line:
                        version_number = line.split(DOAP_VERSION)[1].split('<')[0]
                        version_iri = EDAM_ONTOLOGY + 'EDAM_' + version_number + '.owl'
                        return version_iri
                else:
                    if VERSION_IRI in line:
                        version_iri = line.split(VERSION_IRI)[1].split('"')[0]
                        return version_iri
            return None

    def get_version_iri_for_ontology(self, url):
        return self._file_metadata_dict[url].version_iri

    def _delete_data(self, file_metadata, url):
        self._ontologies[url].close()
        del self._ontologies[url]
        os.unlink(file_metadata.get_db_path())

    def search_all_ontologies_for_term_id(self, term_id):
        return self.search_ontologies_for_term_id(self.all_file_urls(), term_id)

    def search_ontologies_for_term_id(self, ontology_url_list, term_id):
        for ontology_url in ontology_url_list:
            term_label = self.search_ontology_for_term_id(ontology_url, term_id)
            if term_label:
                return term_label
        return None

    def search_ontology_for_term_id(self, ontology_url, term_id):
        version_iri = self.get_version_iri_for_ontology(ontology_url)
        return self._search_ontology_for_term_id_version(ontology_url, term_id, version_iri)

    @functools.lru_cache(maxsize=100000)
    def _search_ontology_for_term_id_version(self, ontology_url, term_id, version_iri):
        assert ontology_url in self._file_metadata_dict
        assert ontology_url in self._ontologies
        assert version_iri == self.get_version_iri_for_ontology(ontology_url)

        terms_found = self._ontologies[ontology_url].search(iri=term_id)
        if terms_found:
            assert len(terms_found) == 1
            try:
                return terms_found[0].label[0]
            except (AttributeError, IndexError):
                raise ValueError(
                    'Term ID "{}" was not registered with a label in ontology "{}"'.format(
                        term_id, ontology_url
                    )
                )
        else:
            return None
