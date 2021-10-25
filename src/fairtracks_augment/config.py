import os
from pathlib import Path

from fairtracks_augment.common import ArgBasedSingleton

DEFAULT_USERDATA_DIR = os.path.join(Path.home(), '.fairtracks_augment')
FILECACHE_DIR = 'file_cache'
ONTOLOGY_DIR = 'ontologies'
METADATA_FILE = 'metadata.yaml'
ONTOLOGY_METADATA_FILE = 'ontologies.yaml'


class Config(metaclass=ArgBasedSingletonMeta):
    def __init__(self, user_data_dir=DEFAULT_USERDATA_DIR):
        self.filecache_dir_path = os.path.join(user_data_dir, FILECACHE_DIR)
        self.ontology_dir_path = os.path.join(user_data_dir, ONTOLOGY_DIR)
        self.metadata_yaml_path = os.path.join(self.ontology_dir_path, ONTOLOGY_METADATA_FILE)

        ensure_dir_exists(self.filecache_dir_path)
        ensure_dir_exists(self.ontology_dir_path)
