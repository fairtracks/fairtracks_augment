import functools
import shutil
import urllib
import os
import owlready2
import requests
import yaml

from urllib.parse import urlparse
from yaml import YAMLObject

from fairtracks_augment.constants import ONTOLOGY_METADATA_FILE, \
    EDAM_ONTOLOGY, DOAP_VERSION, VERSION_IRI, DEFAULT_USERDATA_DIR, ONTOLOGY_DIR, \
    NUM_DOWNLOAD_RETRIES


class ArgBasedSingleton(type):
    _instances = dict()

    def __call__(cls, **kwargs):
        args_as_tuple = tuple(kwargs.items())
        if args_as_tuple not in cls._instances:
            cls._instances[args_as_tuple] = super(ArgBasedSingleton, cls).__call__(**kwargs)
        return cls._instances[args_as_tuple]


class OntologyHelper(metaclass=ArgBasedSingleton):

    class OntologyInfo(YAMLObject):
        yaml_loader = yaml.SafeLoader
        yaml_tag = '!OntologyInfo'

        def __init__(self, ontology_dir_path, owl_filename, version_iri=None, etag=None):
            self._ontology_dir_path = ontology_dir_path
            self.owl_filename = owl_filename
            self.version_iri = version_iri
            self.etag = etag

        @classmethod
        def create_from_url(cls, ontology_dir_path, url):
            owl_file_name = os.path.basename(urlparse(url).path)
            return cls(ontology_dir_path, owl_file_name)

        def get_db_path(self):
            return os.path.join(self._ontology_dir_path,
                                self.owl_filename.replace('.owl', '.sqlite3'))

        def get_owl_path(self):
            return os.path.join(self._ontology_dir_path, self.owl_filename)

    def __init__(self, user_data_dir=DEFAULT_USERDATA_DIR):
        self._ontology_dir_path = os.path.join(user_data_dir, ONTOLOGY_DIR)
        self._metadata_yaml_path = os.path.join(self._ontology_dir_path, ONTOLOGY_METADATA_FILE)

        self._ensure_ontology_dir_exists()
        self._ontology_info_dict = self._load_ontology_metadata()
        self._ontologies = {}
        self._load_ontology_data()

    def __del__(self):
        self.store()

    def store(self):
        self._store_ontology_metadata()
        self._store_ontology_data()

    def clear_storage(self):
        shutil.rmtree(self._ontology_dir_path)

    def _ensure_ontology_dir_exists(self):
        if not os.path.exists(self._ontology_dir_path):
            os.makedirs(self._ontology_dir_path)

    def _load_ontology_metadata(self):
        if os.path.exists(self._metadata_yaml_path):
            with open(self._metadata_yaml_path, 'r') as yaml_file:
                return yaml.safe_load(yaml_file)
        return {}

    def _store_ontology_metadata(self):
        with open(self._metadata_yaml_path, 'w') as yaml_file:
            yaml.dump(self._ontology_info_dict, yaml_file)

    def _load_ontology_data(self):
        for url, ontology_info in self._ontology_info_dict.items():
            self._ensure_ontology_db(url)

    def _ensure_ontology_db(self, url):
        ontology_info = self._ontology_info_dict[url]
        self._ontologies[url] = owlready2.World(filename=ontology_info.get_db_path())

    def _store_ontology_data(self):
        for world in self._ontologies.values():
            world.save()

    def all_ontology_urls(self):
        return list(self._ontology_info_dict.keys())

    def update_all_ontologies(self):
        for url in self.all_ontology_urls():
            self._update_ontology(url)

    def install_or_update_ontology(self, url):
        if url not in self._ontology_info_dict:
            self._install_ontology(url)
        else:
            if self._does_ontology_need_update(url):
                self._update_ontology(url)

    def _install_ontology(self, url):
        self._register_ontology_info(url)

        print('downloading: ' + url)
        self._download_owl_file(url)
        print('downloaded: ' + url)

        print('loading: ' + url)
        self._ensure_ontology_db(url)
        self._parse_owl_file_into_db(url)
        print('loaded: ' + url)

        self._update_version_iri_from_owl_file(url)
        print('updated version IRI: ' + url)

    def _register_ontology_info(self, url):
        self._ontology_info_dict[url] = self.OntologyInfo.create_from_url(self._ontology_dir_path, url)

    def _get_owl_file_path(self, url):
        return self._ontology_info_dict[url].get_owl_path()

    def _download_owl_file(self, url):
        for i in reversed(range(NUM_DOWNLOAD_RETRIES)):
            try:
                with requests.get(url, stream=True) as response:
                    with open(self._get_owl_file_path(url), 'wb') as out_file:
                        shutil.copyfileobj(response.raw, out_file)
                        if 'etag' in response.headers:
                            self._ontology_info_dict[url].etag = response.headers['etag']
                        else:
                            raise NotImplementedError('Ontology URL HTTP response without '
                                                      '"ETag" header is not supported')
            except requests.exceptions.RequestException:
                if i == 0:
                    raise

    def _parse_owl_file_into_db(self, url):
        self._ontologies[url].get_ontology(self._get_owl_file_path(url)).load()

    def _update_version_iri_from_owl_file(self, url):
        version_iri = self._extract_version_iri_from_owl_file(url)
        if not version_iri:
            raise ValueError('Unable to extract versionIRI from owl file for ontology: '
                             + version_iri)
        self._ontology_info_dict[url].version_iri = version_iri

    def _extract_version_iri_from_owl_file(self, url):
        edam = False
        if EDAM_ONTOLOGY in url:
            edam = True

        with open(self._get_owl_file_path(url), 'r') as owlFile:
            for line in owlFile:
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
        return self._ontology_info_dict[url].version_iri

    def get_etag_for_ontology(self, url):
        return self._ontology_info_dict[url].etag

    def _does_ontology_need_update(self, url):
        return True

    def _update_ontology(self, url):
        self._delete_ontology(url)
        self._install_ontology(url)

    def _delete_ontology(self, url):
        del self._ontologies[url]

        print('deleting stored content for: ' + url)
        ontology_info = self.OntologyInfo.create_from_url(url)
        os.unlink(ontology_info.get_owl_path())
        os.unlink(ontology_info.get_db_path())
        print('deleted stored content for: ' + url)

    def search_all_ontologies_for_term_id(self, term_id):
        return self.search_ontologies_for_term_id(self.all_ontology_urls(), term_id)

    def search_ontologies_for_term_id(self, ontology_url_list, term_id):
        for ontologyUrl in ontology_url_list:
            term_label = self.search_ontology_for_term_id(ontologyUrl, term_id)
            if term_label:
                return term_label
        return None

    def search_ontology_for_term_id(self, ontology_url, term_id):
        version_iri = self.get_version_iri_for_ontology(ontology_url)
        return self._search_ontology_for_term_id_version(ontology_url, term_id, version_iri)

    @functools.lru_cache(maxsize=100000)
    def _search_ontology_for_term_id_version(self, ontology_url, term_id, version_iri):
        assert ontology_url in self._ontology_info_dict
        assert ontology_url in self._ontologies
        assert version_iri == self.get_version_iri_for_ontology(ontology_url)

        termLabel = self._ontologies[ontology_url].search(iri=term_id)
        if termLabel:
            return termLabel[0].label[0]
        else:
            return None
