"""Extract the actual submission ZIP and open the UI without key/index/cache."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import json
import subprocess
import uuid
import zipfile
from hashlib import sha256
from starter.src.project import ROOT,RESULTS,write_json,now


def main():
    archive=ROOT/'submission/2A202603569_DinhThiHuong_DataIngestion.zip'
    target=ROOT/'tmp'/('package_smoke_'+uuid.uuid4().hex)
    assert target.resolve().is_relative_to((ROOT/'tmp').resolve())
    target.mkdir(parents=True)
    with zipfile.ZipFile(archive) as z:
        manifest_name=next(name for name in z.namelist() if name.endswith('/SUBMISSION_MANIFEST.json'))
        manifest=json.loads(z.read(manifest_name))
        prefix=manifest_name.rsplit('/',1)[0]+'/'
        for name in z.namelist():
            assert (target/name).resolve().is_relative_to(target.resolve())
            assert not any(part in {'.env','.git','.chroma','.cache','.venv'} for part in Path(name).parts)
        for row in manifest['files']:
            assert sha256(z.read(prefix+row['path'])).hexdigest()==row['sha256']
        z.extractall(target)
    project=target/prefix.rstrip('/')
    code='''import os,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
os.environ.pop('OPENAI_API_KEY',None)
assert not Path('.env').exists()
assert not Path('.chroma').exists()
from streamlit.testing.v1 import AppTest
app=AppTest.from_file('app.py').run(timeout=30)
assert not app.exception
assert app.get('chat_input')[0].proto.disabled
assert len(app.tabs)==3
app.radio[0].set_value('test').run()
assert not app.exception
assert any('8/10' in str(frame.value) for frame in app.dataframe)
print('PACKAGED_UI_WITHOUT_KEY_OR_INDEX_PASS')
'''
    result=subprocess.run([sys.executable,'-X','utf8','-c',code],cwd=project,capture_output=True,text=True,encoding='utf-8',timeout=90)
    assert result.returncode==0, result.stderr[-4000:]
    assert 'PACKAGED_UI_WITHOUT_KEY_OR_INDEX_PASS' in result.stdout
    check=subprocess.run([sys.executable,'-X','utf8','starter/scripts/verify_submission.py'],cwd=project,capture_output=True,text=True,encoding='utf-8',timeout=90)
    assert check.returncode==0,check.stderr[-2000:]
    write_json(RESULTS/'package_smoke.json',{'at':now(),'archive_sha256':sha256(archive.read_bytes()).hexdigest(),
        'manifest_hashes':'pass','extracted_source_ui':'pass','no_env_or_vector_cache':True,
        'chat_disabled_without_index':True,'saved_results_viewable':True,'offline_source_metric_checks':'pass',
        'limitation':'Extracted package tested using the existing Python environment, not a fresh dependency installation or another physical machine. Archive is rebuilt afterward to include this verification record.'})
    print('Extracted ZIP: hashes verified; UI opens without key/index, chat disabled, saved metrics viewable; offline source checks pass.')


if __name__=='__main__':main()
