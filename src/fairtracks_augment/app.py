import functools
import json
import os
import tempfile
import zipfile

import requests
from flask import Flask, jsonify, make_response, abort, request
from werkzeug.utils import secure_filename

from fairtracks_augment.app_data import AppData
from fairtracks_augment.common import getFilenameFromUrl, makeStrPathFromList
from fairtracks_augment.constants import TRACKS, EXPERIMENTS, SAMPLES, TERM_LABEL, \
    DOC_ONTOLOGY_VERSIONS_NAMES, SAMPLE_TYPE_MAPPING, BIOSPECIMEN_CLASS_PATH, \
    SAMPLE_TYPE_SUMMARY_PATH, EXPERIMENT_TARGET_PATHS, TARGET_DETAILS_PATH, TARGET_SUMMARY_PATH, \
    TRACK_FILE_URL_PATH, SPECIES_ID_PATH, IDENTIFIERS_API_URL, RESOLVED_RESOURCES, \
    NCBI_TAXONOMY_RESOLVER_URL, SPECIES_NAME_PATH, SAMPLE_ORGANISM_PART_PATH, \
    SAMPLE_DETAILS_PATH, HAS_AUGMENTED_METADATA, TRACK_FILE_NAME_PATH
from fairtracks_augment.nested_ordered_dict import NestedOrderedDict

app = Flask(__name__)


@app.route('/')
def index():
    return 'OK'


@app.errorhandler(400)
def custom400(error):
    response = jsonify({'message': error.description})
    return make_response(response, 400)


@app.route('/augment', methods=['POST'])
@app.route('/autogenerate', methods=['POST'])
def augment():
    if 'data' not in request.files:
        abort(400, 'Parameter called data containing FAIRtracks JSON data is required')
    dataJson = request.files['data']

    with tempfile.TemporaryDirectory() as tmpDir:
        dataFn = ''
        if dataJson:
            dataFn = secure_filename(dataJson.filename)
            dataJson.save(os.path.join(tmpDir, dataFn))

        with open(os.path.join(tmpDir, dataFn)) as dataFile:
            data = NestedOrderedDict(json.load(dataFile))

        if 'schemas' in request.files:
            file = request.files['schemas']
            filename = secure_filename(file.filename)
            file.save(os.path.join(tmpDir, filename))

            with zipfile.ZipFile(os.path.join(tmpDir, filename), 'r') as archive:
                archive.extractall(tmpDir)

            appData = AppData(data, tmpDir)
        else:
            appData = AppData(data)

        augmentFields(data, appData)

    return data


def addOntologyVersions(data, appData):
    # Very cumbersome way to support both v1 and v21111 names. Should be
    # refactored. Also no good error message if no document info property is
    # found. 
    # Possibility: store property names in App subclasses instead of
    # constants, create new subclass for new version, load correct subclass
    # based on schema ID.
    for docInfoName in DOC_ONTOLOGY_VERSIONS_NAMES.keys():
        if docInfoName in data:
            docInfo = data[docInfoName]
            docOntologyVersionsName = DOC_ONTOLOGY_VERSIONS_NAMES[docInfoName]
            if docOntologyVersionsName not in docInfo:
                docInfo[docOntologyVersionsName] = {}

            docOntologyVersions = docInfo[docOntologyVersionsName]

    ontologyHelper = appData.ontologyHelper
    for url in ontologyHelper.allOntologyUrls():
        docOntologyVersions[url] = ontologyHelper.getVersionIriForOntology()


def generateTermLabels(data, appData):
    for category in data:
        if not isinstance(data[category], list):
            continue
        for subDict in data[category]:
            for path, ontologyUrls in appData.getPathsWithOntologyUrls():
                if path[0] != category:
                    continue
                subPath = path[1:]

                termIdVal = subDict[subPath]
                ontologyHelper = appData.ontologyHelper
                termLabelVal = ontologyHelper.searchOntologiesForTermId(ontologyUrls, termIdVal)

                if termLabelVal:
                    subDict[subPath[:-1] + [TERM_LABEL]] = termLabelVal
                else:
                    abort(400, 'Item ' + termIdVal + ' not found in ontologies ' + str(ontologyUrls)
                          + ' (path in json: ' + makeStrPathFromList(path, category) + ')')


