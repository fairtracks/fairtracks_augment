
TRACKS = 'tracks'
STUDIES = 'studies'
EXPERIMENTS = 'experiments'
SAMPLES = 'samples'
PHENOTYPE = 'phenotype'
JSON_CATEGORIES = [TRACKS, EXPERIMENTS, STUDIES, SAMPLES]

EXPERIMENT_SCHEMA_URL = 'https://raw.githubusercontent.com/fairtracks/fairtracks_standard/v1/current/json/schema/fairtracks_experiment.schema.json'
SAMPLE_SCHEMA_URL = 'https://raw.githubusercontent.com/fairtracks/fairtracks_standard/v1/current/json/schema/fairtracks_sample.schema.json'
TRACK_SCHEMA_URL = 'https://raw.githubusercontent.com/fairtracks/fairtracks_standard/v1/current/json/schema/fairtracks_track.schema.json'
PHENOTYPE_SCHEMA_URL = 'https://raw.githubusercontent.com/fairtracks/fairtracks_standard/v1/current/json/schema/fairtracks_phenotype.schema.json'
SCHEMAS = {EXPERIMENTS: EXPERIMENT_SCHEMA_URL, SAMPLES: SAMPLE_SCHEMA_URL, TRACKS: TRACK_SCHEMA_URL, PHENOTYPE:PHENOTYPE_SCHEMA_URL }

TERM_ID = 'term_id'
PROPERTIES = 'properties'
ONTOLOGY = 'ontology'
TERM_LABEL = 'term_label'
DOC_INFO = 'doc_info'
DOC_ONTOLOGY_VERSIONS = 'doc_ontology_versions'
HAS_AUGMENTED_METADATA = 'has_augmented_metadata'
FILE_NAME = 'file_name'
FILE_URL = 'file_url'

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
SPECIES_ID_PATH = ['species_id']
SPECIES_NAME_PATH = ['species_name']

SCHEMA_FOLDER_PATH = 'schema'

ONTOLOGY_FOLDER_PATH = 'ontologies'

RESOLVED_RESOURCES = 'resolvedResources'
