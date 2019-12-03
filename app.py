import json
from collections import OrderedDict
from flask import Flask, request
import urllib.request

from owlready2 import *


app = Flask(__name__)

EXPERIMENT_SCHEMA_URL = 'https://raw.githubusercontent.com/fairtracks/fairtracks_standard/master/json/schema/fairtracks_experiment.schema.json'
SAMPLE_SCHEMA_URL = 'https://raw.githubusercontent.com/fairtracks/fairtracks_standard/master/json/schema/fairtracks_sample.schema.json'
TRACK_SCHEMA_URL = 'https://raw.githubusercontent.com/fairtracks/fairtracks_standard/master/json/schema/fairtracks_track.schema.json'

EXPERIMENT_SCHEMA_LABEL = 'experimentSchema'
SAMPLE_SCHEMA_LABEL = 'sampleSchema'
TRACK_SCHEMA_LABEL = 'trackSchema'

SCHEMAS = {(EXPERIMENT_SCHEMA_LABEL, EXPERIMENT_SCHEMA_URL), (SAMPLE_SCHEMA_LABEL, SAMPLE_SCHEMA_URL), (TRACK_SCHEMA_LABEL, TRACK_SCHEMA_URL)}


@app.route('/')
def index():
    return 'OK'


@app.route('/autogenerate', methods=['POST'])
def to_gsuite():

    data = json.loads(request.data, object_pairs_hook=OrderedDict)
    for item in data:
        autogenerateFields(item)

    return data


def autogenerateFields(data):
    print(data)
    # if 'tracks' not in data:
    #     return
    #
    # trackData = OrderedDict()
    # for path, value in dictPaths(data['tracks']):
    #     trackData[path] = value
    #
    # dataWithoutTracks = data.copy()
    # dataWithoutTracks.pop('tracks')
    #
    # noTrackData = OrderedDict()
    # for path, value in dictPaths(dataWithoutTracks):
    #     noTrackData[path] = value
    #
    # # # order the columns as in input json with track attributes first
    # resultOrdered = OrderedDict()
    # for col in trackData:
    #     if trackData[col]:
    #         resultOrdered[col] = trackData[col]
    #
    # for col in noTrackData:
    #     if noTrackData[col]:
    #         resultOrdered[col] = noTrackData[col]
    #
    # uri = resultOrdered.pop(URL_PATH, None)
    # if not uri:
    #     return
    # gsuite.addTrack(GSuiteTrack(uri=uri, attributes=resultOrdered, title=resultOrdered[TITLE_PATH],
    #                             genome=resultOrdered[GENOME_PATH]))


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


def initOntologies():
    experimentSchemaFn, _ = urllib.request.urlretrieve(EXPERIMENT_SCHEMA_URL, 'experiment_schema.json')
    sampleSchemaFn, _ = urllib.request.urlretrieve(SAMPLE_SCHEMA_URL, 'sample_schema.json')
    trackSchemaFn, _ = urllib.request.urlretrieve(TRACK_SCHEMA_URL, 'track_schema.json')

    ontologies = {}
    for name, url in SCHEMAS:
        schemaFn, _ = urllib.request.urlretrieve(url, name + '.json')
        ontologies[name] = {}

        with open(schemaFn, 'r') as schemaFile:
            schema = json.load(schemaFile)
            for key, item in schema['properties'].items():
                if 'properties' in item:
                    if 'term_id' in item['properties']:
                        if 'ontology' in item['properties']['term_id']:
                            val = item['properties']['term_id']['ontology']
                            if type(val) == list:
                                ontologies[name][key] = val
                            else:
                                ontologies[name][key] = [val]

    print(ontologies)


    pass


if __name__ == '__main__':
    initOntologies()
    #app.run(host='0.0.0.0')




