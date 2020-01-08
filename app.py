import json

from flask import Flask, jsonify, make_response, abort, request

from AppData import AppData
from CommonFunctions import setInDict, getFilenameFromUrl, getFromDict, makeStrPathFromList, \
    getOntologyFilePath
from Constants import TRACKS, \
    EXPERIMENTS, SAMPLES, TERM_LABEL, DOC_INFO, \
    DOC_ONTOLOGY_VERSIONS, FILE_NAME, VERSION_IRI, DOAP_VERSION, EDAM_ONTOLOGY, \
    SAMPLE_TYPE_MAPPING, BIOSPECIMEN_CLASS_PATH, SAMPLE_TYPE_SUMMARY_PATH, EXPERIMENT_TARGET_PATHS, \
    TARGET_DETAILS_PATH, TARGET_SUMMARY_PATH, TRACK_FILE_URL_PATH

app = Flask(__name__)

appData = AppData()


@app.route('/')
def index():
    return 'OK'


@app.errorhandler(400)
def custom400(error):
    response = jsonify({'message': error.description})
    return make_response(response, 400)


@app.route('/autogenerate', methods=['POST'])
def autogenerate():
    data = json.loads(request.data)
    autogenerateFields(data)

    return data


def addOntologyVersions(data):
    if DOC_INFO in data:
        docInfo = data[DOC_INFO]
        if DOC_ONTOLOGY_VERSIONS not in docInfo:
            docInfo[DOC_ONTOLOGY_VERSIONS] = {}

        docOntologyVersions = docInfo[DOC_ONTOLOGY_VERSIONS]
        docUrls = docOntologyVersions.keys()

        urlAndVersions = []
        for url, ontology in appData.getOntologies().items():
            if url in docUrls:
                continue
            fn = getOntologyFilePath(url)
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


def generateTermLabels(data):
    for category, paths in appData.getPathsWithOntologyUrls().items():
        for item in data[category]:
            for path, ontologyUrls in paths:
                try:
                    termIdVal = getFromDict(item, path)
                except KeyError:
                    continue

                termLabelVal = ''
                for url in ontologyUrls:
                    ontology = appData.getOntologies()[url]
                    termLabelSearch = ontology.search(iri=termIdVal)
                    if termLabelSearch:
                        termLabelVal = termLabelSearch[0].label[0]
                    if termLabelVal:
                        break

                if termLabelVal:
                    setInDict(item, path[:-1] + [TERM_LABEL], termLabelVal)
                else:
                    abort(400, 'Item ' + termIdVal + ' not found in ontologies ' + str(ontologyUrls)
                          + ' (path in json: ' + makeStrPathFromList(path, category) + ')')


def addSampleSummary(data):
    samples = data[SAMPLES]
    for sample in samples:
        biospecimenTermId = getFromDict(sample, BIOSPECIMEN_CLASS_PATH)
        if biospecimenTermId in SAMPLE_TYPE_MAPPING:
            sampleTypeVal = getFromDict(sample, SAMPLE_TYPE_MAPPING[biospecimenTermId])
            if TERM_LABEL in sampleTypeVal:
                setInDict(sample, SAMPLE_TYPE_SUMMARY_PATH, sampleTypeVal[TERM_LABEL])
        else:
            abort(400, 'Unexpected biospecimen_class term_id: ' + biospecimenTermId)


def addTargetSummary(data):
    experiments = data[EXPERIMENTS]
    val = ''
    for exp in experiments:
        for path in EXPERIMENT_TARGET_PATHS:
            try:
                val = getFromDict(exp, path)
                break
            except KeyError:
                continue

        if val:
            details = ''
            try:
                details = getFromDict(exp, TARGET_DETAILS_PATH)
            except KeyError:
                pass

            if details:
                val += ' (' + details + ')'
            setInDict(exp, TARGET_SUMMARY_PATH, val)


def addFileName(data):
    tracks = data[TRACKS]
    for track in tracks:
        fileUrl = getFromDict(track, TRACK_FILE_URL_PATH)
        fileName = getFilenameFromUrl(fileUrl)
        setInDict(track, TRACK_FILE_URL_PATH[:-1] + [FILE_NAME], fileName)


def autogenerateFields(data):
    generateTermLabels(data)
    addOntologyVersions(data)
    addFileName(data)
    addSampleSummary(data)
    addTargetSummary(data)
    #print(json.dumps(data))


if __name__ == '__main__':
    appData.initApp()
    app.run(host='0.0.0.0')




