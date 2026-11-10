from dataclasses import replace,asdict
from logic import initial_state,Position,story_action,story_progress,state_from_backup
from voyage import voyage_action,watch_pose,crew_tick

def free(zone='hold',x=700): return replace(initial_state(),has_key=True,door_open=True,position=Position(zone,x))

def test_coins_are_finite_and_bribes_are_once():
 s=free()
 for name in ('coins_hold','coins_provisions','coins_chart','coins_crew'):
  from content import STORY_POINTS
  p=STORY_POINTS[name];s=replace(s,position=Position(p['zone'],p['x']),reached_kitchen=True)
  a=voyage_action(s,'inspect',name,1000);assert a.accepted;s=a.state
  assert not voyage_action(s,'inspect',name,1000).accepted
 assert story_progress(s)['voyage']['coins']==4

def test_watch_alternates_and_key_does_not_transfer():
 import json
 s=replace(free(),story_state=json.dumps({'voyage':{'watch_start':0}}))
 assert watch_pose(s,'sleeper',0)[1]
 assert not watch_pose(s,'cargo',0)[1]
 assert not watch_pose(s,'sleeper',52_000)[1]
 assert watch_pose(s,'cargo',52_000)[1]
 assert watch_pose(s,'sleeper',104_000)[1]

def test_crate_needs_no_manifest_or_seal():
 s=free('mid',735)
 import json
 s=replace(s,story_state=json.dumps({'items':['crowbar']}))
 opened=story_action(s,'inspect','return_crate',1000);assert opened.accepted and not opened.state.reading
 ready=story_action(opened.state,'inspect','return_crate',1100);assert ready.state.reading=='confirm_crate'
 won=story_action(ready.state,'finish','return_crate',1200);assert won.state.ending=='crate'
 assert state_from_backup(asdict(won.state))

def test_dinghy_requires_sail_and_tools():
 import json
 s=free('aft_deck',1660)
 assert not voyage_action(s,'inspect','lifeboat',1000).accepted
 s=replace(s,story_state=json.dumps({'items':['sail','rope','crowbar']}))
 ready=voyage_action(s,'inspect','lifeboat',1100);assert ready.state.reading=='confirm_dinghy'
 won=voyage_action(ready.state,'finish','lifeboat',1200);assert won.state.ending=='dinghy'
 assert state_from_backup(asdict(won.state))

def wallet(s,count):
 from content import STORY_POINTS
 for name in list(k for k in STORY_POINTS if k.startswith('coins_'))[:count]:
  p=STORY_POINTS[name];s=replace(s,position=Position(p['zone'],p['x']))
  s=voyage_action(s,'inspect',name,1000).state
 return s

def test_cook_payment_escort_and_restore():
 from logic import guard_pose_at,_floor_zone
 s=wallet(free(),2);pose=guard_pose_at(s,'dining',0,2000)
 s=replace(s,position=Position(_floor_zone(pose.y,pose.x),pose.x))
 paid=voyage_action(s,'bribe','cook',2000);assert paid.accepted
 assert story_progress(paid.state)['voyage']['coins']==0
 assert not voyage_action(paid.state,'bribe','cook',2100).accepted
 arrived=finish_guide(paid.state)
 assert arrived.position==Position('mid',735)
 assert story_progress(arrived)['crate_open']
 assert state_from_backup(asdict(arrived))==arrived

def test_boatswain_payment_replaces_tools_but_not_sail():
 import json
 from logic import guard_pose_at,_floor_zone
 s=wallet(free(),3);pose=guard_pose_at(s,'boatswain',0,2000)
 s=replace(s,position=Position(_floor_zone(pose.y,pose.x),pose.x))
 assert not voyage_action(s,'bribe','boatswain',2000).accepted
 p=story_progress(s);p['items']=['sail'];s=replace(s,story_state=json.dumps(p))
 paid=voyage_action(s,'bribe','boatswain',2000);assert paid.accepted
 arrived=finish_guide(paid.state)
 assert arrived.position==Position('aft_deck',1660)
 ready=voyage_action(arrived,'inspect','lifeboat',61000)
 won=voyage_action(ready.state,'finish','lifeboat',62000)
 assert won.state.ending=='dinghy' and state_from_backup(asdict(won.state))

def test_guard_projectiles_can_be_ducked_or_blocked_by_cover():
 import json
 def scene(duck=False,hidden=''):
  return replace(free(),story_state=json.dumps({'voyage':{'armed':True,'duck':duck,'last_tick':1000,'shots':[{'x':680,'y':436,'dir':1,'born':1000}]}}),hidden_barrel=hidden)
 hit=crew_tick(scene(),1200).state
 assert story_progress(hit)['voyage']['hp']==1
 assert story_progress(crew_tick(scene(True),1200).state)['voyage']['hp']==2
 assert story_progress(crew_tick(scene(hidden='cover'),1200).state)['voyage']['hp']==2
 # A second hit causes the existing capture flow.
 p=story_progress(hit);p['voyage']['shots']=[{'x':680,'y':436,'dir':1,'born':1400}]
 p['voyage']['last_tick']=1400
 s=replace(hit,story_state=json.dumps(p))
 assert crew_tick(s,1600).state.capture_phase=='active'

