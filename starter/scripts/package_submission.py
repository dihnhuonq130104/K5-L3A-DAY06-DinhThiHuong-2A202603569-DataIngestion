"""Package allowed source/results with hashes; exclude credentials and runtime caches."""
import sys
from pathlib import Path
import json
import re
import zipfile
from hashlib import sha256
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from starter.src.project import ROOT,RESULTS,read_json,now,digest
from starter.src.pipeline import validate_frozen


def main():
    validate_frozen()
    final=read_json(ROOT/'report/finalization.json')
    assert digest(ROOT/final['report'])==final['sha256'],'Finalized report changed; packaging stopped'
    required=['STUDENT.md','README.md','SUBMISSION_INDEX.md',
              'report/individual/2A202603569_DinhThiHuong.md','data/manifest.json',
              'benchmark/questions.json','benchmark/freeze.json','artifacts/experiment_log.csv',
              'results/traces.json','results/metrics.csv','results/qualitative_audit.json']
    assert all((ROOT/p).is_file() for p in required),'Missing required submission artifact'
    review=read_json(RESULTS/'qualitative_audit.json')
    assert review['status']=='completed_assisted_assessment' and review['human_confirmed'] is False
    assert review['checks']=={'source_pages':43,'gold_quotes':25,'coherence_rows':30,'grounding_rows':30,'metadata_rows':90}
    allow_dirs={'tests','starter','configs','benchmark','artifacts','results','data','docs','report','.streamlit'}
    allow_root={'.gitignore','.env.example','app.py','requirements.txt','requirements.lock.txt','README.md','STUDENT.md','SUBMISSION_INDEX.md','SUBMISSION_CHECKLIST.md','PRODUCT.md','DESIGN.md'}
    extensions={'.md','.py','.json','.jsonl','.csv','.txt','.yml','.yaml','.sql','.toml','.svg','.png','.jpg','.pdf','.example'}
    names=[p.name for p in ROOT.iterdir() if p.is_file()]
    for directory in sorted(allow_dirs):
        base=ROOT/directory
        if base.is_dir():
            names.extend(p.relative_to(ROOT).as_posix() for p in base.rglob('*') if p.is_file())
    entries=[]
    for name in sorted(set(names)):
        p=Path(name)
        if not (p.parts[0] in allow_dirs or name in allow_root):continue
        if p.parts[0]=='starter' and len(p.parts)==2 and p.name not in {'README.md','requirements-api.txt'}:continue
        if p.name=='check_setup.py':continue
        if p.parts[0]=='docs' and p.name not in {'DEMO.md','EXPLANATION.md','README.md'}:continue
        if p.parts[0]=='report' and p.name not in {'2A202603569_DinhThiHuong.md','finalization.json'}:continue
        if any(part in {'.git','.venv','.cache','.chroma','__pycache__','tmp','submission'} for part in p.parts):continue
        if any(part.startswith('.env') and part!='.env.example' for part in p.parts):continue
        if p.suffix.lower() not in extensions and name!='.gitignore':continue
        source=ROOT/p
        if not source.is_file():continue
        assert source.resolve().is_relative_to(ROOT.resolve()),'File outside project'
        payload=source.read_bytes()
        if p.suffix.lower() not in {'.pdf','.png','.jpg'}:
            assert not re.search(rb'\bsk-[A-Za-z0-9_-]{16,}',payload),'Secret pattern detected; no archive created'
        entries.append((p.as_posix(),payload))
    from dotenv import dotenv_values
    key=dotenv_values(ROOT/'.env').get('OPENAI_API_KEY')
    if key:
        assert all(key.encode() not in data for _,data in entries),'Credential bytes detected'
    manifest={'student':'Đinh Thị Hường','student_id':'2A202603569','class':'L3A','created_at':now(),
              'version_basis':'Per-file SHA-256; Git operations omitted at student request',
              'finalized_report_sha256':final['sha256'],
              'assessment':'Completed qualitative assessment with disclosed AI assistance; no independent human review claimed.',
              'files':[{'path':name,'bytes':len(data),'sha256':sha256(data).hexdigest()} for name,data in entries]}
    out=ROOT/'submission';out.mkdir(exist_ok=True)
    stem='2A202603569_DinhThiHuong_DataIngestion'
    archive=out/f'{stem}.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,data in entries:z.writestr(f'{stem}/{name}',data)
        z.writestr(f'{stem}/SUBMISSION_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None,'Archive integrity failure'
        stored=json.loads(z.read(f'{stem}/SUBMISSION_MANIFEST.json'))
        for row in stored['files']:
            assert sha256(z.read(f"{stem}/{row['path']}")).hexdigest()==row['sha256']
    checksum=sha256(archive.read_bytes()).hexdigest()
    (out/f'{stem}.sha256').write_text(f'{checksum}  {archive.name}\n',encoding='utf-8')
    (out/'submission_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Packaged {len(entries)} files, {archive.stat().st_size:,} bytes. Hash verification passed; credentials/caches excluded.')
    print(archive)


if __name__=='__main__':main()
