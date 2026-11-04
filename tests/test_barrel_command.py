from dataclasses import replace,asdict
import json,pytest
import logic as L
from logic import Position,initial_state,story_action,story_progress,state_from_backup
from voyage import progress,save
from db import connect_db,restore_game,apply_action,load_game

def hidden(barrel='barrel_chart_a'):
 _,z,x=next(p for p in L.BARRELS if p[0]==barrel)
 return replace(initial_state(),has_key=True,door_open=True,position=Position(z,x),hidden_barrel=barrel)

def ambush_officer(monkeypatch):
 import voyage
 s=hidden();x,y=L.position_xy(s.position)
 monkeypatch.setattr(voyage.L,'guard_pose_at',lambda *a:L.GuardPose(x+20,y,'walk',0,-1))
 r=voyage.ambush(s,'officer',1000,0);assert r.accepted,r.message
 return r.state

def test_ambush_hides_body_keeps_player_hidden_and_is_once(monkeypatch,tmp_path):
 import voyage
 s=ambush_officer(monkeypatch);v=progress(s)
 assert not s.officer_alive and v['concealed']['officer']==s.hidden_barrel
 assert not v['armed'] and s.hidden_barrel=='barrel_chart_a'
 assert state_from_backup(asdict(s))==s
 assert not voyage.ambush(s,'officer',1100,0).accepted
 with connect_db(tmp_path/'ambush.sqlite3') as c:
  assert restore_game(c,s,'one');before=c.total_changes
  assert not apply_action(c,'ambush',s.position,0,'one',item='cargo',now_ms=1200).accepted
  assert c.total_changes==before and load_game(c,'one')==s

def test_ambush_rejects_far_targets_crates_and_unhidden_player(monkeypatch):
 import voyage
 s=hidden();x,y=L.position_xy(s.position)
 monkeypatch.setattr(voyage.L,'guard_pose_at',lambda *a:L.GuardPose(x+100,y,'walk',0,1))
 assert not voyage.ambush(s,'officer',1000,0).accepted
 assert not voyage.ambush(replace(s,hidden_barrel=''),'officer',1000,0).accepted
 crate=L.CRATES[0];s=replace(s,hidden_barrel=crate[0],position=Position(crate[1],crate[2]))
 assert not voyage.ambush(s,'officer',1000,0).accepted

def test_captain_uniform_and_command_require_concealed_officer(monkeypatch):
 from voyage import captain_ready
 s=ambush_officer(monkeypatch)
 s=replace(s,hidden_barrel='',position=Position('captain',2460))
 opened=story_action(s,'inspect','seal_chest',2000);assert opened.accepted
 worn=story_action(opened.state,'take','seal_chest',2100);assert worn.accepted
 s=worn.state;assert 'captain_uniform' in story_progress(s)['items'] and captain_ready(s)
 assert s.disguised and state_from_backup(asdict(s))==s
 s=replace(s,position=Position('aft_deck',1980))
 won=story_action(s,'inspect','helm',2200);assert won.accepted and won.state.ending=='command'
 assert L.opponents_remaining(won.state)>0 and state_from_backup(asdict(won.state))==won.state
 forged=replace(s,officer_alive=True)
 assert state_from_backup(asdict(forged)) is None
 v=progress(s);v['armed']=True
 assert not story_action(save(s,v),'inspect','helm',2300).accepted

def test_new_patrols_pass_cover_and_shorter_waits():
 assert min(s.x1 for s in L.GUARD_ROUTES['medic'])<=1280
 assert min(s.x1 for s in L.GUARD_ROUTES['officer'])==1980
 assert next(s for s in L.GUARD_ROUTES['dining'] if s.name=='eating').duration==28
 assert next(s for s in L.GUARD_ROUTES['officer'] if s.name.endswith('end_pause')).duration==7


def test_blue_key_is_looted_and_concealed_body_survives_reload(monkeypatch,tmp_path):
 import voyage
 s=hidden('barrel_chest_a');x,y=L.position_xy(s.position)
 monkeypatch.setattr(voyage.L,'guard_pose_at',lambda *a:L.GuardPose(x,y,'watch',0,-1))
 r=voyage.ambush(s,'sleeper',1000,0)
 assert r.accepted and r.state.has_blue_key and r.state.held_item=='blue_key' and not r.state.sleeper_alive
 assert state_from_backup(asdict(r.state))==r.state
 with connect_db(tmp_path/'loot.sqlite3') as c:
  assert restore_game(c,r.state,'a');assert load_game(c,'a')==r.state


def test_concealment_and_uniform_forgery_are_rejected(monkeypatch):
 s=ambush_officer(monkeypatch)
 v=progress(s);v['concealed']['cargo']=v['concealed']['officer']
 assert state_from_backup(asdict(save(s,v))) is None
 assert state_from_backup(asdict(replace(s,officer_corpse_x=2400))) is None
 v=progress(s);v['captain_worn']=True
 assert state_from_backup(asdict(save(s,v))) is None


