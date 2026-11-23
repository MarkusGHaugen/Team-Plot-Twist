import json
from dataclasses import replace,asdict
from logic import initial_state,Position,state_from_backup,story_progress
from voyage import boat_ready
from db import connect_db,restore_game,apply_action,load_game

def free(**kw):return replace(initial_state(),has_key=True,door_open=True,**kw)

def test_dinghy_no_longer_needs_crowbar():
 s=free(position=Position('aft_deck',1660),story_state=json.dumps({'items':['sail','rope']}))
 assert boat_ready(s)
 assert not boat_ready(replace(s,story_state=json.dumps({'items':['sail']})))

def test_restart_requires_confirmation_and_only_resets_own_save(tmp_path):
 s=free(position=Position('hold',760))
 with connect_db(tmp_path/'restart.sqlite3') as c:
  restore_game(c,s,'a');restore_game(c,s,'b')
  assert not apply_action(c,'restart_game',s.position,0,'a',now_ms=1000).accepted
  assert apply_action(c,'restart_prompt',s.position,0,'a',now_ms=1100).accepted
  assert load_game(c,'a').reading=='restart_confirm'
  assert apply_action(c,'close_reading',s.position,0,'a',now_ms=1500).accepted
  assert load_game(c,'a').has_key
  assert apply_action(c,'restart_prompt',s.position,0,'a',now_ms=1600).accepted
  assert apply_action(c,'restart_game',s.position,0,'a',item='confirmed',now_ms=1700).accepted
  assert load_game(c,'a')==initial_state() and load_game(c,'b')==s


def test_guide_waits_in_cover_then_moves_and_returns(monkeypatch):
 from escort import plan,tick,guard_override,SPEED
 from voyage import progress,save
 import escort
 from logic import guard_pose_at
 s=free(position=Position('dining',1100))
 v=progress(s);v.update(coins=0,claimed=['coins_hold','coins_chart'],paid=['cook'])
 v['escort']=plan(s,Position('kitchen',1260),Position('dining',1100),'cook',2000)
 s=save(s,v)
 monkeypatch.setattr(escort,'visible',lambda *args:True)
 waiting=tick(s,progress(s),2250,.25).state
 assert waiting.position==s.position and progress(waiting)['escort']['hidden']
 assert guard_override(waiting,'dining',2250).segment=='guiding_wait'
 assert state_from_backup(asdict(waiting))==waiting
 monkeypatch.setattr(escort,'visible',lambda *args:False)
 moving=tick(waiting,progress(waiting),2500,.5).state
 assert not progress(moving)['escort']['paused']
 from test_canvas_rules import canvas
 e=progress(moving)['escort']
 from escort import pose
 expected=pose(e,2625)
 actual=canvas('guidePosition(input.e,input.now)',{'e':e,'now':2625})
 import pytest
 assert (actual['x'],actual['y'])==pytest.approx(expected)
 s=moving
 for now in range(2750,20000,250):
  s=tick(s,progress(s),now,(now-2000)/1000).state
  if 'escort' not in progress(s):break
 assert s.position==Position('kitchen',1260) and story_progress(s)['crate_open']
 g=progress(s)['guide'];assert guard_override(s,'dining',now).segment=='guide_farewell'
 assert guard_override(s,'dining',g['started']+1000).segment=='returning_to_post'
 assert guard_override(s,'dining',g['started']+20000).segment not in ('returning_to_post','guide_farewell')
 assert state_from_backup(asdict(s))==s


def test_guide_checks_observers_and_cannot_capture_his_passenger(monkeypatch):
 import escort
 from logic import GuardPose,can_guard_see
 from voyage import progress,save
 s=free(position=Position('aft_deck',1450))
 monkeypatch.setattr(escort.L,'guard_pose_at',lambda *args:GuardPose(1350,245,'watch',0,1))
 assert escort.visible(s,(1450,245),2000,0,'boatswain')
 assert not escort.visible(s,(1200,245),2000,0,'boatswain')
 monkeypatch.undo()
 v=progress(s);v.update(coins=0,claimed=['coins_hold','coins_chart','coins_crew'],paid=['boatswain'])
 v['escort']=escort.plan(s,Position('aft_deck',1660),s.position,'boatswain',2000)
 v['escort'].update(hidden=False,paused=False,target=210)
 s=save(s,v)
 assert not can_guard_see(s,0,'boatswain',2000)


def test_completed_game_restart_prompt_leaves_victory_immutable(tmp_path):
 s=free(position=Position('aft_deck',1660),story_state=json.dumps({'items':['sail','rope']}),ending='dinghy')
 with connect_db(tmp_path/'complete.sqlite3') as c:
  restore_game(c,s,'a');before=c.total_changes
  assert not apply_action(c,'restart_prompt',s.position,0,'a',now_ms=1000).accepted
  assert load_game(c,'a')==s and c.total_changes==before
  assert not apply_action(c,'restart_game',s.position,0,'a',item='confirmed',now_ms=1500).accepted
  assert load_game(c,'a')==s


