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
VERSION_IRI = '<owl:versionIRI rdf:resource="'
DOAP_VERSION = '<doap:Version>'
EDAM_ONTOLOGY = 'http://edamontology.org/'

SAMPLE_TYPE_MAPPING = {'http://purl.obolibrary.org/obo/NCIT_C12508':['sample_type', 'cell_type'],
                       'http://purl.obolibrary.org/obo/NCIT_C12913':['sample_type', 'abnormal_cell_type'],
                       'http://purl.obolibrary.org/obo/NCIT_C16403':['sample_type', 'cell_line'],
                       'http://purl.obolibrary.org/obo/NCIT_C103199':['sample_type', 'organism_part']}

BIOSPECIMEN_CLASS_PATH = ['biospecimen_class', 'term_id']
SAMPLE_TYPE_SUMMARY_PATH = ['sample_type', 'summary']

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
        if DOC_ONTOLOGY_VERSIONS not in docInfo:
            docInfo[DOC_ONTOLOGY_VERSIONS] = {}

        docOntologyVersions = docInfo[DOC_ONTOLOGY_VERSIONS]
        docUrls = docOntologyVersions.keys()
        print(docUrls)

        urlAndVersions = []
        for url, ontology in ONTOLOGIES.items():
            if url in docUrls:
                print('skipping url: ' + url)
                continue
            fn = getOntologyFilenameFromUrl(url)
            edam = False
            if EDAM_ONTOLOGY in url:
                edam = True
            with open(fn, 'r') as ontoFile:
                for line in ontoFile:
                    if edam:
                        if DOAP_VERSION in line:
                            versionNumber = line.split(DOAP_VERSION)[1].split('<')[0]
                            versionIri = EDAM_ONTOLOGY + 'EDAM_' + versionNumber + '.owl'
                            urlAndVersions.append((url, versionIri))
                            break
                    else:
                        if VERSION_IRI in line:
                            versionIri = line.split(VERSION_IRI)[1].split('"')[0]
                            urlAndVersions.append((url, versionIri))
                            break

        for url, versionIri in urlAndVersions:
            docOntologyVersions[url] = versionIri

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


def addSampleSummary(data):
    samples = data[SAMPLES]
    for sample in samples:
        biospecimenTermId = getFromDict(sample, BIOSPECIMEN_CLASS_PATH)
        sampleTypeVal = getFromDict(sample, SAMPLE_TYPE_MAPPING[biospecimenTermId])
        if TERM_LABEL in sampleTypeVal:
            print('setting summary to: ' + sampleTypeVal[TERM_LABEL])
            setInDict(sample, SAMPLE_TYPE_SUMMARY_PATH, sampleTypeVal[TERM_LABEL])

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
    data = addSampleSummary(data)
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
        fn = getOntologyFilenameFromUrl(url)
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


def getOntologyFilenameFromUrl(url):
    fn = url.rsplit('/', 1)[-1]

    return fn


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




