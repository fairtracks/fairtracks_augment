import json
import urllib.request
from collections import defaultdict

import owlready2

from CommonFunctions import getFromDict, getPathsToElement, getSchemaFilePath, \
    getOntologyFilePath
from Constants import ONTOLOGY, PROPERTIES, SCHEMAS, TERM_ID, PHENOTYPE, SAMPLES


class AppData():

    def __init__(self):
        self._pathsWithOntologyUrls = defaultdict(list)
        self._ontologies = {}

    def getPathsWithOntologyUrls(self):
        return self._pathsWithOntologyUrls

    def getOntologies(self):
        return self._ontologies

    def initApp(self):
        for category, url in SCHEMAS.items():
            schemaFn, _ = urllib.request.urlretrieve(url, getSchemaFilePath(category))

            with open(schemaFn, 'r') as schemaFile:
                schemaJson = json.load(schemaFile)
                pathsToElement = getPathsToElement(schemaJson[PROPERTIES], TERM_ID)
                ontologyUrlsMap = self._getOntologyUrlsFromSchema(schemaJson[PROPERTIES], pathsToElement)
                self._pathsWithOntologyUrls[category] = ontologyUrlsMap

        self._handlePhenotype()

        self._downloadOntologyFiles()

    def _downloadOntologyFiles(self):
        ontologyUrls = set()

        for category in self._pathsWithOntologyUrls.keys():
            for path, ontoUrls in self._pathsWithOntologyUrls[category]:
                for ontoUrl in ontoUrls:
                    ontologyUrls.add(ontoUrl)

        for url in ontologyUrls:
            path = getOntologyFilePath(url)
            print('loading: ' + url)
            # if not os.path.exists(path):
            #     ontoFile, _ = urllib.request.urlretrieve(url, path)
            ontoFile, _ = urllib.request.urlretrieve(url, path)

            ontology = owlready2.get_ontology(path)
            ontology.load()
            print('loaded: ' + url)
            self._ontologies[url] = ontology

    def _getOntologyUrlsFromSchema(self, data, paths):
        pathsAndUrls = []

        for path in paths:
            ontologyUrls = []
            el = getFromDict(data, path)
            if ONTOLOGY in el:
                ontologyUrls = el[ONTOLOGY]
                if not isinstance(ontologyUrls, list):
                    ontologyUrls = [ontologyUrls]
            newPath = [p for p in path if p != PROPERTIES]
            if ontologyUrls:
                pathsAndUrls.append((newPath, ontologyUrls))

        return pathsAndUrls

    def _handlePhenotype(self):
        if PHENOTYPE in self._pathsWithOntologyUrls:
            phenotypePathsAndUrls = self._pathsWithOntologyUrls[PHENOTYPE]
            correctedPathsAndUrls = []
            for path, ontoUrls in phenotypePathsAndUrls:
                path.insert(0, PHENOTYPE)
                correctedPathsAndUrls.append((path, ontoUrls))

            self._pathsWithOntologyUrls[SAMPLES].extend(correctedPathsAndUrls)
            del self._pathsWithOntologyUrls[PHENOTYPE]

