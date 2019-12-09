import json
import os
import urllib.request
from collections import defaultdict
from os.path import dirname

import owlready2

from CommonFunctions import getFromDict, getPathsToElement, getFilenameFromUrl
from Constants import ONTOLOGY, PROPERTIES, SCHEMAS, TERM_ID, SCHEMA_FOLDER_PATH, \
    ONTOLOGY_FOLDER_PATH


class AppData():

    def __init__(self):
        self._pathsWithOntologyUrls = defaultdict(list)
        self._ontologies = {}

    def getPathsWithOntologyUrls(self):
        return self._pathsWithOntologyUrls

    def getOntologies(self):
        return self._ontologies

    def setPathsWithOntologyUrls(self, paths):
        self._pathsWithOntologyUrls = paths

    def setOntologies(self, ontologies):
        self._ontologies = ontologies

    def initApp(self):
        for category, url in SCHEMAS.items():
            schemaFn, _ = urllib.request.urlretrieve(url, self._getSchemaFilePath(category))

            with open(schemaFn, 'r') as schemaFile:
                schemaJson = json.load(schemaFile)
                pathsToElement = getPathsToElement(schemaJson[PROPERTIES], TERM_ID)
                ontologyUrlsMap = self._getOntologyUrlsFromSchema(schemaJson[PROPERTIES], pathsToElement)
                self._pathsWithOntologyUrls[category] = ontologyUrlsMap

        print(self._pathsWithOntologyUrls)

        self._downloadOntologyFiles()

    def _downloadOntologyFiles(self):
        ontologyUrls = set()

        for category in self._pathsWithOntologyUrls.keys():
            for path, ontoUrls in self._pathsWithOntologyUrls[category]:
                for ontoUrl in ontoUrls:
                    ontologyUrls.add(ontoUrl)

        for url in ontologyUrls:
            print('loading ' + str(url))
            path = self._getOntologyFilePath(url)
            if not os.path.exists(path):
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

    def _getSchemaFilePath(self, category):
        path = os.path.join(SCHEMA_FOLDER_PATH, category + '.json')
        if not os.path.exists(dirname(path)):
            os.makedirs(os.path.dirname(path))

        return path

    def _getOntologyFilePath(self, url):
        path = os.path.join(ONTOLOGY_FOLDER_PATH, getFilenameFromUrl(url))
        if not os.path.exists(dirname(path)):
            os.makedirs(os.path.dirname(path))

        return path















