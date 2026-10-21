"""Input contracts for native-exit evidence; no schema is a native-pass waiver."""
MAX_PLAYER_ASSEMBLIES = 256

def documents():
    string={'type':'string','minLength':1,'maxLength':4096}
    identities={'type':'array','items':string,'maxItems':256,'uniqueItems':True}
    return {
      'unity-native-exit-policy.schema.json':{'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object','additionalProperties':False,
        'required':['schema_version','exits'],'properties':{'schema_version':{'const':1},'exits':{'type':'array','maxItems':256,'items':{
          'type':'object','additionalProperties':False,'required':['id','relative_path','symbol','mechanism','reason'],
          'properties':dict({x:string for x in ('id','relative_path','symbol','reason')},mechanism={'enum':['full_source_graph','source_identity_binding','source_lifecycle','dynamic_configuration','source_animation','source_resource_catalog']})}}}},
      'unity-player-policy.schema.json':{'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object','additionalProperties':False,
        'required':['schema_version','required_types'],'properties':dict(schema_version={'const':1},required_types=dict(identities,minItems=1),forbidden_types=identities,forbidden_references=identities,forbidden_assemblies=identities,call_types=identities)},
      'unity-player-manifest.schema.json':{'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object','additionalProperties':False,
        'required':['schema_version','build_id','source_sha256','platform','backend','assemblies'],'properties':{
          'schema_version':{'const':1},'build_id':string,'source_sha256':{'type':'string','pattern':'^[0-9a-f]{64}$'},'platform':string,'backend':{'enum':['Mono','IL2CPP']},
          'assemblies':{'type':'array','minItems':1,'maxItems':MAX_PLAYER_ASSEMBLIES,'items':{'type':'object','additionalProperties':False,'required':['path','sha256'],'properties':{'path':string,'sha256':{'type':'string','pattern':'^[0-9a-f]{64}$'}}}}}}
    }
