"""Form controls in the component's shadow DOM must keep their own keys."""
from dataclasses import asdict

import pytest

from logic import MAP_CONFIG, initial_state
from test_canvas_rules import NODE, canvas

pytestmark = pytest.mark.skipif(NODE is None, reason='Node executes the Canvas controls')


def test_shadow_dom_volume_slider_does_not_move_or_crouch_the_player():
    data = {**asdict(initial_state()), 'rules': MAP_CONFIG, 'run_id': 'input-focus'}
    result = canvas(r'''(() => {
      const handlers={}, actions=[];
      globalThis.Element=class {constructor(field=false){this.field=field;} closest(){return this.field?this:null;}};
      globalThis.window={addEventListener:(k,f)=>handlers[k]=f,removeEventListener:()=>{}};
      globalThis.document={querySelector:()=>null};globalThis.performance={now:()=>0};
      globalThis.requestAnimationFrame=()=>1;globalThis.cancelAnimationFrame=()=>{};
      const el=()=>({addEventListener:()=>{},removeEventListener:()=>{},querySelector:()=>el(),
        classList:{toggle:()=>{}},lastElementChild:{},focus:()=>{}});
      mount({data:input,parentElement:{querySelector:()=>el(),querySelectorAll:()=>[]},
        key:'input-focus',setTriggerValue:(k,v)=>actions.push(v),setStateValue:()=>{}});
      const client=clients.get('input-focus'), before={...client.position};
      let prevented=0;
      const host=new Element(),slider=new Element(true);
      for(const key of ['ArrowRight',' ']) for(const type of ['keydown','keyup'])
        handlers[type]({key,target:host,composedPath:()=>[slider,host],repeat:false,
          preventDefault:()=>prevented++});
      return {before,after:client.position,prevented,actions:actions.length,keys:client.keys.size};
    })()''', data)
    assert result['after'] == result['before']
    assert result['prevented'] == 0
    assert result['actions'] == 0
    assert result['keys'] == 0
