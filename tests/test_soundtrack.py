import json,subprocess,shutil
from pathlib import Path
from dataclasses import asdict,replace
from logic import initial_state,Position,MAP_CONFIG,toggle_hammock
from test_canvas_rules import canvas

def test_hammock_action_and_prompt_stay_at_cabin():
 s=replace(initial_state(),has_key=True,door_open=True,position=Position('chest_room',1120))
 assert not toggle_hammock(s).accepted
 d={**asdict(s),'rules':MAP_CONFIG,'story':{'voyage':{}},'sleeper_alive':True,'has_blue_key':False}
 result=canvas("(()=>{watchCrew=()=>({x:1120,y:500});return {prompt:blueKeyPrompt({data:input,position:input.position}),action:interactionKind(input,input.position,'f',input.rules)};})()",d)
 assert result['prompt']=='E · Steal the blue key'
 assert result['action']!='hammock'

def test_walking_blue_key_draws_even_with_pistol():
 result=canvas("(()=>{let calls=0;drawBlueKey=()=>calls++;const ctx=new Proxy({},{get:()=>()=>{}});drawWatchKey(ctx,{sleeper_alive:true,has_blue_key:false},{x:1100,y:500,name:'watch'});drawWatchKey(ctx,{sleeper_alive:true,has_blue_key:true},{x:1100,y:500,name:'watch'});drawWatchKey(ctx,{sleeper_alive:true,has_blue_key:false},{x:300,y:365,name:'sleep'});return calls;})()",{})
 assert result==1


def async_canvas(expression):
 source=Path('game_component/game.js').read_text().replace('export default function','function mount')
 runner="const vm=require('vm'),v=JSON.parse(require('fs').readFileSync(0,'utf8')),c={URL};vm.createContext(c);vm.runInContext(v.source,c);Promise.resolve(vm.runInContext(v.expression,c)).then(r=>console.log(JSON.stringify(r))).catch(e=>{console.error(e);process.exitCode=1});"
 result=subprocess.run([shutil.which('node'),'-e',runner],input=json.dumps({'source':source,'expression':expression}),capture_output=True,text=True,check=True)
 return json.loads(result.stdout)

MOCK=r'''
let count=0,interval,clock=1000;
globalThis.document={hidden:false,baseURI:'https://example.com/~/+/'};
globalThis.Date={now:()=>clock};globalThis.setInterval=fn=>{interval=fn;return 1};globalThis.clearInterval=()=>{};
globalThis.Audio=class {constructor(src){count++;this.src=src;this.currentTime=0;this.paused=true;this.error=null;}addEventListener(){}pause(){this.paused=true;}play(){this.paused=false;return Promise.resolve();}};
const calm={run_id:'one',capture_phase:'none',alert_until_ms:0,guard_routes:{},story:{}};
'''

def test_recordings_switch_reset_loop_and_survive_rerenders():
 result=async_canvas('(async()=>{'+MOCK+r'''
 const m=musicEngine();m.touch(calm);await m.toggle();
 const e=m.tracks.explore,a=m.tracks.alert;e.currentTime=123;m.touch(calm);
 const resumed=e.currentTime===123&&!e.paused;
 m.touch({...calm,alert_until_ms:2000});const alert=!a.paused&&e.paused&&a.currentTime===0;
 a.currentTime=17;m.touch({...calm,alert_until_ms:2000});const continuous=a.currentTime===17;
 m.touch(calm);e.currentTime=412.01;interval();const clipped=e.currentTime===0;
 a.currentTime=45;m.touch({...calm,alert_until_ms:2000});const reset=a.currentTime===0;
 m.touch({...calm,run_id:'two'});const newGame=e.currentTime===0&&a.currentTime===0;
 document.hidden=true;m.touch({...calm,run_id:'two'});const hidden=a.paused&&e.paused;
 document.hidden=false;m.touch({...calm,run_id:'two'});const visible=!e.paused;
 await m.toggle();const stopped=e.paused&&a.paused&&m.timer===null;
 return {count,resumed,alert,continuous,clipped,reset,newGame,hidden,visible,stopped,url:e.src};
 })()''')
 assert result==dict(count=2,resumed=True,alert=True,continuous=True,clipped=True,reset=True,newGame=True,hidden=True,visible=True,stopped=True,url='https://example.com/~/+/app/static/music/exploration-v1.ogg')

def test_failed_playback_turns_off_and_reports_error():
 result=async_canvas('(async()=>{'+MOCK+r'''
 Audio.prototype.play=()=>Promise.reject(new Error('blocked'));
 const m=musicEngine();m.touch(calm);await m.toggle();await Promise.resolve();await Promise.resolve();
 return {enabled:m.enabled,timer:m.timer,error:m.error};
 })()''')
 assert not result['enabled'] and result['timer'] is None and 'could not start' in result['error']


def opus_duration(path):
 import struct
 data=path.read_bytes();offset=0;granule=0;skip=None
 while offset<len(data):
  assert data[offset:offset+4]==b'OggS'
  n=data[offset+26];laces=data[offset+27:offset+27+n];body=offset+27+n
  if skip is None:
   assert data[body:body+8]==b'OpusHead';skip=struct.unpack_from('<H',data,body+10)[0]
  g=struct.unpack_from('<q',data,offset+6)[0];granule=max(granule,g)
  offset=body+sum(laces)
 return (granule-skip)/48000


def test_shipped_audio_is_trimmed_exploration_and_full_alert():
 import pytest
 assert opus_duration(Path('static/music/exploration-v1.ogg'))==pytest.approx(412,abs=.03)
 assert opus_duration(Path('static/music/alert-v1.ogg'))==pytest.approx(4004.10,abs=.1)
