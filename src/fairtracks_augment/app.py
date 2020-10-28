import functools
import json
import os
import tempfile
import zipfile

import requests
from flask import Flask, jsonify, make_response, abort, request
from werkzeug.utils import secure_filename

from fairtracks_augment.app_data import AppData
from fairtracks_augment.common import get_filename_from_url, make_str_path_from_list
from fairtracks_augment.constants import TRACKS, EXPERIMENTS, SAMPLES, TERM_LABEL, \
    DOC_ONTOLOGY_VERSIONS_NAMES, SAMPLE_TYPE_MAPPING, BIOSPECIMEN_CLASS_PATH, \
    SAMPLE_TYPE_SUMMARY_PATH, EXPERIMENT_TARGET_PATHS, TARGET_DETAILS_PATH, TARGET_SUMMARY_PATH, \
    TRACK_FILE_URL_PATH, SPECIES_ID_PATH, IDENTIFIERS_API_URL, RESOLVED_RESOURCES, \
    NCBI_TAXONOMY_RESOLVER_URL, SPECIES_NAME_PATH, SAMPLE_ORGANISM_PART_PATH, \
    SAMPLE_DETAILS_PATH, HAS_AUGMENTED_METADATA, TRACK_FILE_NAME_PATH, NUM_DOWNLOAD_RETRIES
from fairtracks_augment.nested_ordered_dict import NestedOrderedDict

app = Flask(__name__)


@app.route('/')
def index():
    return 'OK'


@app.errorhandler(400)
def custom_400(error):
    response = jsonify({'message': error.description})
    return make_response(response, 400)


@app.route('/augment', methods=['POST'])
@app.route('/autogenerate', methods=['POST'])
def augment():
    if 'data' not in request.files:
        abort(400, 'Parameter called data containing FAIRtracks JSON data is required')
    data_json = request.files['data']

    with tempfile.TemporaryDirectory() as tmp_dir:
        data_fn = ''
        if data_json:
            data_fn = secure_filename(data_json.filename)
            data_json.save(os.path.join(tmp_dir, data_fn))

        with open(os.path.join(tmp_dir, data_fn)) as data_file:
            data = NestedOrderedDict(json.load(data_file))

        if 'schemas' in request.files:
            file = request.files['schemas']
            filename = secure_filename(file.filename)
            file.save(os.path.join(tmp_dir, filename))

            with zipfile.ZipFile(os.path.join(tmp_dir, filename), 'r') as archive:
                archive.extractall(tmp_dir)

            app_data = AppData(data, tmp_dir)
        else:
            app_data = AppData(data)

        augment_fields(data, app_data)

    return data


def add_ontology_versions(data, app_data):
    # Very cumbersome way to support both v1 and v2 names. Should be
    # refactored. Also no good error message if no document info property is
    # found. 
    # Possibility: store property names in App subclasses instead of
    # constants, create new subclass for new version, load correct subclass
    # based on schema ID.
    for doc_info_name in DOC_ONTOLOGY_VERSIONS_NAMES.keys():
        if doc_info_name in data:
            doc_info = data[doc_info_name]
            doc_ontology_versions_name = DOC_ONTOLOGY_VERSIONS_NAMES[doc_info_name]
            if doc_ontology_versions_name not in doc_info:
                doc_info[doc_ontology_versions_name] = {}

            doc_ontology_versions = doc_info[doc_ontology_versions_name]

    ontology_helper = app_data.ontology_helper
    for url in ontology_helper.all_ontology_urls():
        doc_ontology_versions[url] = ontology_helper.get_version_iri_for_ontology()


def generate_term_labels(data, app_data):
    for category in data:
        if not isinstance(data[category], list):
            continue
        for sub_dict in data[category]:
            for path, ontology_urls in app_data.get_paths_with_ontology_urls():
                if path[0] != category:
                    continue
                subPath = path[1:]

                term_id_val = sub_dict[subPath]
                helper = app_data.ontology_helper
                term_label_val = helper.search_ontologies_for_term_id(ontology_urls, term_id_val)

                if term_label_val:
                    sub_dict[subPath[:-1] + [TERM_LABEL]] = term_label_val
                else:
                    abort(400, 'Item ' + term_id_val + ' not found in ontologies '
                          + str(ontology_urls) + ' (path in json: '
                          + make_str_path_from_list(path, category) + ')')


def add_sample_summary(data):
    samples = data[SAMPLES]
    for sample in samples:
        biospecimen_term_id = sample[BIOSPECIMEN_CLASS_PATH]
        if biospecimen_term_id in SAMPLE_TYPE_MAPPING:
            sample_type_val = sample[SAMPLE_TYPE_MAPPING[biospecimen_term_id]]
            if TERM_LABEL in sample_type_val:
                summary = sample_type_val[TERM_LABEL]
                details = []

                organism_part = sample[SAMPLE_ORGANISM_PART_PATH]
                if summary != organism_part:
                    details.append(organism_part)

                details.append(sample[SAMPLE_DETAILS_PATH])

                if details:
                    summary = "{} ({})".format(summary, ', '.join(details))

                sample[SAMPLE_TYPE_SUMMARY_PATH] = summary
        else:
            abort(400, 'Unexpected biospecimen_class term_id: ' + biospecimen_term_id)


def add_target_summary(data):
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


def add_file_name(data):
    tracks = data[TRACKS]
    for track in tracks:
        file_url = track[TRACK_FILE_URL_PATH]
        file_name = get_filename_from_url(file_url)
        track[TRACK_FILE_NAME_PATH] = file_name


def add_species_name(data):
    samples = data[SAMPLES]
    for sample in samples:
        species_id = sample[SPECIES_ID_PATH]
        species_name = get_species_name_from_id(species_id)
        sample[SPECIES_NAME_PATH] = species_name


@functools.lru_cache(maxsize=1000)
def get_species_name_from_id(species_id):
    provider_code = resolve_identifier(species_id)
    species_name = get_species_name(species_id.split('taxonomy:')[1], provider_code)
    return species_name


def resolve_identifier(species_id):
    url = IDENTIFIERS_API_URL + species_id
    response_json = requests.get(url).json()

    for resource in response_json['payload'][RESOLVED_RESOURCES]:
        if 'providerCode' in resource:
            if resource['providerCode'] == 'ncbi':
                return resource['providerCode']


def get_species_name(species_id, provider_code):
    if provider_code == 'ncbi':
        url = NCBI_TAXONOMY_RESOLVER_URL + '&id=' + str(species_id)

        for i in reversed(range(NUM_DOWNLOAD_RETRIES)):
            try:
                response_json = requests.get(url).json()
                species_name = response_json['result'][species_id]['scientificname']
                break
            except (requests.exceptions.RequestException, KeyError) as e:
                if i == 0:
                    raise ValueError(
                        "Unable to retrieve species record for species_id "
                        "'{}' in provider '{}': {}".format(species_id, provider_code, e)
                    )

        return species_name


def set_augmented_data_flag(data):
    for doc_info_name in HAS_AUGMENTED_METADATA.keys():
        if doc_info_name in data:
            data[doc_info_name][HAS_AUGMENTED_METADATA[doc_info_name]] = True


def augment_fields(data, app_data):
    generate_term_labels(data, app_data)
    add_ontology_versions(data, app_data)
    add_file_name(data)
    add_sample_summary(data)
    add_target_summary(data)
    add_species_name(data)
    set_augmented_data_flag(data)
    # print(json.dumps(data))


if __name__ == '__main__':
    AppData()  # to initialize ontologies
    app.run(host='0.0.0.0')
