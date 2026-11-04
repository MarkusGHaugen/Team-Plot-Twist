"""Team branding, version and browser-save separation."""
import json,subprocess,shutil,tomllib
from pathlib import Path

def test_team_metadata_and_lock_agree():
 project=tomllib.loads(Path('pyproject.toml').read_text())['project']
 assert project['name']=='team-plot-twist' and project['version']=='1.0.0'
 lock=tomllib.loads(Path('uv.lock').read_text())
 own=next(p for p in lock['package'] if p['name']==project['name'])
 assert own['version']==project['version']
 assert 'Team Plot Twist' in Path('app.py').read_text()

def test_team_identity_does_not_read_or_overwrite_predecessor_save():
 identity=Path('game_component/browser_identity.js').read_text().replace('export default function','function mount')
 backup=Path('game_component/browser_backup.js').read_text().replace('export default function','function backup')
 script=r'''const vm=require('vm'),fs=require('fs'),input=JSON.parse(fs.readFileSync(0,'utf8'));
 const solo={id:'a'.repeat(32),backup:{secret:'private-progress'}};
 const values=new Map([['plot-twist-browser-save-v1',JSON.stringify(solo)]]);
 const c={crypto:{randomUUID:()=> 'b'.repeat(32)},localStorage:{getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,v)}};
 vm.createContext(c);vm.runInContext(input.identity,c);let result;c.setStateValue=(k,v)=>result=v;
 vm.runInContext('mount({data:{request_identity:true},setStateValue})',c);
 vm.runInContext(input.backup.replace('const SAVE_KEY','const BACKUP_KEY').replaceAll('setItem(SAVE_KEY','setItem(BACKUP_KEY'),c);
 vm.runInContext('backup({data:{player_id:"b".repeat(32),state:{team:true}}})',c);
 console.log(JSON.stringify({result,solo:JSON.parse(values.get('plot-twist-browser-save-v1')),team:JSON.parse(values.get('team-plot-twist-browser-save-v1'))}));'''
 r=subprocess.run([shutil.which('node'),'-e',script],input=json.dumps({'identity':identity,'backup':backup}),capture_output=True,text=True,check=True)
 v=json.loads(r.stdout)
 assert v['result']['id']=='b'*32 and v['result']['backup'] is None
 assert v['solo']=={'id':'a'*32,'backup':{'secret':'private-progress'}}
 assert v['team']=={'id':'b'*32,'backup':{'team':True}}


def test_source_packaging_ignores_parent_history_and_private_files(tmp_path):
 import importlib.util,zipfile
 spec=importlib.util.spec_from_file_location('team_packager','scripts/package_release.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 outer=tmp_path/'outer';outer.mkdir();subprocess.run(['git','init',str(outer)],check=True,capture_output=True)
 (outer/'private-note.txt').write_text('do not export')
 root=outer/'team';root.mkdir();(root/'app.py').write_text('team code')
 (root/'.env').write_text('not for export');(root/'data').mkdir();(root/'data/progress.sqlite3').write_text('private save')
 (root/'release-files.json').write_text(json.dumps(['app.py','.env','data/progress.sqlite3','release-files.json']))
 output=module.package(root,tmp_path/'source.zip')
 with zipfile.ZipFile(output) as z:assert set(z.namelist())=={'Team-Plot-Twist/app.py','Team-Plot-Twist/release-files.json'}
