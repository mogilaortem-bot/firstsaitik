import sys,json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent
out=Path(sys.argv[1]) if len(sys.argv)>1 else Path.cwd();out.mkdir(parents=True,exist_ok=True)
m=json.loads((root/'manifest.json').read_text());target=out/m['archive_name'];digest=hashlib.sha256()
with target.open('wb') as dest:
    for p in m['parts']:
        data=(root/p['name']).read_bytes()
        assert len(data)==p['size_bytes'] and hashlib.sha256(data).hexdigest()==p['sha256'],p['name']
        dest.write(data);digest.update(data)
assert target.stat().st_size==m['size_bytes'] and digest.hexdigest()==m['sha256']
print(target)
