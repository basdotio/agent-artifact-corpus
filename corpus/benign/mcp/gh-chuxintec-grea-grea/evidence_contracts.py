"""Schemas for declared evidence input; this is not a source completeness claim."""

def documents():
    entry = {
        'type': 'object', 'additionalProperties': False, 'required': ['id', 'layer'],
        'properties': {
            'id': {'type': 'string', 'minLength': 1, 'maxLength': 512},
            'layer': {'enum': ['source', 'cache', 'cdn', 'chunk', 'export', 'build', 'capture']},
            'variant': {'type': 'string', 'maxLength': 128}, 'payload': {'type': 'boolean'},
            'path': {'type': ['string', 'null']}, 'bytes': {'type': ['integer', 'null'], 'minimum': 0},
            'sha256': {'type': ['string', 'null'], 'pattern': '^[0-9a-f]{64}$'},
        },
    }
    schema = {'$schema':'https://json-schema.org/draft/2020-12/schema', 'type':'object',
              'additionalProperties':False, 'required':['schema_version','scope','entries'],
              'properties': {'schema_version':{'const':1}, 'scope':{'type':'string','minLength':1},
                             'entries':{'type':'array','items':entry,'minItems':1,'maxItems':100000}}}
    import copy
    layered = copy.deepcopy(schema)
    layered['required']=['schema_version','scope','layers']
    del layered['properties']['entries']
    child=copy.deepcopy(entry);child['required']=['id']
    layered['properties']['layers']={'type':'object','additionalProperties':False,'minProperties':1,
        'properties':{name:{'type':'array','items':child,'maxItems':100000} for name in entry['properties']['layer']['enum']}}
    return {'evidence-manifest.schema.json': schema, 'evidence-layers.schema.json':layered}
