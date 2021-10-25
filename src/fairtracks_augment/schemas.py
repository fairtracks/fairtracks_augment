import functools
import json
import os
import owlready2

from fairtracks_augment.constants import EDAM_ONTOLOGY, DOAP_VERSION, VERSION_IRI
from fairtracks_augment.localcache import LocalCache


class SchemaHelper(LocalCache):
    def __init__(self, config):
        self._schemas = {}
        super().__init__(filecache_dir_path=config.filecache_dir_path,
                         data_dir_path=config.schema_dir_path)

    # def _get_metadata_cls(cls):
    #     return FileMetadata

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