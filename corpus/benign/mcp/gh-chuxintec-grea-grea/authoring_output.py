"""Create-only native-authoring candidates and bounded C# identities."""
import json
import re
from grea.host.paths import Path
from grea.safe_paths import disjoint
from grea.data_io import sha, encode
VERSION = "0.1.0"

KEYWORDS = set('abstract as base bool break byte case catch char checked class const continue decimal default delegate do double else enum event explicit extern false finally fixed float for foreach goto if implicit in int interface internal is lock long namespace new null object operator out override params private protected public readonly ref return sbyte sealed short sizeof stackalloc static string struct switch this throw true try typeof uint ulong unchecked unsafe ushort using virtual void volatile while'.split())


def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}',value) or value in KEYWORDS:
        raise ValueError('Expected a bounded non-keyword C# identifier')
    return value


def write_candidate(output, files, sources, identity):
    output=Path(output).absolute()
    if any(p.is_symlink() for p in (output,*output.parents)): raise ValueError('Linked output rejected')
    output=disjoint(output,*sources)
    manifest=dict(schema_version=1,implementation_version=VERSION,identity=identity,files={k:sha(v) for k,v in sorted(files.items())})
    files=dict(files,**{'generation.json':encode(manifest)})
    if output.exists():
        actual={p.relative_to(output).as_posix():sha(p.read_bytes()) for p in output.rglob('*') if p.is_file() and not p.is_symlink()}
        if any(p.is_symlink() for p in output.rglob('*')) or actual!={k:sha(v) for k,v in files.items()}:
            raise ValueError('Generation conflict: candidate changed or input differs; choose a new output for review')
        status='unchanged'
    else:
        output.mkdir(parents=True,exist_ok=False)
        for name,raw in files.items():
            target=output/name;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as stream: stream.write(raw)
        status='candidate_created'
    return dict(schema_version=1,status=status,identity=identity,files=manifest['files'],output=str(output),runtime_json=False)
