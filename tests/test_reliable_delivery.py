from dataclasses import replace
from logic import initial_state,Position,guard_time,raise_alert,guard_pose_at,can_guard_see
from db import connect_db,restore_game,load_game

def test_door_alarm_checks_inside_cell_first():
 import json
 s=replace(initial_state(),has_key=True,door_open=True,position=Position('cell',230))
 alarm=raise_alert(s,guard_time('cell_return',.5),1000)
 assert alarm.accepted
 path=json.loads(alarm.state.alert_paths)['patrol']
 assert [180.,500.] in path
 assert path.index([180.,500.])<path.index([1320.,500.])
 assert can_guard_see(alarm.state,0,'patrol',2000)

def test_retry_executes_coin_pickup_once_and_stale_run_is_rejected(tmp_path):
 from action_transport import handle_action
 s=replace(initial_state(),has_key=True,door_open=True,position=Position('hold',760))
 p={'request_id':'one:1','run_id':'one','kind':'story_inspect','position':{'zone':'hold','value':760},'item':'coins_hold','guard_elapsed':0}
 with connect_db(tmp_path/'delivery.sqlite3') as c:
  restore_game(c,s,'player');cache={}
  first,_,duplicate=handle_action(c,p,'player','one',cache,1000)
  assert first.accepted and not duplicate
  before=c.total_changes
  retry,_,duplicate=handle_action(c,{**p,'delivery':2},'player','one',cache,1100)
  assert retry.accepted and duplicate and c.total_changes==before
  from logic import story_progress
  assert story_progress(load_game(c,'player'))['voyage']['coins']==1
  stale,_,_=handle_action(c,{**p,'request_id':'one:2'},'player','two',cache,1200)
  assert not stale.accepted and c.total_changes==before

def test_canvas_retries_lost_request_and_requires_matching_ack():
 from dataclasses import asdict
 from logic import MAP_CONFIG,GUARD_ROUTES
 from test_canvas_rules import canvas
 data={**asdict(replace(initial_state(),has_key=True,position=Position('cell',374))),
       'rules':MAP_CONFIG,'guard_routes':{k:[asdict(s) for s in v] for k,v in GUARD_ROUTES.items()},
       'run_id':'delivery-test','feedback':{'seq':0,'request_id':''}}
 result=canvas(r'''(() => {
  let time=0,frame;const handlers={},triggers=[];
  globalThis.Element=class {closest(){return null;}};
  globalThis.window={addEventListener:(k,f)=>handlers[k]=f,removeEventListener:()=>{}};
  globalThis.document={querySelector:()=>null};globalThis.performance={now:()=>time};
  globalThis.requestAnimationFrame=f=>{frame=f;return 1};globalThis.cancelAnimationFrame=()=>{};
  draw=()=>{};guardPose=()=>({x:900,y:365,facing:1,name:'pause'});
  guardCanSee=guardNoticesDoor=investigating=wardrobeInSight=()=>false;
  const el=()=>({addEventListener:()=>{},removeEventListener:()=>{},setAttribute:()=>{},querySelector:()=>el(),classList:{toggle:()=>{}},lastElementChild:{},focus:()=>{}});
  const parent={querySelector:()=>el(),querySelectorAll:()=>[]};
  const args={data:input,parentElement:parent,key:'reliable',setTriggerValue:(k,v)=>triggers.push(v),setStateValue:()=>{}};
  const event=k=>({key:k,target:new Element(),repeat:false,preventDefault:()=>{}});
  mount(args);handlers.keydown(event('f'));handlers.keydown(event('e'));
  const first=triggers[0].request_id;
  mount({...args,data:{...input,feedback:{seq:1,request_id:'older',accepted:true}}});
  const held=clients.get('reliable').actionInFlight;
  time=2001;frame(time);
  const retry=triggers[1];
  mount({...args,data:{...input,door_open:true,feedback:{seq:2,request_id:first,accepted:true}}});
  const second=triggers.at(-1).request_id;
  mount({...args,data:{...input,door_open:true,feedback:{seq:3,request_id:first,accepted:true}}});
  return {held,same:retry.request_id===first,retried:retry.delivery>triggers[0].delivery,queued:second!==first,stillWaiting:clients.get('reliable').actionInFlight};
 })()''',data)
 assert result=={'held':True,'same':True,'retried':True,'queued':True,'stillWaiting':True}


def test_closing_door_after_alarm_does_not_hide_prisoner_from_cell_search():
 from logic import open_door
 s=replace(initial_state(),has_key=True,door_open=True,position=Position('cell',360))
 alarm=raise_alert(s,guard_time('cell_return',.5),1000).state
 closed=open_door(alarm).state
 assert not closed.door_open and not closed.door_alerted
 assert can_guard_see(closed,0,'patrol',2000)