def test_malformed_economy_and_free_boat_victory_are_rejected():
 import json
 for v in ({'coins':99},{'claimed':[['bad']]},{'paid':['cook'],'coins':0},{'shots':[{}]}):
  assert state_from_backup({**asdict(free()),'story_state':json.dumps({'voyage':v})}) is None
 assert state_from_backup({**asdict(free()),'ending':'dinghy'}) is None

def test_dinghy_has_complete_walkable_path_from_cell():
 from test_playthrough import start_free,take_story,walk,accepted
 s=start_free()
 for point in ('tools_chest','rope_chest','sail_chest'):s=take_story(s,point)
 s=walk(s,Position('aft_deck',1660))
 confirmed=accepted(story_action(s,'inspect','lifeboat',10000))
 won=accepted(story_action(confirmed,'finish','lifeboat',11000))
 assert won.ending=='dinghy' and state_from_backup(asdict(won))

def test_dinghy_can_be_saved_after_old_ending_constraint_migrates(tmp_path):
 import sqlite3,json
 from db import _CREATE,connect_db,restore_game,load_game,new_game,apply_action
 path=tmp_path/'old.sqlite3'
 with sqlite3.connect(path) as c:c.execute(_CREATE.replace(",'dinghy'",''))
 with connect_db(path) as c:
  new_game(c,'one')
  s=replace(free('aft_deck',1660),story_state=json.dumps({'items':['sail','rope','crowbar']}))
  assert restore_game(c,s,'other')
  assert apply_action(c,'story_inspect',s.position,0,'other',item='lifeboat',now_ms=1000).accepted
  assert apply_action(c,'story_finish',s.position,0,'other',item='lifeboat',now_ms=1100).accepted
 with connect_db(path) as c:
  assert load_game(c,'other').ending=='dinghy'
  before=c.total_changes
  assert not apply_action(c,'voyage_tick',s.position,0,'other',now_ms=2000).accepted
  assert c.total_changes==before

def test_watch_animation_matches_python_and_pauses():
 import json
 from logic import MAP_CONFIG,route_points
 from test_canvas_rules import canvas
 s=replace(free(),story_state=json.dumps({'voyage':{'watch_start':1000}}))
 for now in (1000,46000,48000,53000,98000,105000):
  for kind in ('sleeper','cargo'):
   p,sleeping=watch_pose(s,kind,now)
   d={**asdict(s),'story':story_progress(s),'paused_at_ms':now,'rules':{**MAP_CONFIG,'watch_path':route_points(Position('cabin',300),Position('chest_room',1320))}}
   js=canvas('watchCrew(input.data,input.kind)',{'data':d,'kind':kind})
   import pytest
   assert (js['x'],js['y'])==pytest.approx((p.x,p.y))
   assert (js['name']=='sleep')==sleeping

def test_armed_guards_see_thirty_percent_further_through_disguise():
 import json
 from logic import can_guard_see,guard_pose_for
 p=guard_pose_for('patrol',0)
 s=replace(free('cabin',p.x-210),disguised=True,wardrobe_contents='player_clothes')
 # Use the guard's actual floor at this time.
 from logic import _floor_zone
 s=replace(s,position=Position(_floor_zone(p.y,p.x-210),p.x-210))
 assert not can_guard_see(s,0,'patrol',1000)
 s=replace(s,story_state=json.dumps({'voyage':{'armed':True}}))
 assert can_guard_see(s,0,'patrol',1000)

def test_watch_key_stays_with_original_guard_after_waking():
 import json
 from logic import steal_blue_key,_floor_zone
 s=replace(free(),story_state=json.dumps({'voyage':{'watch_start':1000}}))
 p,sleeping=watch_pose(s,'sleeper',54000)
 assert not sleeping
 s=replace(s,position=Position(_floor_zone(p.y,p.x),p.x))
 assert steal_blue_key(s,0,54000).accepted
 assert not steal_blue_key(replace(s,has_blue_key=True),0,54000).accepted


def finish_guide(s):
 # Guides now wait for patrol gaps rather than teleporting after elapsed wall time.
 for now in range(2250,182000,250):
  s=crew_tick(s,now,(now-2000)/1000).state
  if 'escort' not in story_progress(s)['voyage']:return s
 raise AssertionError('The guide never found a safe route')
