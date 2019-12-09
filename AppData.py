import json
import os
import urllib.request
from collections import defaultdict

import owlready2

from CommonFunctions import getFromDict, getPathsToElement, getFilenameFromUrl
from Constants import ONTOLOGY, PROPERTIES, SCHEMAS, TERM_ID


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
            schemaFn, _ = urllib.request.urlretrieve(url, category + '.json')

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
            fn = getFilenameFromUrl(url)
            if not os.path.exists(fn):
                ontoFile, _ = urllib.request.urlretrieve(url, fn)

            ontology = owlready2.get_ontology(fn)
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
