def test_guide_save_rejects_incomplete_or_impossible_motion():
 from voyage import progress,save
 from escort import plan
 s=free(position=Position('dining',1100));v=progress(s)
 v.update(coins=0,claimed=['coins_hold','coins_chart'],paid=['cook'])
 v['escort']=plan(s,Position('kitchen',1260),s.position,'cook',2000)
 assert state_from_backup(asdict(save(s,v)))
 import copy
 for patch in ({'target':99999},{'distance':-1},{'covers':[0,10000]},{'hidden':False}):
  bad=copy.deepcopy(v);bad['escort'].update(patch)
  assert state_from_backup(asdict(save(s,bad))) is None
 bad=copy.deepcopy(v);del bad['escort']['distance']
 assert state_from_backup(asdict(save(s,bad))) is None
 # Older three-field escort saves remain readable.
 old=copy.deepcopy(v);old['escort']={k:v['escort'][k] for k in ('kind','started','path')}
 assert state_from_backup(asdict(save(s,old)))


def test_music_uses_one_player_pair_and_cleans_up_its_scheduler():
 from test_canvas_rules import require_node
 expression=r'''(async()=>{
  let contexts=0,cleared=0,clock=1000,callback;
  globalThis.Date={now:()=>clock};globalThis.document={hidden:false};globalThis.URL=class {constructor(path){this.href=path;}};
  globalThis.setInterval=fn=>{callback=fn;return 1;};globalThis.clearInterval=()=>cleared++;
  const param=()=>({value:0,setTargetAtTime:()=>{},setValueAtTime:()=>{},linearRampToValueAtTime:()=>{},exponentialRampToValueAtTime:()=>{}});
  globalThis.Audio=class {constructor(){contexts++;this.currentTime=0;}addEventListener(){}pause(){}play(){return Promise.resolve();}};
  const m=musicEngine();m.note=()=>{};
  const before=m.enabled;await m.toggle();const same=musicEngine()===m;
  m.touch({capture_phase:'none',alert_until_ms:0,guard_routes:{},story:{}});const explore=m.mode;
  m.touch({capture_phase:'none',alert_until_ms:2000,guard_routes:{},story:{}});const alert=m.mode;
  await m.toggle();const off=!m.enabled&&m.timer===null;
  await m.toggle();clock=4001;callback();
  return {before,same,contexts,explore,alert,off,abandoned:!m.enabled&&m.timer===null,cleared};
 })()'''
 import subprocess,shutil
 from pathlib import Path
 source=Path('game_component/game.js').read_text().replace('export default function','function mount')
 runner="const vm=require('vm'),v=JSON.parse(require('fs').readFileSync(0,'utf8')),c={};vm.createContext(c);vm.runInContext(v.source,c);Promise.resolve(vm.runInContext(v.expression,c)).then(r=>console.log(JSON.stringify(r))).catch(e=>{console.error(e);process.exitCode=1});"
 result=json.loads(subprocess.run([require_node(),'-e',runner],input=json.dumps({'source':source,'expression':expression}),text=True,capture_output=True,check=True).stdout)
 assert result=={'before':False,'same':True,'contexts':2,'explore':'explore','alert':'alert','off':True,'abandoned':True,'cleared':2}


def test_canvas_guide_and_returning_guard_match_authoritative_pose():
 from escort import plan,guard_override
 from voyage import progress,save
 from logic import MAP_CONFIG,GUARD_ROUTES
 from test_canvas_rules import canvas
 import pytest
 s=free(position=Position('dining',1100));v=progress(s)
 v.update(coins=0,claimed=['coins_hold','coins_chart'],paid=['cook'])
 e=plan(s,Position('kitchen',1260),s.position,'cook',2000)
 e.update(paused=False,hidden=False,target=e['covers'][-1]);v['escort']=e
 s=save(s,v)
 for now in (2000,2100,2600,3100):
  data={**asdict(s),'story':story_progress(s),'rules':MAP_CONFIG,'paused_at_ms':now}
  js=canvas('guidePose(input,"dining")',data);p=guard_override(s,'dining',now)
  assert (js['x'],js['y'],js['facing'])==pytest.approx((p.x,p.y,p.facing))
 v.pop('escort');v['guide']={'kind':'cook','path':e['return_path'],'started':10000,'speech_until':10000,'resume_elapsed':0.}
 s=save(s,v)
 for now in (9000,10500,20000):
  data={**asdict(s),'story':story_progress(s),'rules':MAP_CONFIG,'paused_at_ms':now,'guard_routes':{k:[asdict(x) for x in route] for k,route in GUARD_ROUTES.items()}}
  js=canvas('guidePose(input,"dining")',data);p=guard_override(s,'dining',now)
  assert (js['x'],js['y'],js['facing'])==pytest.approx((p.x,p.y,p.facing))


def test_restart_confirmation_keeps_the_last_unreported_position(tmp_path):
 s=free(position=Position('hold',700))
 with connect_db(tmp_path/'moving.sqlite3') as c:
  restore_game(c,s,'a');nearby=Position('hold',735)
  r=apply_action(c,'restart_prompt',nearby,0,'a',now_ms=1100)
  assert r.accepted and r.state.position==nearby
  assert apply_action(c,'close_reading',nearby,0,'a',now_ms=1200).accepted
  assert load_game(c,'a').position==nearby


def test_guide_checks_that_the_helper_is_not_seen_either(monkeypatch):
 import escort
 s=free(position=Position('dining',1100))
 e={'kind':'cook','path':[[1100,365],[1120,365]]}
 # The prisoner is behind cover; the helper would already be visible at departure.
 monkeypatch.setattr(escort,'visible',lambda state,xy,now,*args:now==2000 and xy[0]>1100)
 assert not escort.clear_leg(s,e,0,20,2000,0)
