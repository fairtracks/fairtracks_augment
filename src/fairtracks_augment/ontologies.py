import functools
import os
import owlready2
import requests
import shutil
import urllib3
import yaml

from cachecontrol import CacheControl, CacheControlAdapter
from cachecontrol.caches import FileCache
from urllib.parse import urlparse
from yaml import YAMLObject

from fairtracks_augment.constants import ONTOLOGY_METADATA_FILE, \
    EDAM_ONTOLOGY, DOAP_VERSION, VERSION_IRI, DEFAULT_USERDATA_DIR, ONTOLOGY_DIR, \
    NUM_DOWNLOAD_RETRIES, REQUEST_TIMEOUT, FILECACHE_DIR, BACKOFF_FACTOR


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
        self._filecache_dir_path = os.path.join(user_data_dir, FILECACHE_DIR)
        self._metadata_yaml_path = os.path.join(self._ontology_dir_path, ONTOLOGY_METADATA_FILE)

        self._ensure_dir_exists(self._ontology_dir_path)
        self._ensure_dir_exists(self._filecache_dir_path)
        self._ontology_info_dict = self._load_ontology_metadata()
        self._ontologies = {}
        self._load_ontology_data()

    def __del__(self):
        self.store()

    def store(self):
        self._store_ontology_metadata()
        self._store_ontology_data()

    @staticmethod
    def _ensure_dir_exists(dir_path):
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

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
            self.update_ontology(url)

    def install_or_update_ontology(self, url):
        if url not in self._ontology_info_dict:
            self.install_ontology(url)
        else:
            self.update_ontology(url)

    def install_ontology(self, url):
        self._assert_ontology_not_installed(url)

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

    def _assert_ontology_not_installed(self, url):
        assert url not in self._ontology_info_dict
        assert url not in self._ontologies

    def _assert_ontology_installed(self, url):
        assert url in self._ontology_info_dict
        assert url in self._ontologies

    def _register_ontology_info(self, url):
        self._ontology_info_dict[url] = \
            self.OntologyInfo.create_from_url(self._ontology_dir_path, url)

    def update_ontology(self, url):
        self._assert_ontology_installed(url)

        if self._does_ontology_need_update(url):
            self.delete_ontology(url)
            self.install_ontology(url)
            return True
        else:
            return False

    def _http_get_request(self, url, callback_if_ok):
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
            session = CacheControl(session, cache=FileCache(self._filecache_dir_path),
                                   adapter_class=_create_cache_control_adapter)

            with session.get(url, stream=True, timeout=REQUEST_TIMEOUT) as response:
                response.raise_for_status()

                if 'etag' not in response.headers:
                    raise NotImplementedError('Ontology URL HTTP response without '
                                              '"ETag" header is not supported')

                return callback_if_ok(response)
        except requests.exceptions.RequestException:
            raise

    def _does_ontology_need_update(self, url):
        def _has_etag_changed_callback(response):
            return response.headers.get('etag') != self._ontology_info_dict[url].etag
        return self._http_get_request(url, callback_if_ok=_has_etag_changed_callback)

    def _get_owl_file_path(self, url):
        return self._ontology_info_dict[url].get_owl_path()

    def _download_owl_file(self, url):
        def _download_owl_file_callback(response):
            self._ontology_info_dict[url].etag = response.headers['etag']
            with open(self._get_owl_file_path(url), 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
        self._http_get_request(url, callback_if_ok=_download_owl_file_callback)

    def _parse_owl_file_into_db(self, url):
        self._ontologies[url].get_ontology(self._get_owl_file_path(url)).load()

    def _update_version_iri_from_owl_file(self, url):
        version_iri = self._extract_version_iri_from_owl_file(url)
        if not version_iri:
            raise ValueError('Unable to extract versionIRI from owl file for ontology: ' + url)
        self._ontology_info_dict[url].version_iri = version_iri

    def _extract_version_iri_from_owl_file(self, url):
        edam = False
        if EDAM_ONTOLOGY in url:
            edam = True

        with open(self._get_owl_file_path(url), 'r') as owlFile:
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

    def delete_ontology(self, url):
        self._assert_ontology_installed(url)

        print('deleting stored content for: ' + url)

        ontology_info = self._ontology_info_dict[url]
        del self._ontology_info_dict[url]

        self._ontologies[url].close()
        del self._ontologies[url]
        os.unlink(ontology_info.get_owl_path())
        os.unlink(ontology_info.get_db_path())

        print('deleted stored content for: ' + url)

    def delete_all_ontologies(self):
        for url in self.all_ontology_urls():
            self.delete_ontology(url)

    def get_version_iri_for_ontology(self, url):
        return self._ontology_info_dict[url].version_iri

    def get_etag_for_ontology(self, url):
        return self._ontology_info_dict[url].etag

    def search_all_ontologies_for_term_id(self, term_id):
        return self.search_ontologies_for_term_id(self.all_ontology_urls(), term_id)

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
        assert ontology_url in self._ontology_info_dict
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
