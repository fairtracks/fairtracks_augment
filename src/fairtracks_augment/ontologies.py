import functools
import shutil
import urllib
import os
import owlready2
import requests
import yaml

from urllib.parse import urlparse
from yaml import YAMLObject

from fairtracks_augment.constants import ONTOLOGY_METADATA_FILE, \
    EDAM_ONTOLOGY, DOAP_VERSION, VERSION_IRI, DEFAULT_USERDATA_DIR, ONTOLOGY_DIR, \
    NUM_DOWNLOAD_RETRIES


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

        def __init__(self, ontologyDirPath, owl_filename, version_iri=None, etag=None):
            self._ontologyDirPath = ontologyDirPath
            self.owlFilename = owl_filename
            self.versionIRI = version_iri
            self.etag = etag

        @classmethod
        def createFromUrl(cls, ontologyDirPath, url):
            owlFileName = os.path.basename(urlparse(url).path)
            return cls(ontologyDirPath, owlFileName)

        def getDbPath(self):
            return os.path.join(self._ontologyDirPath,
                                self.owlFilename.replace('.owl', '.sqlite3'))

        def getOwlPath(self):
            return os.path.join(self._ontologyDirPath, self.owlFilename)

    def __init__(self, userDataDir=DEFAULT_USERDATA_DIR):
        self._ontologyDirPath = os.path.join(userDataDir, ONTOLOGY_DIR)
        self._metadataYamlPath = os.path.join(self._ontologyDirPath, ONTOLOGY_METADATA_FILE)

        self._ensureOntologyDirExists()
        self._ontologyInfoDict = self._loadOntologyMetadata()
        self._ontologies = {}
        self._loadOntologyData()

    def __del__(self):
        self.store()

    def store(self):
        self._storeOntologyMetadata()
        self._storeOntologyData()

    def clearStorage(self):
        shutil.rmtree(self._ontologyDirPath)

    def _ensureOntologyDirExists(self):
        if not os.path.exists(self._ontologyDirPath):
            os.makedirs(self._ontologyDirPath)

    def _loadOntologyMetadata(self):
        if os.path.exists(self._metadataYamlPath):
            with open(self._metadataYamlPath, 'r') as yamlFile:
                return yaml.safe_load(yamlFile)
        return {}

    def _storeOntologyMetadata(self):
        with open(self._metadataYamlPath, 'w') as yamlFile:
            yaml.dump(self._ontologyInfoDict, yamlFile)

    def _loadOntologyData(self):
        for url, ontologyInfo in self._ontologyInfoDict.items():
            self._ensureOntologyDb(url)

    def _ensureOntologyDb(self, url):
        ontologyInfo = self._ontologyInfoDict[url]
        self._ontologies[url] = owlready2.World(filename=ontologyInfo.getDbPath())

    def _storeOntologyData(self):
        for world in self._ontologies.values():
            world.save()

    def allOntologyUrls(self):
        return list(self._ontologyInfoDict.keys())

    def updateAllOntologies(self):
        for url in self.allOntologyUrls():
            self._updateOntology(url)

    def installOrUpdateOntology(self, url):
        if url not in self._ontologyInfoDict:
            self._installOntology(url)
        else:
            if self._doesOntologyNeedUpdate(url):
                self._updateOntology(url)

    def _installOntology(self, url):
        self._registerOntologyInfo(url)

        print('downloading: ' + url)
        self._downloadOwlFile(url)
        print('downloaded: ' + url)

        print('loading: ' + url)
        self._ensureOntologyDb(url)
        self._parseOwlFileIntoDb(url)
        print('loaded: ' + url)

        self._updateVersionIRIFromOwlFile(url)
        print('updated version IRI: ' + url)

    def _registerOntologyInfo(self, url):
        self._ontologyInfoDict[url] = self.OntologyInfo.createFromUrl(self._ontologyDirPath, url)

    def _getOwlFilePath(self, url):
        return self._ontologyInfoDict[url].getOwlPath()

    def _downloadOwlFile(self, url):
        for i in reversed(range(NUM_DOWNLOAD_RETRIES)):
            try:
                with requests.get(url, stream=True) as response:
                    with open(self._getOwlFilePath(url), 'wb') as out_file:
                        shutil.copyfileobj(response.raw, out_file)
                        if 'etag' in response.headers:
                            self._ontologyInfoDict[url].etag = response.headers['etag']
                        else:
                            raise NotImplementedError('Ontology URL HTTP response without '
                                                      '"ETag" header is not supported')
            except requests.exceptions.RequestException:
                if i == 0:
                    raise

    def _parseOwlFileIntoDb(self, url):
        self._ontologies[url].get_ontology(self._getOwlFilePath(url)).load()

    def _updateVersionIRIFromOwlFile(self, url):
        versionIRI = self._extractVersionIriFromOwlFile(url)
        if not versionIRI:
            raise ValueError('Unable to extract versionIRI from owl file for ontology: '
                             + versionIRI)
        self._ontologyInfoDict[url].versionIRI = versionIRI

    def _extractVersionIriFromOwlFile(self, url):
        edam = False
        if EDAM_ONTOLOGY in url:
            edam = True

        with open(self._getOwlFilePath(url), 'r') as owlFile:
            for line in owlFile:
                if edam:
                    if DOAP_VERSION in line:
                        versionNumber = line.split(DOAP_VERSION)[1].split('<')[0]
                        versionIri = EDAM_ONTOLOGY + 'EDAM_' + versionNumber + '.owl'
                        return versionIri
                else:
                    if VERSION_IRI in line:
                        versionIri = line.split(VERSION_IRI)[1].split('"')[0]
                        return versionIri
            return None

    def getVersionIriForOntology(self, url):
        return self._ontologyInfoDict[url].versionIRI

    def getETagForOntology(self, url):
        return self._ontologyInfoDict[url].etag

    def _doesOntologyNeedUpdate(self, url):
        return True

    def _updateOntology(self, url):
        self._deleteOntology(url)
        self._installOntology(url)

    def _deleteOntology(self, url):
        del self._ontologies[url]

        print('deleting stored content for: ' + url)
        ontologyInfo = self.OntologyInfo.createFromUrl(url)
        os.unlink(ontologyInfo.getOwlPath())
        os.unlink(ontologyInfo.getDbPath())
        print('deleted stored content for: ' + url)

    def searchAllOntologiesForTermId(self, termId):
        return self.searchOntologiesForTermId(self.allOntologyUrls(), termId)

    def searchOntologiesForTermId(self, ontologyUrlList, termId):
        for ontologyUrl in ontologyUrlList:
            termLabel = self.searchOntologyForTermId(ontologyUrl, termId)
            if termLabel:
                return termLabel
        return None

    def searchOntologyForTermId(self, ontologyUrl, termId):
        versionIRI = self.getVersionIRIForOntology(ontologyUrl)
        return self._searchOntologyForTermIdVersioned(ontologyUrl, termId, versionIRI)

    @functools.lru_cache(maxsize=100000)
    def _searchOntologyForTermIdVersioned(self, ontologyUrl, termId, versionIRI):
        assert ontologyUrl in self._ontologyInfoDict
        assert ontologyUrl in self._ontologies
        assert versionIRI == self.getVersionIRIForOntology(ontologyUrl)

        termLabel = self._ontologies[ontologyUrl].search(iri=termId)
        if termLabel:
            return termLabel[0].label[0]
        else:
            return None