def addSampleSummary(data):
    samples = data[SAMPLES]
    for sample in samples:
        biospecimenTermId = sample[BIOSPECIMEN_CLASS_PATH]
        if biospecimenTermId in SAMPLE_TYPE_MAPPING:
            sampleTypeVal = sample[SAMPLE_TYPE_MAPPING[biospecimenTermId]]
            if TERM_LABEL in sampleTypeVal:
                summary = sampleTypeVal[TERM_LABEL]
                details = []

                organismPart = sample[SAMPLE_ORGANISM_PART_PATH]
                if summary != organismPart:
                    details.append(organismPart)

                details.append(sample[SAMPLE_DETAILS_PATH])

                if details:
                    summary = "{} ({})".format(summary, ', '.join(details))

                sample[SAMPLE_TYPE_SUMMARY_PATH] = summary
        else:
            abort(400, 'Unexpected biospecimen_class term_id: ' + biospecimenTermId)


def addTargetSummary(data):
    experiments = data[EXPERIMENTS]
    val = ''
    for exp in experiments:
        for path in EXPERIMENT_TARGET_PATHS:
            val = exp.get(path)
            if val is not None:
                break

        if val:
            details = exp.get(TARGET_DETAILS_PATH)
            if details:
                val += ' (' + details + ')'
            exp[TARGET_SUMMARY_PATH] = val


def addFileName(data):
    tracks = data[TRACKS]
    for track in tracks:
        fileUrl = track[TRACK_FILE_URL_PATH]
        fileName = getFilenameFromUrl(fileUrl)
        track[TRACK_FILE_NAME_PATH] = fileName


def addSpeciesName(data):
    samples = data[SAMPLES]
    for sample in samples:
        speciesId = sample[SPECIES_ID_PATH]
        speciesName = getSpeciesNameFromId(speciesId)
        sample[SPECIES_NAME_PATH] = speciesName


@functools.lru_cache(maxsize=1000)
def getSpeciesNameFromId(speciesId):
    providerCode = resolveIdentifier(speciesId)
    speciesName = getSpeciesName(speciesId.split('taxonomy:')[1], providerCode)
    return speciesName


def resolveIdentifier(speciesId):
    url = IDENTIFIERS_API_URL + speciesId
    responseJson = requests.get(url).json()

    for resource in responseJson['payload'][RESOLVED_RESOURCES]:
        if 'providerCode' in resource:
            if resource['providerCode'] == 'ncbi':
                return resource['providerCode']


def getSpeciesName(speciesId, providerCode):
    if providerCode == 'ncbi':
        url = NCBI_TAXONOMY_RESOLVER_URL + '&id=' + str(speciesId)

        for i in range(3):
            try:
                responseJson = requests.get(url).json()
                speciesName = responseJson['result'][speciesId]['scientificname']
                break
            except KeyError:
                pass

        return speciesName


def setAugmentedDataFlag(data):
    for docInfoName in HAS_AUGMENTED_METADATA.keys():
        if docInfoName in data:
            data[docInfoName][HAS_AUGMENTED_METADATA[docInfoName]] = True


def augmentFields(data, appData):
    generateTermLabels(data, appData)
    addOntologyVersions(data, appData)
    addFileName(data)
    addSampleSummary(data)
    addTargetSummary(data)
    addSpeciesName(data)
    setAugmentedDataFlag(data)
    #print(json.dumps(data))


if __name__ == '__main__':
    AppData()  # to initialize ontologies
    app.run(host='0.0.0.0')
