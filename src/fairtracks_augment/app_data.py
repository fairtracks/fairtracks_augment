import os
import json
import tempfile
import urllib

from fairtracks_augment.common import getPathsToElement
from fairtracks_augment.constants import ONTOLOGY, PROPERTIES, TERM_ID, \
    ITEMS, TOP_SCHEMA_FN, SCHEMA_URL_PART1, SCHEMA_URL_PART2
from fairtracks_augment.nested_ordered_dict import NestedOrderedDict
from fairtracks_augment.ontologies import OntologyHelper


class AppData:
    def __init__(self, data=None, tmpDir=None):
        print("initializing ontologies...")

        self.ontologyHelper = OntologyHelper()
        self._pathsWithOntologyUrls = []

        if data is None:
            data = NestedOrderedDict()
            data["@schema"] = self._getCurrentSchemaUrl()

        if tmpDir:
            schemas = {}
            for filename in os.listdir(tmpDir):
                if filename.endswith(".json"):
                    with open(os.path.join(tmpDir, filename)) as schemaFile:
                        schema = json.load(schemaFile)
                        schemas[filename] = schema

            pathsToElement = getPathsToElement(TERM_ID, data=schemas[TOP_SCHEMA_FN], schemas=schemas)
        else:
            schemaUrl = data['@schema']
            pathsToElement = getPathsToElement(TERM_ID, url=schemaUrl)

        self._pathsWithOntologyUrls = self._extractPathsAndOntologyUrlsFromSchema(pathsToElement)
        self._installAllOntologies()

    @staticmethod
    def _getCurrentSchemaUrl():
        i = 1
        currentSchemaUrl = None
        with tempfile.TemporaryDirectory() as tmpDir:
            while True:
                schemaUrl = SCHEMA_URL_PART1 + "v" + str(i) + SCHEMA_URL_PART2
                try:
                    schemaFn, _ = urllib.request.urlretrieve(schemaUrl,
                                                             os.path.join(tmpDir, 'schema.json'))
                    currentSchemaUrl = schemaUrl
                    i += 1
                except:
                    break
        return currentSchemaUrl

    def getPathsWithOntologyUrls(self):
        return self._pathsWithOntologyUrls

    def _extractPathsAndOntologyUrlsFromSchema(self, pathsToElement):
        pathsAndUrls = []

        for url, path, val in pathsToElement:
            ontologyUrls = []
            if ONTOLOGY in val:
                ontologyUrls = val[ONTOLOGY]
                if not isinstance(ontologyUrls, list):
                    ontologyUrls = [ontologyUrls]
            newPath = self._cleanupElementPath(path)
            if ontologyUrls:
                pathsAndUrls.append((newPath, ontologyUrls))

        return pathsAndUrls

    def _cleanupElementPath(self, path):
        return [p for p in path if p != PROPERTIES and p != ITEMS]

    def _installAllOntologies(self):
        for ontologyUrl in self._getAllOntologyUrls():
            self.ontologyHelper.installOrUpdateOntology(ontologyUrl)

    def _getAllOntologyUrls(self):
        ontologyUrls = set()
        for path, ontoUrls in self._pathsWithOntologyUrls:
            for ontoUrl in ontoUrls:
                ontologyUrls.add(ontoUrl)
        return list(ontologyUrls)
