import os
from pathlib import Path

TRACKS = 'tracks'
STUDIES = 'studies'
EXPERIMENTS = 'experiments'
SAMPLES = 'samples'

SCHEMA_URL_PART1 = 'https://raw.githubusercontent.com/fairtracks/fairtracks_standard/'
SCHEMA_URL_PART2 = '/current/json/schema/fairtracks.schema.json'
TOP_SCHEMA_FN = 'fairtracks.schema.json'

TERM_ID = 'term_id'
ONTOLOGY = 'ontology'
TERM_LABEL = 'term_label'
DOC_ONTOLOGY_VERSIONS_NAMES = {'doc_info': 'doc_ontology_versions',
                               'document': 'ontology_versions'}
HAS_AUGMENTED_METADATA = {'doc_info': 'has_augmented_metadata',
                          'document': 'has_augmented_metadata'}
FILE_NAME = 'file_name'
FILE_URL = 'file_url'
ITEMS = 'items'
PROPERTIES = 'properties'

VERSION_IRI = '<owl:versionIRI rdf:resource="'
DOAP_VERSION = '<doap:Version>'
EDAM_ONTOLOGY = 'http://edamontology.org/'

IDENTIFIERS_API_URL = 'http://resolver.api.identifiers.org/'
NCBI_TAXONOMY_RESOLVER_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=taxonomy&retmode=json'

SAMPLE_TYPE_MAPPING = {'http://purl.obolibrary.org/obo/NCIT_C12508':['sample_type', 'cell_type'],
                       'http://purl.obolibrary.org/obo/NCIT_C12913':['sample_type', 'abnormal_cell_type'],
                       'http://purl.obolibrary.org/obo/NCIT_C16403':['sample_type', 'cell_line'],
                       'http://purl.obolibrary.org/obo/NCIT_C103199':['sample_type', 'organism_part']}
SAMPLE_ORGANISM_PART_PATH = ['sample_type', 'organism_part', 'term_label']
SAMPLE_DETAILS_PATH = ['sample_type', 'details']

BIOSPECIMEN_CLASS_PATH = ['biospecimen_class', 'term_id']
SAMPLE_TYPE_SUMMARY_PATH = ['sample_type', 'summary']
EXPERIMENT_TARGET_PATHS = [['target', 'sequence_feature', 'term_label'], ['target', 'gene_id'],
                           ['target', 'gene_product_type', 'term_label'],
                           ['target', 'macromolecular_structure', 'term_label'],
                           ['target', 'phenotype', 'term_label']]

TARGET_DETAILS_PATH = ['target', 'details']
TARGET_SUMMARY_PATH = ['target', 'summary']
TRACK_FILE_URL_PATH = ['file_url']
TRACK_FILE_NAME_PATH = ['file_name']
SPECIES_ID_PATH = ['species_id']
SPECIES_NAME_PATH = ['species_name']

NUM_DOWNLOAD_RETRIES = 3
REQUEST_TIMEOUT = 10
BACKOFF_FACTOR = 0
DEFAULT_USERDATA_DIR = os.path.join(Path.home(), '.fairtracks_augment')
FILECACHE_DIR = 'file_cache'
ONTOLOGY_DIR = 'ontologies'
ONTOLOGY_METADATA_FILE = 'ontologies.yaml'

RESOLVED_RESOURCES = 'resolvedResources'
