"""Narrow, stdlib-only validation for grea's own brand assets, not arbitrary binaries."""
import math
from pathlib import PurePosixPath
import re
import struct
import xml.etree.ElementTree as ET
import zlib

SIZES=(24,32,64,128,512)


def validate_asset(name,data):
    if len(data)>2*1024*1024:raise ValueError('Brand asset budget exceeded')
    match=re.fullmatch(r'plugin/assets/(icon|logo_light|logo_dark)(?:_(24|32|64|128|512))?\.(png|svg)',name)
    if not match:raise ValueError('Not an approved brand asset path')
    if match[3]=='svg':
        if match[2] or len(data)>32768 or b'<!' in data or b'<?' in data:raise ValueError('Unsupported SVG declaration/size')
        try:root=ET.fromstring(data)
        except ET.ParseError as error:raise ValueError('Invalid SVG') from error
        if root.tag!='{http://www.w3.org/2000/svg}svg' or root.get('viewBox')!='0 0 512 512':raise ValueError('Expected own 512-square SVG')
        allowed={'svg':{'width','height','viewBox'},'rect':{'x','y','width','height','rx','fill'},'polygon':{'points','fill'}}
        for element in root.iter():
            tag=element.tag.removeprefix('{http://www.w3.org/2000/svg}')
            if tag not in allowed or set(element.attrib)-allowed[tag] or element.text and element.text.strip():raise ValueError('SVG scripts, links and unknown constructs refused')
            if tag!='svg' and not re.fullmatch('#[0-9A-Fa-f]{6}',element.get('fill','')):raise ValueError('Solid SVG colors required')
            for key,value in element.attrib.items():
                if key in ('fill','viewBox'):continue
                tokens=value.replace(',',' ').split() if key=='points' else [value]
                if key=='points' and (len(tokens)<6 or len(tokens)>80 or len(tokens)%2):raise ValueError('Invalid polygon')
                for token in tokens:
                    number=float(token)
                    if not math.isfinite(number) or not 0<=number<=512:raise ValueError('SVG coordinate outside canvas')
        return dict(format='svg',width=512,height=512)
    if not match[2] or not data.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Expected approved RGBA PNG')
    offset=8;chunks=[];compressed=bytearray();width=height=None
    while offset<len(data):
        if offset+12>len(data):raise ValueError('Truncated PNG')
        count=struct.unpack('>I',data[offset:offset+4])[0];kind=data[offset+4:offset+8];end=offset+12+count
        if end>len(data) or kind not in (b'IHDR',b'IDAT',b'IEND'):raise ValueError('Unsupported PNG chunk')
        body=data[offset+8:offset+8+count];crc=struct.unpack('>I',data[end-4:end])[0]
        if zlib.crc32(kind+body)&0xffffffff!=crc:raise ValueError('PNG CRC mismatch')
        chunks.append(kind)
        if kind==b'IHDR':
            if len(chunks)!=1 or count!=13:raise ValueError('Invalid PNG header')
            width,height,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',body)
            if width!=height or width!=int(match[2]) or depth!=8 or color!=6 or compression or filtering or interlace:raise ValueError('Expected bounded 8-bit RGBA square PNG')
        elif kind==b'IDAT':compressed.extend(body)
        elif count or end!=len(data):raise ValueError('PNG trailing payload')
        offset=end
    if not chunks or chunks[0]!=b'IHDR' or chunks[-1]!=b'IEND' or b'IDAT' not in chunks:raise ValueError('Incomplete PNG')
    expected=height*(1+width*4);decoder=zlib.decompressobj();pixels=decoder.decompress(bytes(compressed),expected+1)
    if len(pixels)!=expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:raise ValueError('PNG pixel stream differs from dimensions')
    if any(pixels[y*(1+width*4)]>4 for y in range(height)):raise ValueError('Invalid PNG row filter')
    return dict(format='png',width=width,height=height,alpha_channel=True)


def validate_interface(manifest,read):
    interface=manifest.get('interface',{})
    for key in ('composerIcon','logo','logoDark'):
        if key not in interface:continue
        value=interface[key]
        if not isinstance(value,str) or not value.startswith('./') or '\\' in value or '..' in value.split('/'):raise ValueError('Local brand path required')
        path=PurePosixPath(value[2:]).as_posix()
        if path.startswith('plugin/'):source=path
        elif path.startswith('assets/'):source='plugin/'+path
        else:raise ValueError('Brand icon must stay in plugin assets')
        try:data=read(path)
        except (KeyError,OSError) as error:raise ValueError('Missing packaged brand asset: '+path) from error
        validate_asset(source,data)
    if 'brandColor' in interface and not re.fullmatch('#[0-9a-fA-F]{6}',interface['brandColor']):raise ValueError('Invalid brand color')
