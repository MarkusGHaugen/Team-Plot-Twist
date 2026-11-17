"""Run the shipped Canvas rules in Node and compare with Python's rules."""
import json
from pathlib import Path
import shutil
import subprocess
from dataclasses import asdict, replace
import pytest
from logic import MAP_CONFIG, FLOORS, STAIRS, BARRELS, CRATES, Position, advance_player, initial_state

NODE=shutil.which('node')
pytestmark=pytest.mark.skipif(NODE is None,reason='Node is needed to execute the actual Canvas rules')


def require_node():
    # Other test modules also call this helper directly, outside this module's
    # skip marker. Keep their Python tests usable when Node is not installed.
    if NODE is None:
        pytest.skip('Node is needed to execute the actual Canvas rules')
    return NODE


def canvas(expression, payload):
    node = require_node()
    source=Path('game_component/game.js').read_text().replace('export default function','function mount')
    script="const vm=require('vm');let v=JSON.parse(require('fs').readFileSync(0,'utf8'));let c={};vm.createContext(c);vm.runInContext(v.source,c);c.input=v.payload;console.log(JSON.stringify(vm.runInContext(v.expression,c)));"
    result=subprocess.run([node,'-e',script],input=json.dumps({'source':source,'payload':payload,'expression':expression}),text=True,capture_output=True,check=True)
    return json.loads(result.stdout)


def test_canvas_movement_matches_python_at_every_floor_stair_and_boundary():
    positions=[Position(z,x) for z,(a,b,y) in FLOORS.items() for x in (a,a+20,b-20,b)]
    positions += [Position(z,v) for z in STAIRS for v in (0,.3,.9,1)]
    positions += [Position('mast',v) for v in (0,.5,1)]
    cases=[(asdict(p),opened,h,v,.1) for p in positions for opened in (False,True) for h,v in ((1,0),(-1,0),(0,1),(0,-1))]
    expected=[asdict(advance_player(Position(**p),o,h,v,dt)) for p,o,h,v,dt in cases]
    actual=canvas('input.cases.map(a=>move(...a,input.rules))',{'cases':cases,'rules':MAP_CONFIG})
    for a,b in zip(actual,expected):
        assert a['zone']==b['zone']
        assert a['value']==pytest.approx(b['value'])


def test_f_examines_crates_e_takes_and_other_context_controls_remain_consistent():
    state=asdict(replace(initial_state(),has_key=True,door_open=True))
    cases=[]
    for name,zone,x in CRATES:
        cases.append((Position(zone,x),'f','search_crate'))
        cases.append((Position(zone,x),'e','take_lamp' if name=='crate_hold_b' else 'empty_pickup'))
    for name,zone,x in BARRELS: cases.append((Position(zone,x),'f','barrel'))
    cases += [(Position('cabin',460),'f','wardrobe'),(Position('cabin',460),'e','outfit'),
              (Position('cabin',300),'f','hammock'),(Position('cabin',300),'e','steal_blue'),
              (Position('chest_room',1120),'f','unlock_chest'),(Position('chest_room',1120),'e','take_pistol'),
              (Position('cell',374),'f','open'),(Position('cell',374),'e','steal')]
    actual=canvas('input.cases.map(([p,k])=>interactionKind(input.state,p,k,input.rules))',
                  {'cases':[(asdict(p),k) for p,k,_ in cases],'state':state,'rules':MAP_CONFIG})
    assert actual==[expected for _,_,expected in cases]


def test_movement_during_unacknowledged_action_is_not_lost_or_sent_over_trigger():
    from logic import GUARD_ROUTES
    data={**asdict(replace(initial_state(),position=Position('cell',374),has_key=True)),
          'rules':MAP_CONFIG,'guard_routes':{k:[asdict(s) for s in v] for k,v in GUARD_ROUTES.items()},
          'run_id':'protocol-test','feedback':{'seq':0},'guard_started_ms':0}
    expression=r'''(() => {
      const handlers={}, triggers=[], reports=[];
      globalThis.Element=class {closest(){return null;}};
      globalThis.window={addEventListener:(k,f)=>handlers[k]=f,removeEventListener:()=>{}};
      globalThis.document={querySelector:()=>null};
      globalThis.performance={now:()=>1000};
      globalThis.requestAnimationFrame=()=>1;globalThis.cancelAnimationFrame=()=>{};
      const el=()=>({addEventListener:()=>{},removeEventListener:()=>{},querySelector:()=>el(),classList:{toggle:()=>{}},lastElementChild:{},focus:()=>{}});
      const parent={querySelector:()=>el(),querySelectorAll:()=>[]};
      const args={data:input,parentElement:parent,key:'protocol',setTriggerValue:(k,v)=>triggers.push(v),setStateValue:(k,v)=>reports.push(v)};
      mount(args);
      const event=k=>({key:k,target:new Element(),repeat:false,preventDefault:()=>{}});
      handlers.keydown(event('f'));
      handlers.keydown(event('a'));handlers.keyup(event('a'));
      const during=reports.length;
      mount({...args,data:{...input,door_open:true,feedback:{seq:1,accepted:true,text:'Åpen'}}});
      handlers.keydown(event('a'));handlers.keyup(event('a'));
      return {triggers:triggers.length,during,position:reports.at(-1),actionPosition:triggers[0].position};
    })()'''
    result=canvas(expression,data)
    assert result['triggers']==1 and result['during']==0
    assert result['actionPosition']['value']==374
    assert result['position']['value']==pytest.approx(374-2*.09*MAP_CONFIG['player_speed'])
