import json
import urllib.request

from flask import Flask
from owlready2 import *

app = Flask(__name__)

EXPERIMENT_SCHEMA_URL = 'https://raw.githubusercontent.com/fairtracks/fairtracks_standard/v1/current_test/json/schema/fairtracks_experiment.schema.json'
SAMPLE_SCHEMA_URL = 'https://raw.githubusercontent.com/fairtracks/fairtracks_standard/v1/current_test/json/schema/fairtracks_sample.schema.json'
TRACK_SCHEMA_URL = 'https://raw.githubusercontent.com/fairtracks/fairtracks_standard/v1/current_test/json/schema/fairtracks_track.schema.json'

TRACKS = 'tracks'
STUDIES = 'studies'
EXPERIMENTS = 'experiments'
SAMPLES = 'samples'

SCHEMAS = {EXPERIMENTS:EXPERIMENT_SCHEMA_URL, SAMPLES:SAMPLE_SCHEMA_URL, TRACKS:TRACK_SCHEMA_URL}

ONTOLOGIES = {}
itemToOntologyMapping = {}
termIdPaths = {}

JSON_CATEGORIES = [TRACKS, EXPERIMENTS, STUDIES, SAMPLES]

TERM_ID = 'term_id'
PROPERTIES = 'properties'
ONTOLOGY = 'ontology'
TERM_LABEL = 'term_label'
DOC_INFO = 'doc_info'
DOC_ONTOLOGY_VERSIONS = 'doc_ontology_versions'
FILE_NAME = 'file_name'
FILE_URL = 'file_url'
fileUrlPath = []


pathsWithOntologyUrls = defaultdict(list)


@app.route('/')
def index():
    return 'OK'


@app.route('/autogenerate', methods=['POST'])
def autogenerate():
    #data = json.loads(request.data)
    with open('fairtracks.no-auto.json', 'r') as f:
        data = json.load(f)
        autogenerateFields(data)

    return data


def addOntologyVersions(data):
    if DOC_INFO in data:
        docInfo = data[DOC_INFO]
        if not DOC_ONTOLOGY_VERSIONS in docInfo:
            docInfo[DOC_ONTOLOGY_VERSIONS] = {}

        docOntologyVersions = docInfo[DOC_ONTOLOGY_VERSIONS]

        for url, ontology in ONTOLOGIES.items():
            pass

    return data


def generateTermLabels(data):
    for category in pathsWithOntologyUrls.keys():
        print(category)
        for item in data[category]:
            for path, ontologyUrls in pathsWithOntologyUrls[category]:
                print(path)
                try:
                    termIdVal = getFromDict(item, path)
                except KeyError:
                    continue

                print(termIdVal)
                termLabelVal = ''
                for url in ontologyUrls:
                    ontology = ONTOLOGIES[url]
                    termLabelVal = ontology.search(iri=termIdVal)[0].label[0]
                    if termLabelVal:
                        break

                print(termLabelVal)
                setInDict(item, path[:-1] + [TERM_LABEL], termLabelVal)

    return data

def addFileName(data):
    tracks = data[TRACKS]
    for track in tracks:
        fileUrl = getFromDict(track, fileUrlPath)
        fileName = fileUrl.rsplit('/', 1)[-1]
        setInDict(track, fileUrlPath[:-1] + [FILE_NAME], fileName)

    return data


def getFromDict(dataDict, pathList):
    for k in pathList:
        dataDict = dataDict[k]
    return dataDict


def setInDict(dataDict, pathList, value):
    getFromDict(dataDict, pathList[:-1])[pathList[-1]] = value


def autogenerateFields(data):
    data = generateTermLabels(data)
    data = addOntologyVersions(data)
    data = addFileName(data)
    print(json.dumps(data))


def getPathsToElement(data, key, path=[]):
    if isinstance(data, dict):
        for k,v in data.items():
            newPath = path + [k]
            if k == key:
                yield newPath
            else:
                for el in getPathsToElement(v, key, newPath):
                    yield el
    elif isinstance(data, list):
        for i in data:
            for el in getPathsToElement(i, key, path):
                yield el


def getPathsToElementInSchema(data, key):
    pathsWithOntologyUrls = []

    for path in getPathsToElement(data, key):
        ontologyUrls = []
        el = getFromDict(data, path)
        if ONTOLOGY in el:
            ontologyUrls = el[ONTOLOGY]
            if not isinstance(ontologyUrls, list):
                ontologyUrls = [ontologyUrls]
        newPath = [p for p in path if p != PROPERTIES]
        if ontologyUrls:
            pathsWithOntologyUrls.append((newPath, ontologyUrls))

    return pathsWithOntologyUrls

def downloadOntologyFiles(ontologyUrls):
    for url in ontologyUrls:
        print('loading ' + str(url))
        fn = url.rsplit('/', 1)[-1]
        if not os.path.exists(fn):
            ontoFile, _ = urllib.request.urlretrieve(url, fn)

        ontology = owlready2.get_ontology(fn)
        ontology.load()
        print('loaded: ' + url)
        ONTOLOGIES[url] = ontology


def initOntologies():
    ontologyUrls = set()

    for category, url in SCHEMAS.items():
        schemaFn, _ = urllib.request.urlretrieve(url, category + '.json')

        with open(schemaFn, 'r') as schemaFile:
            schemaJson = json.load(schemaFile)
            pathsWithOntologyUrls[category].extend(getPathsToElementInSchema(schemaJson[PROPERTIES], TERM_ID))

            if category == TRACKS:
                for path in getPathsToElement(schemaJson[PROPERTIES], FILE_URL):
                    fileUrlPath.extend(path)
                    break
                if PROPERTIES in fileUrlPath:
                    fileUrlPath.remove(PROPERTIES)
                print(fileUrlPath)

        for path, ontoUrls in pathsWithOntologyUrls[category]:
            for ontoUrl in ontoUrls:
                ontologyUrls.add(ontoUrl)

    print(pathsWithOntologyUrls)
    downloadOntologyFiles(ontologyUrls)


def dictPaths(myDict, path=[]):
    pass
    # for k,v in myDict.iteritems():
    #     newPath = path + [k]
    #     if isinstance(v, dict):
    #         for item in dictPaths(v, newPath):
    #             yield item
    #     else:
    #         # track attributes should not have 'tracks->' in the attribute name
    #         if newPath[0] == 'tracks':
    #             yield SEP.join(newPath[1:]), str(v)
    #         else:
    #             if isinstance(v, list):
    #                 yield SEP.join(newPath), ARRAY_SEP.join(v)
    #             else:
    #                 yield SEP.join(newPath), str(v)



if __name__ == '__main__':
    initOntologies()
    autogenerate()
    #app.run(host='0.0.0.0')




