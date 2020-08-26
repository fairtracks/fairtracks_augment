from collections import defaultdict

import os
import owlready2
import urllib.request
import json

from CommonFunctions import getPathsToElement, getOntologyFilePath
from Constants import ONTOLOGY, PROPERTIES, TERM_ID, ITEMS, TOP_SCHEMA_FN


class AppData:
    def __init__(self, ontologies):
        self._pathsWithOntologyUrls = defaultdict(list)
        self._ontologies = ontologies

    def getPathsWithOntologyUrls(self):
        return self._pathsWithOntologyUrls

    def getOntologies(self):
        return self._ontologies

    def initApp(self, data, tmpDir=None):
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

        ontologyUrlsMap = self._getOntologyUrlsFromSchema(pathsToElement)
        self._pathsWithOntologyUrls = ontologyUrlsMap

        self._downloadOntologyFiles()

    def _downloadOntologyFiles(self):
        ontologyUrls = set()

        for path, ontoUrls in self._pathsWithOntologyUrls:
            for ontoUrl in ontoUrls:
                ontologyUrls.add(ontoUrl)

        for url in ontologyUrls:
            path = getOntologyFilePath(url)

            if not os.path.exists(path):
                print('downloading: ' + url)
                ontoFile, _ = urllib.request.urlretrieve(url, path)
                print('downloaded: ' + url)
            #ontoFile, _ = urllib.request.urlretrieve(url, path)

            if url not in self._ontologies:
                print('loading: ' + url)
                ontology = owlready2.get_ontology(path)
                ontology.load()
                print('loaded: ' + url)
                self._ontologies[url] = ontology

    def _getOntologyUrlsFromSchema(self, paths):
        pathsAndUrls = []

        for url, path, val in paths:
            ontologyUrls = []
            if ONTOLOGY in val:
                ontologyUrls = val[ONTOLOGY]
                if not isinstance(ontologyUrls, list):
                    ontologyUrls = [ontologyUrls]
            newPath = [p for p in path if p != PROPERTIES and p != ITEMS]
            if ontologyUrls:
                pathsAndUrls.append((newPath, ontologyUrls))

        return pathsAndUrls
