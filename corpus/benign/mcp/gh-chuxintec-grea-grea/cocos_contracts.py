"""Exported structural evidence contract, separate from Unity runtime/asset schemas."""
def documents():
    return {'cocos-evidence.schema.json': {
        '$schema':'https://json-schema.org/draft/2020-12/schema','type':'object',
        'required':['schema_version','tool','implementation_version','source_format','status','errors','unsupported','scope','effects'],
        'properties':{
            'schema_version':{'const':1},'tool':{'enum':['cocos_assets','cocos_modules']},
            'implementation_version':{'type':'string','minLength':1},'source_format':{'type':'string','minLength':1},
            'status':{'enum':['complete','partial','unsupported','error']},
            'source':{'type':'object','properties':{'sha256':{'type':'string','pattern':'^[0-9a-f]{64}$'},'bytes':{'type':'integer','minimum':0}}},
            'selection':{'type':'object'},'outputs':{'type':'array','items':{'type':'object','required':['path','sha256'],'properties':{'path':{'type':'string'},'sha256':{'type':'string','pattern':'^[0-9a-f]{64}$'}}}},
            'errors':{'type':'array','items':{'type':'object','required':['code','location','message'],'properties':{'code':{'type':'string'},'location':{'type':'string'},'message':{'type':'string'}}}},
            'unsupported':{'type':'array'},'scope':{'type':'string'},'effects':{'type':'array','items':{'type':'string'}}},
        'allOf':[{'if':{'properties':{'status':{'const':'complete'}}},'then':{'required':['source','selection','outputs']}}]}}
