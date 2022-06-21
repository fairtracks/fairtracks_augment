import functools
import json
import os
from urllib.parse import urlparse, quote

import owlready2

from fairtracks_augment.constants import EDAM_ONTOLOGY, DOAP_VERSION, VERSION_IRI
from fairtracks_augment.localcache import LocalCache, FileMetadata


class SchemasMetadata(FileMetadata):
    yaml_tag = '!SchemasMetadata'

    @classmethod
    def create_from_url(cls, file_dir_path, url):
        # url_path = urlparse(url).path
        file_name = quote(url, safe='')
        return cls(file_dir_path, file_name)

    def get_file_path(self):
        return os.path.join(self._file_dir_path, self._filename)


class SchemaHelper(LocalCache):
    def __init__(self, config):
        self._schemas = {}
        super().__init__(filecache_dir_path=config.filecache_dir_path,
                         data_dir_path=config.schema_dir_path)

    def _get_metadata_cls(cls):
        return SchemasMetadata

    def _load_data_from_stored(self):
        for url in self._file_metadata_dict.keys():
            self._install_data_from_file(url)

    def _install_data_from_file(self, url):
        self._schemas[url] = json.load(open(self._get_file_path(url), 'r'))

    def _store_data(self):
        pass

    def _data_contains_url(self, url):
        return url in self._schemas

    def _update_metadata_from_file(self, url):
        pass

    def _delete_data(self, file_metadata, url):
        del self._schemas[url]