def test_regular_wardrobe_removes_captain_uniform(monkeypatch):
 from voyage import wear_captain,captain_ready
 s=ambush_officer(monkeypatch);s=replace(s,hidden_barrel='',position=Position('cabin',460),wardrobe_open=True)
 s=wear_captain(s).state;assert captain_ready(s)
 removed=L.change_outfit(s);assert removed.accepted and not progress(removed.state)['captain_worn']
 assert not captain_ready(removed.state) and state_from_backup(asdict(removed.state))


def test_command_ending_migrates_old_database_constraint(monkeypatch,tmp_path):
 import sqlite3
 from db import _CREATE
 from voyage import wear_captain
 path=tmp_path/'legacy.sqlite3'
 with sqlite3.connect(path) as c:c.execute(_CREATE.replace(",'command'",''))
 s=wear_captain(replace(ambush_officer(monkeypatch),hidden_barrel='')).state
 s=replace(s,position=Position('aft_deck',1980))
 with connect_db(path) as c:
  assert restore_game(c,s,'a')
  won=apply_action(c,'story_inspect',s.position,0,'a',item='helm',now_ms=2000)
  assert won.accepted and won.state.ending=='command'
  before=c.total_changes
  assert not apply_action(c,'ambush',s.position,0,'a',item='cargo',now_ms=2100).accepted
  assert c.total_changes==before
 with connect_db(path) as c:assert load_game(c,'a').ending=='command'


def test_canvas_ambush_target_capture_clothes_and_cutscene_paths():
 from test_canvas_rules import canvas
 s=hidden();d={**asdict(s),'story':story_progress(s),'rules':L.MAP_CONFIG,'guard_routes':{k:[asdict(p) for p in r] for k,r in L.GUARD_ROUTES.items()}}
 result=canvas(r'''(()=>{
 guardPose=()=>({x:2050,y:245,name:'walk'});watchCrew=()=>({x:300,y:365});
 const target=ambushTarget({data:input,position:input.position});let drawn;
 person=(...args)=>{drawn={kind:args[9],style:args[10]}};
 drawCaptor({}, {data:input,capture:{kind:'dining',guard:{x:2050,y:245}}},{x:2060,y:245},0);
 const boat=[6,8,10,11,12,15,20].map(t=>dinghyMotion(1000,500,t));
 const cook=[5,7,9,10].map(t=>crateDeliveryMotion(1000,500,t));
 return {target:target[0],drawn,boat,cook};
 })()''',d)
 assert result['target'] in L.GUARD_ROUTES
 assert result['drawn']['kind']=='dining' and result['drawn']['style']==L.GUARD_STYLES['dining']
 for i,m in enumerate(result['boat']):
  if m['away']==0:assert m['y']-85*m['scale']>=m['water']
  else:assert m['x']-60*m['scale']>m['bow']
 cook=result['cook']
 assert cook[-1]['aboard'] and cook[-1]['cook']==cook[-1]['top']
 assert cook[1]['cook']['x']>cook[2]['cook']['x'] and cook[1]['cook']['y']>cook[2]['cook']['y']


def test_command_route_from_new_game_through_real_movement():
 from test_playthrough import start_free,walk,accepted,take_story
 from voyage import ambush
 s=start_free();s=walk(s,Position('chart_room',2050))
 s=accepted(L.toggle_barrel(s));s=accepted(ambush(s,'officer',1000000,7))
 assert progress(s)['concealed']=={'officer':'barrel_chart_a'}
 s=accepted(L.toggle_barrel(s));s=take_story(s,'seal_chest')
 assert progress(s)['captain_worn']
 s=walk(s,Position('aft_deck',1980));s=accepted(story_action(s,'inspect','helm',1001000))
 assert s.ending=='command' and L.opponents_remaining(s)==9
 assert state_from_backup(asdict(s))==s


def test_watch_pauses_shorten_by_thirty_percent_without_extending_shift():
 route=L.CARGO_WATCH_ROUTE
 assert sum(p.duration for p in route)==pytest.approx(45)
 assert next(p.duration for p in route if p.name=='cargo_left_pause')==pytest.approx(3.8969072165)
 assert next(p.duration for p in route if p.name=='cargo_right_pause')==pytest.approx(4.8711340206)
 for p in route:
  if p.x1!=p.x2:assert abs(p.x2-p.x1)/p.duration==pytest.approx(34.4888888889)


def test_captain_must_wait_until_current_search_ends(monkeypatch):
 from voyage import wear_captain
 s=wear_captain(replace(ambush_officer(monkeypatch),hidden_barrel='')).state
 s=replace(s,position=Position('aft_deck',1980),alert_started_ms=1000,alert_until_ms=21000)
 denied=story_action(s,'inspect','helm',3000)
 assert not denied.accepted and denied.state==s
 assert story_action(s,'inspect','helm',22000).state.ending=='command'
