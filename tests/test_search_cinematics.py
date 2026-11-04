import json,math
from dataclasses import replace,asdict
import pytest
from logic import initial_state,Position,GUARD_ROUTES,guard_pose_at,_start_alert,story_progress,state_from_backup
from voyage import watch_pose,save,progress

def scene(armed=False):
 s=replace(initial_state(),has_key=True,door_open=True,position=Position('hold',700))
 v=progress(s);v.update(armed=armed,watch_start=1000)
 return _start_alert(save(s,v),0,1000)

def test_all_guards_move_throughout_alarm_and_persist_during_combat():
 for armed in (False,True):
  s=scene(armed)
  for kind in (*GUARD_ROUTES,'sleeper'):
   for t in range(1000,20000 if not armed else 80000,500):
    a=guard_pose_at(s,kind,(t-1000)/1000,t);b=guard_pose_at(s,kind,(t-900)/1000,t+100)
    mid=guard_pose_at(s,kind,(t-950)/1000,t+50)
    # A guard can reverse during a sample; measure travelled distance, not net displacement.
    assert math.dist((a.x,a.y),(mid.x,mid.y))+math.dist((mid.x,mid.y),(b.x,b.y))>1,(kind,t,armed)
  assert state_from_backup(asdict(s))==s

def test_search_areas_extend_beyond_home_patrol():
 s=scene()
 paths=json.loads(s.alert_paths)
 assert min(p[0] for p in paths['cargo'])<=760
 for kind in ('cargo','sailor','medic','officer','lookout'):
  routine=GUARD_ROUTES[kind]
  assert min(p[0] for p in paths[kind])<min(p.x1 for p in routine) or max(p[0] for p in paths[kind])>max(p.x1 for p in routine),kind

def test_working_cargo_guard_passes_the_barrel():
 s=replace(initial_state(),story_state=json.dumps({'voyage':{'watch_start':1000}}))
 xs=[watch_pose(s,'cargo',1000+i*250)[0].x for i in range(180)]
 assert min(xs)<=760 and max(xs)>1100
 assert max(s.x1 for s in GUARD_ROUTES['cargo'])>=1300

def test_canvas_search_matches_every_guard_including_watch():
 from test_canvas_rules import canvas
 from logic import MAP_CONFIG,route_points
 s=scene(True)
 cases=[];expected=[]
 for kind in (*GUARD_ROUTES,'sleeper'):
  for now in (1000,5500,19500,21000,34500,61250):
   d={**asdict(s),'story':story_progress(s),'paused_at_ms':now,'guard_started_ms':1000,
      'parsedAlertPaths':json.loads(s.alert_paths),'parsedAlertResume':json.loads(s.alert_resume),
      'rules':{**MAP_CONFIG,'watch_path':route_points(Position('cabin',300),Position('chest_room',1320))},
      'guard_routes':{k:[asdict(p) for p in v] for k,v in GUARD_ROUTES.items()}}
   cases.append([d,kind]);p=guard_pose_at(s,kind,(now-1000)/1000,now);expected.append((p.x,p.y,p.facing))
 result=canvas('input.map(([d,k])=>k==="sleeper"?watchCrew(d,k):guardPose(d,k))',cases)
 for a,b in zip(result,expected):assert (a['x'],a['y'],a['facing'])==pytest.approx(b)


def test_rotating_watch_does_not_jump_when_swapping_posts():
 s=replace(initial_state(),story_state=json.dumps({'voyage':{'watch_start':1000}}))
 for kind in ('cargo','sleeper'):
  for elapsed in (45000,52000,97000,104000):
   a,_=watch_pose(s,kind,1000+elapsed-1);b,_=watch_pose(s,kind,1000+elapsed)
   assert math.dist((a.x,a.y),(b.x,b.y))<1,(kind,elapsed)


def test_crate_night_lasts_eight_seconds_before_delivery():
 from test_canvas_rules import canvas
 result=canvas(r'''(()=>{
  let t=0,scene='';globalThis.performance={now:()=>t};
  drawCratePrelude=()=>{scene='night'};drawCrateDelivery=()=>{scene='delivery'};
  const ctx=new Proxy({createLinearGradient:()=>({addColorStop:()=>{}})},{get:(o,k)=>k in o?o[k]:(()=>{})});
  return [0,3000,7999,8000,15000].map(now=>{t=now;drawEnding(ctx,1000,500,{data:{ending:'crate'},endingStartedAt:0});return scene;});
 })()''',{})
 assert result==['night','night','night','delivery','delivery']


def test_alarm_expires_continuously_at_different_watch_phases():
 for phase in (0,40,44,50,90,103):
  s=replace(initial_state(),has_key=True,door_open=True,position=Position('hold',700),story_state=json.dumps({'voyage':{'watch_start':1000}}))
  now=1000+phase*1000;s=_start_alert(s,phase,now)
  for kind in (*GUARD_ROUTES,'sleeper'):
   a=guard_pose_at(s,kind,phase+20,now+19999);b=guard_pose_at(s,kind,phase+20,now+20000)
   assert math.dist((a.x,a.y),(b.x,b.y))<3,(kind,phase)
