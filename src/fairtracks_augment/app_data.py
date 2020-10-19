import os
import json
import tempfile
import urllib

from fairtracks_augment.common import get_paths_to_element
from fairtracks_augment.constants import ONTOLOGY, PROPERTIES, TERM_ID, \
    ITEMS, TOP_SCHEMA_FN, SCHEMA_URL_PART1, SCHEMA_URL_PART2
from fairtracks_augment.nested_ordered_dict import NestedOrderedDict
from fairtracks_augment.ontologies import OntologyHelper


class AppData:
    def __init__(self, data=None, tmp_dir=None):
        print("initializing ontologies...")

        self.ontology_helper = OntologyHelper()
        self._paths_with_ontology_urls = []

        if data is None:
            data = NestedOrderedDict()
            data["@schema"] = self._get_current_schema_url()

        if tmp_dir:
            schemas = {}
            for filename in os.listdir(tmp_dir):
                if filename.endswith(".json"):
                    with open(os.path.join(tmp_dir, filename)) as schema_file:
                        schema = json.load(schema_file)
                        schemas[filename] = schema

            paths_to_element = get_paths_to_element(TERM_ID, data=schemas[TOP_SCHEMA_FN],
                                                    schemas=schemas)
        else:
            schema_url = data['@schema']
            paths_to_element = get_paths_to_element(TERM_ID, url=schema_url)

        self._paths_with_ontology_urls = \
            self._extract_paths_and_ontology_urls_from_schema(paths_to_element)
        self._install_all_ontologies()

    @staticmethod
    def _get_current_schema_url():
        i = 1
        current_schema_url = None
        with tempfile.TemporaryDirectory() as tmp_dir:
            while True:
                schema_url = SCHEMA_URL_PART1 + "v" + str(i) + SCHEMA_URL_PART2
                try:
                    schema_fn, _ = urllib.request.urlretrieve(schema_url,
                                                              os.path.join(tmp_dir, 'schema.json'))
                    current_schema_url = schema_url
                    i += 1
                except:
                    break
        return current_schema_url

    def get_paths_with_ontology_urls(self):
        return self._paths_with_ontology_urls

    def _extract_paths_and_ontology_urls_from_schema(self, paths_to_element):
        paths_and_urls = []

        for url, path, val in paths_to_element:
            ontology_urls = []
            if ONTOLOGY in val:
                ontology_urls = val[ONTOLOGY]
                if not isinstance(ontology_urls, list):
                    ontology_urls = [ontology_urls]
            new_path = self._cleanup_element_path(path)
            if ontology_urls:
                paths_and_urls.append((new_path, ontology_urls))

        return paths_and_urls

    def _cleanup_element_path(self, path):
        return [p for p in path if p != PROPERTIES and p != ITEMS]

    def _install_all_ontologies(self):
        for ontology_url in self._get_all_ontology_urls():
            self.ontology_helper.install_or_update_ontology(ontology_url)

    def _get_all_ontology_urls(self):
        ontology_urls = set()
        for path, onto_urls in self._paths_with_ontology_urls:
            for onto_url in onto_urls:
                ontology_urls.add(onto_url)
        return list(ontology_urls)
