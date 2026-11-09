from dataclasses import replace
from logic import initial_state,Position
from db import connect_db,restore_game,apply_action,load_game

def test_capture_heartbeat_returns_legacy_capture_to_cell(tmp_path):
 s=replace(initial_state(),has_key=True,door_open=True,position=Position('cabin',160),capture_phase='active',capture_guard_zone='cabin',capture_guard_value=180)
 with connect_db(tmp_path/'capture.sqlite3') as c:
  assert restore_game(c,s,'one')
  assert apply_action(c,'capture_tick',s.position,0,'one',now_ms=1000).accepted
  assert apply_action(c,'capture_tick',s.position,0,'one',now_ms=31000).accepted
  assert load_game(c,'one').position.zone=='cell'
  assert load_game(c,'one').capture_phase=='none'

def test_legacy_chest_panel_closes_without_losing_progress(tmp_path,monkeypatch):
 import app,json
 s=replace(initial_state(),has_key=True,door_open=True,position=Position('hold',510),story_state=json.dumps({'inspected':['tools_chest'],'items':['crowbar']}),reading='tools_chest',paused_at_ms=1000)
 path=tmp_path/'legacy.sqlite3';monkeypatch.setattr(app,'DB_PATH',path)
 with connect_db(path) as c:assert restore_game(c,s,'one')
 resumed=app.read_progress('one')
 assert not resumed.reading and resumed.has_key
 assert 'crowbar' in resumed.story_state
 assert app.ITEMS['crowbar']['name']=='Crowbar'

def test_wardrobe_reachable_from_stair_landing():
 from logic import toggle_wardrobe,change_outfit
 s=replace(initial_state(),has_key=True,door_open=True,position=Position('mid',540))
 opened=toggle_wardrobe(s);assert opened.accepted and opened.state.wardrobe_open
 assert change_outfit(opened.state).accepted
 assert not toggle_wardrobe(replace(s,position=Position('hold',540))).accepted

def test_backend_imports_refresh_same_second_source_changes(tmp_path):
 import subprocess,sys
 from pathlib import Path
 script='''import sys
from pathlib import Path
from runtime_loader import load_backend
r=Path(sys.argv[1]);sys.path.insert(0,str(r))
load_backend(r)
import db
assert db.VALUE=='old'
(r/'content.py').write_text("VALUE='new'\\n")
load_backend(r)
assert db.VALUE=='new'
'''
 for name,text in [('content',"VALUE='old'\n"),('logic','from content import VALUE\n'),('escort','from logic import VALUE\n'),('voyage','from logic import VALUE\n'),('feast','from logic import VALUE\n'),('shiplife','from voyage import VALUE\n'),('db','from voyage import VALUE\n'),('action_transport','from db import VALUE\n')]:
  (tmp_path/(name+'.py')).write_text(text)
 result=subprocess.run([sys.executable,'-c',script,str(tmp_path)],capture_output=True,text=True)
 assert result.returncode==0,result.stderr
