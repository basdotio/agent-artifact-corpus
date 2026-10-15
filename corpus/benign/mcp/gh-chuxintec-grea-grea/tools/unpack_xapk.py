"""Extract the supplied XAPK without executing Android code or contacting servers."""
import argparse,pathlib,zipfile,hashlib,json

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('source',type=pathlib.Path);a.add_argument('--output',type=pathlib.Path,required=True);args=a.parse_args()
    P=args.output.resolve()
    if P.exists() and any(P.iterdir()):a.error('Output directory must be empty; preserve earlier evidence')
    P.mkdir(parents=True,exist_ok=True)
    def extract(z,root,select=lambda n:True):
     root=root.resolve();root.mkdir(parents=True,exist_ok=True)
     for name in z.namelist():
      dest=(root/name).resolve()
      if not dest.is_relative_to(root):raise ValueError('Unsafe archive path')
      if select(name):z.extract(name,root)
    with zipfile.ZipFile(args.source) as z:extract(z,P/'Reference')
    (P/'Analysis').mkdir(exist_ok=True)
    for apk in (P/'Reference').glob('*.apk'):
     with zipfile.ZipFile(apk) as z:
      (P/'Analysis').mkdir(exist_ok=True);(P/'Analysis'/f'{apk.stem}-files.txt').write_text('\n'.join(z.namelist()))
      extract(z,P/'Analysis/unpacked'/apk.stem,lambda n:n.startswith('assets/') or n.endswith('libil2cpp.so'))
    digest=hashlib.sha256()
    with args.source.open('rb') as source:
     for block in iter(lambda:source.read(1024*1024),b''):digest.update(block)
    (P/'Analysis/source.json').write_text(json.dumps({'source':str(args.source.resolve()),'sha256':digest.hexdigest()},indent=2))

if __name__ == '__main__':
    main()
