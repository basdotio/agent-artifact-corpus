"""Versioned bounded authoring input formats; semantic preflight remains in tools."""
def validate(filename, value):
    from jsonschema import Draft202012Validator,ValidationError
    try:Draft202012Validator(documents()[filename]).validate(value)
    except ValidationError as error:raise ValueError('Authoring contract: '+error.message) from error


def documents():
    def obj(properties):return dict(type='object',additionalProperties=False,required=list(properties),properties=properties)
    def array(items,minimum=0,maximum=64):return dict(type='array',items=items,minItems=minimum,maxItems=maximum)
    number=dict(type='number',minimum=-100000,maximum=100000)
    def vector(length,integer=False):return dict(type='array',minItems=length,maxItems=length,items=dict(type='integer',minimum=0,maximum=100000) if integer else number)
    name=dict(type='string',pattern='^[A-Za-z_][A-Za-z0-9_]{0,63}$')
    field=obj(dict(name=name,type=dict(enum=['int','string','bool']),nullable=dict(type='boolean'),min=dict(type='integer',minimum=-2147483648,maximum=2147483647),max=dict(type='integer',minimum=-2147483648,maximum=2147483647)))
    field['required']=['name','type']
    config=obj(dict(schema_version=dict(const=1),namespace=dict(type='string',maxLength=200),name=name,key=name,fields=array(field,1)))
    sprite=obj(dict(name=name,image=dict(type='string',minLength=1,maxLength=256),rect=vector(4,True),rotated_cw=dict(type='boolean'),original_size=vector(2,True),offset=vector(2,True),pivot=vector(2),border=vector(4,True),pixels_per_unit=dict(type='number',exclusiveMinimum=0,maximum=10000)))
    curve=obj(dict(target=dict(type='string'),property=dict(enum=['m_Local'+kind+'.'+axis for kind in ('Position','Scale') for axis in ('x','y','z')]),keys=array(vector(2),2,10000)))
    clip=obj(dict(name=name,duration=dict(type='number',exclusiveMinimum=0,maximum=600),loop=dict(type='boolean'),curves=array(curve,1,128),events=array(obj(dict(time=number,function=dict(const='Pulse'))),0,128)))
    recipe=obj(dict(schema_version=dict(const=1),sprites=array(sprite),targets=array(obj(dict(path=dict(type='string'),scale=vector(3)))),clips=array(clip)))
    return {filename:dict(schema,**{'$schema':'https://json-schema.org/draft/2020-12/schema'}) for filename,schema in [('unity-config-authoring.schema.json',config),('unity-native-assets.schema.json',recipe)]}
