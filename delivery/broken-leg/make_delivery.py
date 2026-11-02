"""Verify the production kit and create deterministic, portable ZIP files."""
import argparse, hashlib, json, zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[1]/'docs/broken-leg'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def archive(target,files):
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_STORED) as z:
        for name in sorted(files):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            info.create_system=3
            info.external_attr=0o100644<<16
            info.compress_type=zipfile.ZIP_STORED
            z.writestr(info,(SOURCE/name).read_bytes())
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
    return {'file':target.name,'bytes':target.stat().st_size,'sha256':digest(target)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('output');args=parser.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((HERE/'manifest.json').read_text())
    for item in manifest['files']:
        p=SOURCE/item['path']
        assert p.is_file(),p
        assert p.stat().st_size==item['bytes'],p
        assert digest(p)==item['sha256'],p
    names=[x['path'] for x in manifest['files']]
    reports=[archive(out/'Ancient_Bergman_Broken_Leg_Production_Kit.zip',names),
             archive(out/'ElevenLabs_8_Texts_EN.zip',[p for p in names if p.startswith('voiceover/')])]
    check=HERE/'expected_archives.json'
    if check.exists():assert reports==json.loads(check.read_text()),'Archive verification failed'
    (out/'archive_checksums.json').write_text(json.dumps(reports,indent=2)+'\n')
    print(json.dumps(reports),flush=True)

if __name__=='__main__':main()
