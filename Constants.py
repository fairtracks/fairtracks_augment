
TRACKS = 'tracks'
STUDIES = 'studies'
EXPERIMENTS = 'experiments'
SAMPLES = 'samples'
JSON_CATEGORIES = [TRACKS, EXPERIMENTS, STUDIES, SAMPLES]

EXPERIMENT_SCHEMA_URL = 'https://raw.githubusercontent.com/fairtracks/fairtracks_standard/v1/current_test/json/schema/fairtracks_experiment.schema.json'
SAMPLE_SCHEMA_URL = 'https://raw.githubusercontent.com/fairtracks/fairtracks_standard/v1/current_test/json/schema/fairtracks_sample.schema.json'
TRACK_SCHEMA_URL = 'https://raw.githubusercontent.com/fairtracks/fairtracks_standard/v1/current_test/json/schema/fairtracks_track.schema.json'
SCHEMAS = {EXPERIMENTS: EXPERIMENT_SCHEMA_URL, SAMPLES: SAMPLE_SCHEMA_URL, TRACKS: TRACK_SCHEMA_URL}

TERM_ID = 'term_id'
PROPERTIES = 'properties'
ONTOLOGY = 'ontology'
TERM_LABEL = 'term_label'
DOC_INFO = 'doc_info'
DOC_ONTOLOGY_VERSIONS = 'doc_ontology_versions'
FILE_NAME = 'file_name'
FILE_URL = 'file_url'

VERSION_IRI = '<owl:versionIRI rdf:resource="'
DOAP_VERSION = '<doap:Version>'
EDAM_ONTOLOGY = 'http://edamontology.org/'

SAMPLE_TYPE_MAPPING = {'http://purl.obolibrary.org/obo/NCIT_C12508':['sample_type', 'cell_type'],
                       'http://purl.obolibrary.org/obo/NCIT_C12913':['sample_type', 'abnormal_cell_type'],
                       'http://purl.obolibrary.org/obo/NCIT_C16403':['sample_type', 'cell_line'],
                       'http://purl.obolibrary.org/obo/NCIT_C103199':['sample_type', 'organism_part']}

BIOSPECIMEN_CLASS_PATH = ['biospecimen_class', 'term_id']
SAMPLE_TYPE_SUMMARY_PATH = ['sample_type', 'summary']
EXPERIMENT_TARGET_PATHS = [['target', 'sequence_feature', 'term_label'], ['target', 'gene_id'],
                           ['target', 'gene_product_type', 'term_label'],
                           ['target', 'macromolecular_structure', 'term_label'],
                           ['target', 'phenotype', 'term_label']]

TARGET_DETAILS_PATH = ['target', 'target_details']
TARGET_SUMMARY_PATH = ['target', 'summary']
TRACK_FILE_URL_PATH = ['file_url']

SCHEMA_FOLDER_PATH = 'schema'

ONTOLOGY_FOLDER_PATH = 'ontologies'
