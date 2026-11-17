// Local Streamlit v2 component. The fixed map is mirrored from logic.py; only
// player progress is sent back to Python for validation and SQLite storage.
const clients = globalThis.__teamPlotTwistClients ??= new Map();
const ZONE_NAMES = {
  cell: "Cell", hold: "Hold", lower_stair: "Lower stairs",
  cabin: "Cabin", hammock: "Upper hammock", mid: "Middle deck",
  dining: "Mess hall", chest_room: "Chest room",
  upper_stair: "Upper stairs", upper_deck: "Upper deck", kitchen: "Galley",
  mast: "Mast", mast_top: "Mast top",
  sail_store:"Sail store", armory:"Armory", provisions:"Provisions",
  infirmary:"Infirmary", crew_room:"Crew quarters", officers:"Officers passage",
  aft_deck:"Aft deck", chart_room:"Chart room", captain:"Captain cabin",
  sail_stair:"Sail store stairs", aft_stair:"Aft stairs",
  provisions_stair:"Provisions stairs", captain_stair:"Captain stairs",
};

function musicEngine() {
  const previous=globalThis.__teamPlotTwistMusic;
  if(previous?.version===4)return previous;
  if(previous){previous.enabled=false;if(previous.timer)clearInterval(previous.timer);previous.ctx?.close?.();}
  const m={version:4,enabled:false,volume:.22,mode:'explore',timer:null,lastTouch:0,runId:null,active:null,error:'',tracks:null,sfxCtx:null};
  try {const saved=Number(localStorage.getItem('team-pt-music-volume')??.22);if(Number.isFinite(saved))m.volume=Math.max(0,Math.min(.6,saved));}catch(_){}
  m.ensureTracks=()=>{
    if(m.tracks)return;
    m.tracks={explore:new Audio(new URL('app/static/music/exploration-v1.ogg',document.baseURI).href),alert:new Audio(new URL('app/static/music/alert-v1.ogg',document.baseURI).href)};
    for(const audio of Object.values(m.tracks)) {
      audio.preload='none';audio.loop=true;audio.volume=m.volume;
      audio.addEventListener('error',()=>{m.error='Music could not load. Click Music to retry.';m.enabled=false;m.stop();});
    }
  };
  m.stop=()=>{if(m.timer){clearInterval(m.timer);m.timer=null;}if(m.tracks)for(const audio of Object.values(m.tracks))audio.pause();m.active=null;};
  m.sync=()=>{
    if(!m.tracks)return;
    const wanted=m.enabled&&!document.hidden&&m.mode!=='ending'?m.mode:null;
    for(const [kind,audio] of Object.entries(m.tracks)){audio.volume=m.volume;if(kind!==wanted)audio.pause();}
    if(m.tracks.explore.currentTime>=412)m.tracks.explore.currentTime=0;
    if(m.active===wanted)return;
    m.active=wanted;
    if(wanted){const audio=m.tracks[wanted];
      Promise.resolve(audio.play()).then(()=>{if(m.active!==wanted)audio.pause();}).catch(error=>{
        if(error.name==='AbortError'||m.active!==wanted)return;
        m.error='Music could not start. Click Music to retry.';m.enabled=false;m.stop();
      });
    }
  };
  m.ensureSfx=()=>{
    try{const AudioContextClass=window.AudioContext||window.webkitAudioContext;if(!AudioContextClass)return null;m.sfxCtx||(m.sfxCtx=new AudioContextClass());if(m.sfxCtx.state==='suspended')m.sfxCtx.resume();return m.sfxCtx;}catch(_){return null;}
  };
  m.playSplash=()=>{
    if(!m.enabled)return;
    try{
      const ac=m.ensureSfx();if(!ac)return;
      const length=Math.floor(ac.sampleRate*.48),buffer=ac.createBuffer(1,length,ac.sampleRate),samples=buffer.getChannelData(0);
      for(let i=0;i<length;i++){const fade=1-i/length;samples[i]=(Math.random()*2-1)*fade*fade;}
      const noise=ac.createBufferSource(),filter=ac.createBiquadFilter(),gain=ac.createGain();noise.buffer=buffer;filter.type='lowpass';filter.frequency.setValueAtTime(1800,ac.currentTime);filter.frequency.exponentialRampToValueAtTime(260,ac.currentTime+.42);gain.gain.setValueAtTime(Math.max(.01,m.volume*.7),ac.currentTime);gain.gain.exponentialRampToValueAtTime(.001,ac.currentTime+.46);noise.connect(filter);filter.connect(gain);gain.connect(ac.destination);noise.start();noise.stop(ac.currentTime+.48);
      const plop=ac.createOscillator(),pg=ac.createGain();plop.type='sine';plop.frequency.setValueAtTime(210,ac.currentTime);plop.frequency.exponentialRampToValueAtTime(65,ac.currentTime+.19);pg.gain.setValueAtTime(Math.max(.01,m.volume*.38),ac.currentTime);pg.gain.exponentialRampToValueAtTime(.001,ac.currentTime+.2);plop.connect(pg);pg.connect(ac.destination);plop.start();plop.stop(ac.currentTime+.21);
    }catch(_){}
  };
  m.touch=(data,introActive=false,introTime=0,finaleDark=false)=>{
    m.lastTouch=Date.now();const run=String(data.run_id??'');
    if(m.runId!==run){m.runId=run;m.error='';if(m.tracks)for(const audio of Object.values(m.tracks))audio.currentTime=0;}
    const tense=data.capture_phase==='active'||gameNow(data)<data.alert_until_ms||(data.story?.voyage?.armed&&(data.sleeper_alive||Object.keys(data.guard_routes||{}).some(k=>data[k+'_alive'])));
    const mode=finaleDark?'alert':data.ending?'ending':introActive?(introTime>=15.3?'alert':'explore'):tense?'alert':'explore';
    if(mode!==m.mode){if(mode==='alert'&&m.tracks)m.tracks.alert.currentTime=0;m.mode=mode;}
    m.sync();
  };
  m.toggle=async()=>{
    m.ensureTracks();m.enabled=!m.enabled;m.error='';m.lastTouch=Date.now();
    if(m.enabled){
      m.ensureSfx();
      for(const audio of Object.values(m.tracks))if(audio.error)audio.load();
      if(!m.timer)m.timer=setInterval(()=>{if(Date.now()-m.lastTouch>2000){m.enabled=false;m.stop();}else m.sync();},250);
      m.sync();
    }else m.stop();
  };
  globalThis.__teamPlotTwistMusic=m;return m;
}
function guideDistance(e,now) {
  const distance=e.distance===undefined?(now-e.started)/1000*85:e.distance+(e.paused?0:Math.max(0,now-e.updated)/1000*85);
  return Math.min(e.target??Infinity,distance);
}
function guidePosition(e,now) {return pointOnPath(e.path,guideDistance(e,now));}
function positionAtXY(p,rules) {
  const floor=floorZone(p.y,p.x,rules);if(floor)return {zone:floor,value:p.x};
  for(const [zone,[x1,y1,x2,y2]] of Object.entries(rules.stairs)) {
    const f=(p.y-y1)/(y2-y1);
    if(f>=0&&f<=1&&Math.abs(p.x-(x1+(x2-x1)*f))<2)return {zone,value:f};
  }
  return {zone:'hold',value:p.x};
}
// Drugged stew: mirrors feast.py. The saved plan fixes every walk, meal and nap.
const FEAST={walk:95,ret:60,sleep:120000,mid:1105};
function feastBack(f,kind) {
  const own=k=>f.sleep[k]+FEAST.sleep+pathLength(f.returns[k])/FEAST.ret*1000;
  return f.watch&&(kind==='cargo'||kind==='sleeper')?Math.max(...['cargo','sleeper'].filter(k=>k in f.sleep).map(own)):own(kind);
}
function feastShift(f){return f.watch?Math.trunc(feastBack(f,'cargo')-f.gather):0;}
function feastAlong(path,d) {
  const total=pathLength(path),p=pointOnPath(path,d),a=pointOnPath(path,Math.min(total,d+6)),b=pointOnPath(path,Math.max(0,d-6));
  return {x:p.x,y:p.y,facing:a.x>b.x?1:a.x<b.x?-1:1};
}
function feastPose(d,kind) {
  const f=d.story?.voyage?.feast,now=gameNow(d);
  if(!f||!f.paths[kind]||!d[kind+'_alive']||now<f.gather)return null;
  const path=f.paths[kind],walked=(now-f.gather)/1000*FEAST.walk;
  if(walked<pathLength(path))return {...feastAlong(path,walked),name:kind==='dining'?'feast_serve':'feast_walk'};
  const [x,y]=path[path.length-1],table=x<FEAST.mid?1:-1;
  if(now<f.sleep[kind])return {x,y,facing:table,name:'feast_eat'};
  if(now<f.sleep[kind]+FEAST.sleep)return {x,y,facing:table,name:'feast_sleep'};
  const ret=f.returns[kind],back=(now-f.sleep[kind]-FEAST.sleep)/1000*FEAST.ret;
  if(back<pathLength(ret))return {...feastAlong(ret,back),name:'feast_return'};
  if(now<feastBack(f,kind)){const [px,py]=ret[ret.length-1];return {x:px,y:py,facing:1,name:'feast_post'};}
  return null;
}
function feastResumed(d,kind) {
  const v=d.story?.voyage||{},f=v.feast,now=gameNow(d);
  if(!f||f.resume[kind]===undefined||!d[kind+'_alive'])return null;
  const done=feastBack(f,kind);if(now<done)return null;
  if(kind==='patrol'&&(d.suspect_started_ms||d.patrol_resume_ms>=done))return null;
  const g=v.guide;if(g&&kind===(g.kind==='cook'?'dining':'boatswain')&&g.started>f.drugged)return null;
  return routinePose(d,kind,f.resume[kind]+(now-done)/1000);
}
function feastStage(d) {
  const f=d.story?.voyage?.feast;if(!f)return '';
  if(gameNow(d)<f.gather)return 'cooking';
  const names=Object.keys(f.sleep).filter(k=>d[k+'_alive']).map(k=>feastPose(d,k)?.name);
  if(names.length&&names.every(n=>n==='feast_sleep'))return 'asleep';
  if(names.some(n=>n==='feast_sleep'))return 'dozing';
  if(names.some(n=>n==='feast_serve'||n==='feast_walk'))return 'gathering';
  if(names.some(n=>n==='feast_eat'))return 'eating';
  if(names.some(n=>n==='feast_return'||n==='feast_post'))return 'waking';
  return 'over';
}
function feastSecondsLeft(d) {
  const f=d.story?.voyage?.feast;if(!f)return 0;
  const wakes=Object.keys(f.sleep).filter(k=>d[k+'_alive']).map(k=>f.sleep[k]+FEAST.sleep);
  return wakes.length?Math.max(0,Math.ceil((Math.min(...wakes)-gameNow(d))/1000)):0;
}
function drawFeastCrew(ctx,kind,pose,d,elapsed) {
  const style=d.rules.guard_styles[kind]||null,facing=pose.facing<0?'left':'right',t=performance.now()/1000;
  if(pose.name==='feast_eat'||pose.name==='feast_sleep') {
    ctx.save();ctx.translate(pose.x,pose.y);ctx.scale(1,.72);
    // Asleep: slumped forward, head on the table.
    if(pose.name==='feast_sleep'){ctx.translate(0,-17);ctx.rotate((pose.facing<0?-1:1)*1.05);ctx.translate(0,17);}
    person(ctx,0,0,true,elapsed,pose.name==='feast_eat'?'bowl':'none',facing,false,false,kind,style);
    ctx.restore();
    if(pose.name==='feast_eat'){const bob=Math.sin(t*5+pose.x)*4;line(ctx,pose.x+pose.facing*6,pose.y-30,pose.x+pose.facing*13,pose.y-40+bob,'#d9d1bf',2);}
    else {const k=(t*.6+pose.x*.013)%1;ctx.save();ctx.globalAlpha=1-k;label(ctx,'z',pose.x+pose.facing*16+k*8,pose.y-46-k*26,9+k*9);ctx.restore();}
    return;
  }
  person(ctx,pose.x,pose.y,true,elapsed,'none',facing,pose.name!=='feast_post',false,kind,style);
  if(pose.name==='feast_serve') {
    const side=pose.facing<0?-1:1;
    roundBox(ctx,pose.x+side*14-13,pose.y-38,26,17,6,'#4f5552','#2b2c2b');line(ctx,pose.x+side*14-14,pose.y-38,pose.x+side*14+14,pose.y-38,'#c3b084',3);
    ctx.strokeStyle='rgba(240,240,235,.5)';ctx.lineWidth=2;for(const o of [-5,4]){ctx.beginPath();ctx.moveTo(pose.x+side*14+o,pose.y-42);ctx.quadraticCurveTo(pose.x+side*14+o+5,pose.y-50,pose.x+side*14+o,pose.y-58+Math.sin(t*4+o)*2);ctx.stroke();}
  }
}
function guidePose(d,kind) {
  const v=d.story?.voyage||{},e=v.escort,g=v.guide,now=gameNow(d);
  if(e&&kind===(e.kind==='cook'?'dining':'boatswain')) {
    const distance=guideDistance(e,now),p=pointOnPath(e.path,distance+24),q=pointOnPath(e.path,distance+32);
    return {...p,facing:q.x<p.x?-1:1,name:e.paused?'guiding_wait':'guiding'};
  }
  if(g&&kind===(g.kind==='cook'?'dining':'boatswain')) {
    if(d.alert_started_ms>g.started||v.armed)return null;
    const total=pathLength(g.path),distance=Math.min(24,total)+Math.max(0,now-g.started)/1000*85;
    if(distance>=total) {
      if(d.alert_started_ms>g.started)return null;
      return baseGuardPose({...d,guard_started_ms:now-(g.resume_elapsed+(distance-total)/85)*1000,alert_until_ms:0,patrol_resume_ms:0},kind);
    }
    const p=pointOnPath(g.path,distance),q=pointOnPath(g.path,distance+8);
    return {...p,facing:q.x>=p.x?1:-1,name:now<g.speech_until?'guide_farewell':'returning_to_post'};
  }
  return null;
}
function clamp(value, low, high) { return Math.max(low, Math.min(high, value)); }
function positionXY(position, rules) {
  const v = position.value;
  if (position.zone === "mast") return {x:rules.mast_x,y:245-(245-rules.mast_top_y)*v};
  if (position.zone === "mast_top") return {x:v,y:rules.mast_top_y};
  const floor = rules.floors[position.zone === "hammock" ? "cabin" : position.zone];
  if (floor) return { x: v, y: floor[2] };
  const stair = rules.stairs[position.zone];
  if (stair) return { x: stair[0] + (stair[2] - stair[0]) * v, y: stair[1] + (stair[3] - stair[1]) * v };
  return { x: 230, y: 500 };
}

function floorZone(y,x,rules) {
  return Object.entries(rules.floors).filter(([,f])=>f[2]===y && f[0]<=x && x<=f[1]).at(-1)?.[0];
}
function move(position, doorOpen, horizontal, vertical, dt, rules) {
  const z=position.zone,v=position.value;
  dt=clamp(dt,0,3);
  const floorPosition=(x,y)=>({zone:floorZone(y,x,rules),value:x});
  if(z==="hammock") return position;
  if(z==="mast") {
    const p=v+vertical*rules.mast_speed*dt;
    if(p>=1) return {zone:"mast_top",value:rules.mast_x};
    if(p<=0) return {zone:"upper_deck",value:rules.mast_x};
    return {zone:z,value:p};
  }
  if(z==="mast_top") {
    if(vertical<0 && Math.abs(v-rules.mast_x)<=30) {
      const p=1+vertical*rules.mast_speed*dt;
      return p<=0?{zone:"upper_deck",value:rules.mast_x}:{zone:"mast",value:p};
    }
    return {zone:z,value:clamp(v+horizontal*rules.player_speed*dt,rules.mast_x-40,rules.mast_x+40)};
  }
  const onStair=(name,p)=>{
    const [x1,y1,x2,y2]=rules.stairs[name];
    if(p<=0) return floorPosition(x1,y1);
    if(p>=1) return floorPosition(x2,y2);
    return {zone:name,value:p};
  };
  if(rules.stairs[z]) {
    if(horizontal && !vertical && (v<=.18 || v>=.82)) {
      const [x1,y1,x2,y2]=rules.stairs[z], [x,y]=v<=.18?[x1,y1]:[x2,y2];
      return floorPosition(clamp(x+horizontal*rules.player_speed*dt,rules.world_min,rules.world_max),y);
    }
    return onStair(z,v+vertical*rules.stair_speed*dt);
  }
  if(!rules.floors[z]) return position;
  const y=rules.floors[z][2];
  for(const [name,[x1,y1,x2,y2]] of Object.entries(rules.stairs)) {
    if(vertical>0 && y===y1 && z!=="cell" && v>=x1-45 && v<=x2+20) return onStair(name,dt*rules.stair_speed);
    if(vertical<0 && y===y2 && v>=x1-20 && v<=x2+45) return onStair(name,1-dt*rules.stair_speed);
  }
  if(z==="upper_deck" && vertical>0 && Math.abs(v-rules.mast_x)<=18)
    return {zone:"mast",value:Math.min(1,dt*rules.mast_speed)};
  let x=clamp(v+horizontal*rules.player_speed*dt,rules.world_min,rules.world_max);
  if(y===500 && !doorOpen) x=z==="cell"?Math.min(x,rules.closed_cell_max):Math.max(x,rules.closed_hold_min);
  return floorPosition(x,y);
}

function searchPose(data,kind) {
  const now=gameNow(data),armed=data.story?.voyage?.armed;
  if(!(now>=data.alert_started_ms&&now<data.alert_until_ms||armed))return null;
  let path=(data.parsedAlertPaths||JSON.parse(data.alert_paths||'{}'))[kind];
  if(!path&&armed&&kind==='sleeper')path=data.rules.watch_path||[[300,365],[540,365],[440,500],[1320,500]];
  if(!path)return null;
  const span=data.alert_until_ms-data.alert_started_ms,duration=span===data.rules.search_alert_ms?span:data.rules.alert_duration_ms;
  let phase=Math.max(0,now-data.alert_started_ms)/duration%2;
  if(phase>1){path=[...path].reverse();phase-=1;}
  const length=pathLength(path),distance=length*phase,p=pointOnPath(path,distance);
  let left=distance;
  for(let i=1;i<path.length;i++){const a=path[i-1],b=path[i],n=Math.hypot(b[0]-a[0],b[1]-a[1]);if(!n)continue;if(left<=n||i===path.length-1)return {...p,name:'search_'+kind,facing:b[0]>=a[0]?1:-1};left-=n;}
  return {...p,name:'search_'+kind,facing:1};
}
function routinePose(data,kind,elapsed) {
  const segments=data.guard_routes?.[kind]||[],cycle=segments.reduce((n,s)=>n+s.duration,0);let left=elapsed/(cycle||1);left=(left-Math.floor(left))*cycle;
  for(let i=0;i<segments.length;i++){const s=segments[i];if(left<s.duration){const f=left/s.duration,prev=segments[(i+segments.length-1)%segments.length];return {x:s.x1+(s.x2-s.x1)*f,y:s.y1+(s.y2-s.y1)*f,name:s.name,facing:s.x2===s.x1?(prev.x2>=prev.x1?1:-1):s.x2>s.x1?1:-1};}left-=s.duration;}
  return {x:1320,y:500,name:'watch',facing:-1};
}
function watchCrew(d,kind) {
  const meal=feastPose(d,kind);if(meal)return meal;
  const search=searchPose(d,kind);if(search)return search;
  if(kind==='cargo' && d.story?.voyage?.watch_start===undefined)return null;
  if(!(d.sleeper_alive&&d.cargo_alive)) return kind==='sleeper'?{x:300,y:365,name:d.story?.voyage?.armed?'armed_watch':'sleep',facing:positionXY(d.position,d.rules).x>=300?1:-1}:null;
  const v=d.story?.voyage||{},shift=v.feast&&gameNow(d)>=v.feast.gather?feastShift(v.feast):0,t=Math.max(0,(gameNow(d)-shift-(v.watch_start??gameNow(d)))/1000)%104;
  if(kind==='sleeper'?t<45:t>=52&&t<97)return {x:300,y:365,name:d.story?.voyage?.armed?'armed_watch':'sleep',facing:positionXY(d.position,d.rules).x>=300?1:-1};
  if(!(t>=45&&t<52||t>=97)){
    const watchRoute=d.rules.cargo_watch_route;if(watchRoute)return routinePose({...d,guard_routes:{...d.guard_routes,cargo:watchRoute}},'cargo',kind==='cargo'?t:t-52);
    const route=d.guard_routes?.cargo||d.rules.cargo_route;if(route){let phase=0;for(const s of route){if(s.name==='cargo_right_pause')break;phase+=s.duration;}return routinePose({...d,guard_routes:{...d.guard_routes,cargo:route}},'cargo',phase+(kind==='cargo'?t:t-52)*route.reduce((n,s)=>n+s.duration,0)/45);}
  }
  let f=1;
  if(t>=45&&t<52) f=kind==='sleeper'?(t-45)/7:1-(t-45)/7;
  if(t>=97) f=kind==='sleeper'?1-(t-97)/7:(t-97)/7;
  const path=d.rules.watch_path||[[300,365],[540,365],[440,500],[1320,500]];
  let left=f*path.slice(1).reduce((n,b,i)=>n+Math.hypot(b[0]-path[i][0],b[1]-path[i][1]),0);
  for(let i=1;i<path.length;i++) {const a=path[i-1],b=path[i],len=Math.hypot(b[0]-a[0],b[1]-a[1]);if(left<=len){const q=left/(len||1);return {x:a[0]+(b[0]-a[0])*q,y:a[1]+(b[1]-a[1])*q,name:'watch',facing:kind==='sleeper'?1:-1};}left-=len;}
  return {x:1320,y:500,name:'watch',facing:1};
}
// Online, every crew tick is a full server round trip, and a key press waits
// behind it. The server only needs one while something can happen between key
// presses: a fight, an escort, the first tick that starts the watch rota, or
// the sleeper close enough to spot the player. The reach is wider than the
// sleeper's 160px sight so network delay cannot hide a sighting.
const TICK_REACH_X=360,TICK_REACH_Y=60;
function crewTickNeeded(d,position) {
  const v=d.story?.voyage||{};
  if(v.armed||v.escort||v.watch_start===undefined)return true;
  if(!d.sleeper_alive||d.disguised||d.hidden_barrel||d.in_hammock)return false;
  const p=watchCrew(d,'sleeper');if(!p)return false;
  const xy=positionXY(position,d.rules);
  return Math.abs(xy.x-p.x)<=TICK_REACH_X&&Math.abs(xy.y-p.y)<=TICK_REACH_Y;
}

function gameNow(data) { return Number(data.paused_at_ms || data.uiPauseAt || Date.now()) - Number(data.paused_total_ms || 0); }
function guardElapsed(data,kind="patrol") {
  const now=gameNow(data), start=Number(data.guard_started_ms || now);
  return Math.max(0,(now-start)/1000);
}
function baseGuardPose(data, kind="patrol") {
  const now=gameNow(data);
  const search=searchPose(data,kind);if(search)return search;
  if(kind==="patrol" && data.suspect_started_ms && data.suspect_guard_zone) {
    const point=positionXY({zone:data.suspect_guard_zone,value:data.suspect_guard_value},data.rules);
    const px=positionXY(data.position,data.rules).x;
    return {...point,name:"inspection_pause",progress:0,facing:px>=point.x?1:-1};
  }
  const paths=data.parsedAlertPaths || {};
  const resumes=data.parsedAlertResume || {};
  const patrolOverride=kind==="patrol" && data.patrol_resume_ms && data.patrol_resume_ms>=data.alert_started_ms;
  if(!patrolOverride&&now>=Number(data.alert_started_ms)&&now<Number(data.alert_until_ms)&&paths[kind]){
    const path=paths[kind],distance=(now-Number(data.alert_started_ms))/1000*data.rules.guard_speed*data.rules.alert_speed;
    let left=Math.max(0,distance);
    for(let i=1;i<path.length;i++){
      const a=path[i-1],b=path[i],length=Math.hypot(b[0]-a[0],b[1]-a[1]);
      if(left<=length||i===path.length-1){
        const f=length?clamp(left/length,0,1):1;
        return {x:a[0]+(b[0]-a[0])*f,y:a[1]+(b[1]-a[1])*f,
          name:`search_${kind}`,progress:f,facing:b[0]>a[0]?1:b[0]<a[0]?-1:1};
      }
      left-=length;
    }
  }
  const segments = data.guard_routes?.[kind] || data.guard_segments || [];
  const cycle = segments.reduce((sum, segment) => sum + Number(segment.duration), 0);
  if (!cycle) return { x: 920, y: 365, name: "dining_out", progress: 0, facing:-1 };
  let remaining=(patrolOverride?data.patrol_resume_elapsed+Math.max(0,now-data.patrol_resume_ms)/1000:now>=Number(data.alert_until_ms)&&Number(data.alert_until_ms)>0&&resumes[kind]!==undefined
    ? Number(resumes[kind])+(now-Number(data.alert_until_ms))/1000 : guardElapsed(data,kind))%cycle;
  for (let i=0;i<segments.length;i++) {
    const segment=segments[i];
    const duration = Number(segment.duration);
    if (remaining < duration) {
      const progress = remaining / duration;
      return {
        x: Number(segment.x1) + (Number(segment.x2) - Number(segment.x1)) * progress,
        y: Number(segment.y1) + (Number(segment.y2) - Number(segment.y1)) * progress,
        name: segment.name, progress,
        facing: Number(segment.x2) === Number(segment.x1)
          ? (Number(segments[(i+segments.length-1)%segments.length].x2)>=Number(segments[(i+segments.length-1)%segments.length].x1)?1:-1)
          : Number(segment.x2) > Number(segment.x1) ? 1 : -1,
      };
    }
    remaining -= duration;
  }
  return { x: 920, y: 365, name: "dining_out", progress: 0, facing:-1 };
}
function guardPose(data,kind="patrol") {
  const meal=feastPose(data,kind)||feastResumed(data,kind);if(meal)return meal;
  const guided=guidePose(data,kind);if(guided)return guided;
  const pose=(kind==='cargo'?watchCrew(data,kind):null)||baseGuardPose(data,kind),signal=data.story?.signal,now=gameNow(data);
  if(signal && signal.started<=now && now<signal.until && now>=Number(data.alert_until_ms)
      && !(kind==="patrol" && data.suspect_started_ms)
      && Math.abs(pose.y-signal.y)<=data.rules.vision_height && Math.abs(pose.x-signal.x)<=400) {
    return {...pose,facing:signal.x>=pose.x?1:-1};
  }
  return pose;
}
function guardCanSee(client, guard, kind="patrol") {
  const d=client.data, r=d.rules;
  if(d.story?.voyage?.escort && kind===(d.story.voyage.escort.kind==='cook'?'dining':'boatswain'))return false;
  if(d.story?.voyage?.armed || d.story?.voyage?.escort?.hidden || guard.name==='sleep' || guard.name==='feast_sleep')return false;
  if (!d[`${kind}_alive`] || d.disguised || d.hidden_barrel || d.in_hammock || d.capture_phase !== "none") return false;
  const p=positionXY(client.position,r);
  if(client.position.zone==='cell')return kind==='patrol'&&gameNow(d)>=d.alert_started_ms&&gameNow(d)<d.alert_until_ms&&guard.y===500&&guard.x<=390;
  const ahead=(p.x-guard.x)*guard.facing;
  const range=r.guard_styles[kind].vision*(d.has_lamp&&d.lamp_lit&&d.held_item==="lamp"?r.lamp_vision_multiplier:1);
  return ahead>=12 && ahead<=range && Math.abs(p.y-guard.y)<=r.vision_height;
}
function guardNoticesDoor(client, guard) {
  const d=client.data;
  return d.patrol_alive && d.door_open && !d.door_alerted && d.capture_phase === "none"
    && guard.x>=410 && guard.x<=455 && Math.abs(guard.y-500)<1;
}
function nearProp(position, props, reach) {
  return props.find(([,zone,x]) => position.zone===zone && Math.abs(position.value-x)<=reach);
}
function storyPoint(position,r,state=null) {
  const pills=(state?.story?.items||[]).includes('sleeping_pills');
  return Object.entries(r.story_points || {}).find(([,p])=>position.zone===p.zone && Math.abs(position.value-p.x)<=p.reach && (p.kind!=='cell_floor'||pills));
}
function blueKeyPrompt(client) {
  const d=client.data,wp=watchCrew(d,'sleeper'),xy=positionXY(client.position,d.rules);
  if(!d.sleeper_alive||d.has_blue_key||!wp||Math.abs(xy.x-wp.x)>d.rules.sleeper_range||Math.abs(xy.y-wp.y)>25)return '';
  const atBed=client.position.zone==='cabin'&&Math.abs(client.position.value-d.rules.sleeper_x)<=d.rules.sleeper_range;
  return 'E · Steal the blue key'+(atBed?' · F · Rest in upper hammock':'');
}
function drawBlueKey(ctx,x,y) {
  ctx.save();ctx.shadowColor='#6cb6ff';ctx.shadowBlur=12;ctx.strokeStyle='#6cb6ff';ctx.lineWidth=3;
  ctx.beginPath();ctx.arc(x+20,y-30,6,0,Math.PI*2);ctx.stroke();line(ctx,x+24,y-25,x+28,y-14,'#6cb6ff',3);line(ctx,x+27,y-18,x+33,y-20,'#6cb6ff',3);ctx.restore();
}
function drawWatchKey(ctx,data,pose) {if(data.sleeper_alive&&!data.has_blue_key&&pose.name!=='sleep')drawBlueKey(ctx,pose.x,pose.y);}
function ambushTarget(client) {
  const d=client.data,barrel=d.rules.barrels.find(b=>b[0]===d.hidden_barrel);
  if(!barrel||Object.values(d.story?.voyage?.concealed||{}).includes(d.hidden_barrel))return null;
  const xy=positionXY(client.position,d.rules);
  return [...Object.keys(d.guard_routes),'sleeper'].map(kind=>[kind,kind==='sleeper'?watchCrew(d,kind):guardPose(d,kind)])
    .filter(([kind,p])=>d[kind+'_alive']&&p&&Math.abs(p.x-xy.x)<=58&&Math.abs(p.y-xy.y)<=22)
    .sort((a,b)=>Math.abs(a[1].x-xy.x)-Math.abs(b[1].x-xy.x))[0]||null;
}
// Barrel ambush cutscene: pop up, grab the crew member, haul them over the rim
// and stuff them head first into the barrel, then settle back to just the hat.
const AMBUSH_MS=1500;
function easeInOut(t){return t<.5?2*t*t:1-2*(1-t)*(1-t);}
function quadPoint(a,b,c,t){const u=1-t;return {x:u*u*a.x+2*u*t*b.x+t*t*c.x,y:u*u*a.y+2*u*t*b.y+t*t*c.y};}
function ambushMotion(a,ms) {
  const rim=a.by-47,side=a.x>=a.bx?1:-1,turn=-side*Math.PI;
  const start={x:a.x,y:a.y-35},grabbed={x:a.x-side*7,y:a.y-37},peak={x:a.bx+side*14,y:rim-80},dip={x:a.bx,y:rim+5};
  let phase,lift,guard=null,angle=0,kick=false,startled=false,wobble=0;
  if(ms<180){phase='pop';lift=1-(1-ms/180)**2;guard=start;}
  else if(ms<420){phase='grab';const u=(ms-180)/240;lift=1;startled=true;
    guard={x:start.x+(grabbed.x-start.x)*u,y:start.y+(grabbed.y-start.y)*u};angle=-side*.16*u;}
  else if(ms<900){phase='haul';const u=easeInOut((ms-420)/480);lift=1-.75*u;
    guard=quadPoint(grabbed,peak,dip,u);angle=-side*.16+(turn+side*.16)*u;}
  else if(ms<1150){phase='plunge';const u=(ms-900)/250;lift=.25*Math.max(0,1-u*3);kick=true;
    guard={x:a.bx,y:dip.y+(rim+52-dip.y)*u*u};angle=turn+Math.sin(ms/22)*.1*(1-u);}
  else {phase=ms<AMBUSH_MS?'settle':'done';lift=0;const u=clamp((ms-1150)/(AMBUSH_MS-1150),0,1);
    wobble=Math.sin(u*Math.PI*5)*.08*(1-u);}
  // Hands hold the collar: the shoulder point of the rotated body.
  const hands=guard&&lift>.05?{x:guard.x+9*Math.sin(angle),y:guard.y-9*Math.cos(angle)}:null;
  return {phase,lift,guard,angle,kick,startled,wobble,hands,side,rim,done:ms>=AMBUSH_MS};
}
function barrelLurker(ctx,x,rim,lift,hands,coat,hatColor,band) {
  const head=rim+8-34*lift,brim=head-9;
  ctx.save();ctx.beginPath();ctx.rect(x-200,rim-300,400,300);ctx.clip();
  if(hands&&lift>.05) for(const s of [-1,1]) {
    const sx=x+s*10,sy=head+17,hx=hands.x+s*5,hy=hands.y+s*3;
    const ex=(sx+hx)/2+s*4,ey=Math.min(sy,hy)-8;
    line(ctx,sx,sy,ex,ey,coat,6);line(ctx,ex,ey,hx,hy,coat,6);
    ctx.fillStyle='#d0a173';ctx.beginPath();ctx.arc(hx,hy,4,0,Math.PI*2);ctx.fill();
  }
  if(lift>.02){
    roundBox(ctx,x-12,head+9,24,32,5,coat,'#2c2927');
    ctx.fillStyle='#d0a173';ctx.beginPath();ctx.arc(x,head,10,0,Math.PI*2);ctx.fill();
    ctx.fillStyle='#272622';ctx.beginPath();ctx.arc(x+(hands&&hands.x<x?-4:4),head-1,1.5,0,Math.PI*2);ctx.fill();
  }
  ctx.fillStyle=hatColor;ctx.beginPath();ctx.moveTo(x-17,brim);ctx.lineTo(x-9,brim-12);
  ctx.lineTo(x+8,brim-12);ctx.lineTo(x+17,brim);ctx.fill();
  line(ctx,x-20,brim,x+20,brim,band,4);
  ctx.restore();
}
function drawAmbush(ctx,client,anim,now) {
  const d=client.data,m=ambushMotion(anim,now-anim.start),vv=d.story?.voyage||{};
  const coat=vv.captain_worn?d.rules.guard_styles.officer.color:d.disguised?'#9c3d33':'#2d6b73';
  const lurk=()=>barrelLurker(ctx,anim.bx,m.rim,m.lift,m.hands,coat,d.disguised?'#302b29':'#273a40','#c6b180');
  if(m.kick)lurk();
  if(m.guard){
    // Everything inside the barrel below its rim stays hidden.
    ctx.save();ctx.beginPath();ctx.rect(anim.bx-4000,anim.by-4000,8000,8000);ctx.rect(anim.bx-21,m.rim+1,42,80);ctx.clip('evenodd');
    ctx.save();ctx.translate(m.guard.x,m.guard.y);ctx.rotate(m.angle);
    person(ctx,0,35,true,m.kick?(now-anim.start)/260:0,'none',anim.x>=anim.bx?'left':'right',m.kick,false,anim.kind,d.rules.guard_styles[anim.kind]||null,false);
    ctx.restore();ctx.restore();
    if(m.startled)label(ctx,'!',m.guard.x-5,m.guard.y-50,25);
  }
  if(m.wobble){ctx.save();ctx.translate(anim.bx,anim.by);ctx.rotate(m.wobble);barrel(ctx,0,0,1);ctx.restore();}
  if(m.phase==='settle'){const u=(now-anim.start-1150)/(AMBUSH_MS-1150);ctx.fillStyle=`rgba(214,190,150,${.5*(1-u)})`;
    for(const s of [-1,1]){ctx.beginPath();ctx.arc(anim.bx+s*(22+18*u),m.rim-4-6*u,4+5*u,0,Math.PI*2);ctx.fill();}}
  if(!m.kick)lurk();
  return m;
}
// Rats live in the hold and chest room. They wander between the cargo, stop to
// sniff, and bolt away squeaking when anyone comes close on their deck.
const RAT_FLOOR=500,RAT_MIN=420,RAT_MAX=1350,RAT_FEAR=95;
function ratRandom(seed){let s=seed>>>0;return ()=>{s=(Math.imul(s,1664525)+1013904223)>>>0;return s/4294967296;};}
function initRats(){return [480,705,960,1225].map((x,i)=>({x,dir:i%2?-1:1,mode:'sniff',until:0,speed:0,squeak:0,rand:ratRandom(97+i*31)}));}
function stepRats(rats,dt,threats,now) {
  for(const r of rats) {
    const near=threats.filter(t=>Math.abs(t.y-RAT_FLOOR)<20).map(t=>t.x-r.x).sort((a,b)=>Math.abs(a)-Math.abs(b))[0];
    if(near!==undefined&&Math.abs(near)<RAT_FEAR) {
      if(r.mode!=='flee')r.squeak=now+800;
      r.mode='flee';r.dir=near>0?-1:1;r.speed=260;r.until=now+900+r.rand()*500;
    } else if(now>=r.until) {
      if(r.mode==='flee'||r.rand()<.45){r.mode='sniff';r.speed=0;r.until=now+700+r.rand()*1800;}
      else {r.mode='scurry';r.dir=r.rand()<.5?-1:1;r.speed=70+r.rand()*60;r.until=now+500+r.rand()*1400;}
    }
    r.x+=r.dir*r.speed*dt;
    if(r.x<RAT_MIN){r.x=RAT_MIN;r.dir=1;}
    if(r.x>RAT_MAX){r.x=RAT_MAX;r.dir=-1;}
  }
  return rats;
}
function drawRat(ctx,r,now) {
  const t=now/1000,run=r.speed>0,bob=run?Math.sin(t*38+r.x)*1.2:0,sniff=run?0:Math.sin(t*14+r.x)*1.5;
  ctx.save();ctx.translate(r.x,RAT_FLOOR-5+bob);ctx.scale(r.dir*1.35,1.35);
  ctx.strokeStyle='#8f6f66';ctx.lineWidth=1.6;ctx.beginPath();ctx.moveTo(-9,0);
  ctx.quadraticCurveTo(-17,-2+Math.sin(t*9+r.x)*3,-25,2);ctx.stroke();
  ctx.fillStyle='#7a6a60';ctx.beginPath();ctx.ellipse(0,-3,10,5,0,0,Math.PI*2);ctx.fill();
  ctx.fillStyle='#a8968a';ctx.beginPath();ctx.ellipse(1,-1,7,2,0,0,Math.PI*2);ctx.fill();ctx.fillStyle='#7a6a60';
  ctx.beginPath();ctx.ellipse(9+sniff*.4,-4,5,3.4,-.15,0,Math.PI*2);ctx.fill();
  ctx.fillStyle='#d79a90';ctx.beginPath();ctx.arc(14+sniff*.5,-4,1.3,0,Math.PI*2);ctx.fill();
  ctx.fillStyle='#c9a19a';ctx.beginPath();ctx.arc(7,-8,2.6,0,Math.PI*2);ctx.fill();
  ctx.fillStyle='#111';ctx.beginPath();ctx.arc(11,-5,.9,0,Math.PI*2);ctx.fill();
  const step=run?Math.sin(t*40+r.x)*2.5:0;
  line(ctx,-5,0,-5+step,3,'#3c322f',1.5);line(ctx,5,0,5-step,3,'#3c322f',1.5);
  ctx.restore();
  if(now<r.squeak)label(ctx,'squeak!',r.x-18,RAT_FLOOR-16-(800-(r.squeak-now))/40,9);
}
function drawCaptor(ctx,client,player,elapsed) {
  const kind=client.capture.kind||client.data.capture_guard,style=client.data.rules.guard_styles[kind]||client.data.rules.guard_styles.patrol;
  person(ctx,client.capture.guard.x,client.capture.guard.y,true,elapsed,kind==='patrol'&&!client.data.has_key?'cell_key':'none',client.capture.guard.x<player.x?'right':'left',true,false,kind,style);
}
function interactionKind(state,position,key,r) {
  if(key==='e' && state.sleeper_alive&&!state.has_blue_key) {
    const wp=watchCrew({...state,rules:r},'sleeper'),xy=positionXY(position,r);
    if(wp&&Math.abs(xy.x-wp.x)<=r.sleeper_range&&Math.abs(xy.y-wp.y)<=25)return 'steal_blue';
  }
  if(key==="f" && state.hidden_barrel) return "barrel";
  if(position.zone==="hammock") return key==="f"?"hammock":"resting";
  const near=(zone,x,reach)=>position.zone===zone && Math.abs(position.value-x)<=reach;
  if(Math.abs(positionXY(position,r).y-365)<=20&&Math.abs(positionXY(position,r).x-r.wardrobe_x)<=r.wardrobe_range) return key==="f"?"wardrobe":"outfit";
  if(near("cabin",r.sleeper_x,r.sleeper_range)) return key==="f"?"hammock":"steal_blue";
  if(near("chest_room",r.chest_x,r.chest_range)) return key==="f"?"unlock_chest":"take_pistol";
  const story=storyPoint(position,r,state);
  if(story?.[1].kind==='cannon') return 'fire_cannon';
  if(story?.[1].kind==='stew') return (state.story?.items||[]).includes('sleeping_pills')&&!state.story?.voyage?.stew_drugged?'drug_stew':'story_inspect';
  if(story) return key==="f"?"story_inspect":"story_take";
  const crate=nearProp(position,r.crates,r.crate_range);
  if(crate) return key==="f"?(state.story?.voyage?.armed?"barrel":"search_crate"):crate[0]==="crate_hold_b"?"take_lamp":"empty_pickup";
  if(key==="f" && nearProp(position,r.barrels,r.barrel_range)) return "barrel";
  return key==="f"?"open":"steal";
}
function wardrobeInSight(client,guard) {
  if(client.data.story?.voyage?.armed||client.data.story?.voyage?.escort)return false;
  const d=client.data,r=d.rules,ahead=(r.wardrobe_x-guard.x)*guard.facing;
  return d.patrol_alive && !d.wardrobe_suspected && d.wardrobe_open && d.wardrobe_contents==="player_clothes"
    && Math.abs(guard.y-365)<=1 && guard.x>=160 && guard.x<=520 && ahead>=-16 && ahead<=r.wardrobe_sight;
}
function investigating(client,guard) {
  if(client.data.story?.voyage?.armed||client.data.story?.voyage?.escort||client.data.story?.voyage?.captain_worn)return false;
  const d=client.data,p=positionXY(client.position,d.rules);
  return d.wardrobe_suspected && d.patrol_alive && d.disguised && !d.hidden_barrel && !d.in_hammock
    && client.position.zone!=="cell" && Math.abs(p.x-guard.x)<=d.rules.inspection_range
    && Math.abs(p.y-guard.y)<=d.rules.vision_height;
}

function canSteal(client, guard) {
  return !client.data.has_key && client.position.zone === "cell"
    && client.position.value >= client.data.rules.cell_key_player_min && client.data.patrol_alive
    && Math.abs(guard.y-500)<=client.data.rules.key_height
    && Math.hypot(guard.x-client.position.value,guard.y-500)<=client.data.rules.key_reach;
}

function line(ctx, x1, y1, x2, y2, color, width = 1) {
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2);
  ctx.strokeStyle = color; ctx.lineWidth = width; ctx.stroke();
}
function roundBox(ctx, x, y, w, h, radius, fill, stroke) {
  ctx.beginPath(); ctx.roundRect(x, y, w, h, radius);
  ctx.fillStyle = fill; ctx.fill();
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 2; ctx.stroke(); }
}
function label(ctx, text, x, y, size = 15) {
  ctx.font = `700 ${size}px Georgia, serif`;
  ctx.fillStyle = "#f8e5bc";
  ctx.shadowColor = "#281b13"; ctx.shadowBlur = 5;
  ctx.fillText(text, x, y); ctx.shadowBlur = 0;
}
function barrel(ctx, x, y, size = 1) {
  ctx.save(); ctx.translate(x, y); ctx.scale(size, size);
  roundBox(ctx, -20, -47, 40, 47, 7, "#a07342", "#3c2a1e");
  line(ctx, -19, -34, 19, -34, "#392820", 5);
  line(ctx, -19, -11, 19, -11, "#392820", 5);
  line(ctx, -14, -44, -14, -3, "#d2aa67", 1);
  line(ctx, 12, -44, 12, -3, "#75502c", 2);
  ctx.restore();
}
function crate(ctx, x, y, w = 56, h = 47) {
  ctx.fillStyle = "#9b7044"; ctx.fillRect(x, y - h, w, h);
  ctx.strokeStyle = "#3e2a20"; ctx.lineWidth = 4; ctx.strokeRect(x, y - h, w, h);
  line(ctx, x + 3, y - h + 3, x + w - 3, y - 3, "#64442c", 4);
  line(ctx, x + w - 3, y - h + 3, x + 3, y - 3, "#c59859", 3);
}
function lamp(ctx, x, y) {
  line(ctx, x, y, x, y + 18, "#4e3426", 2);
  ctx.fillStyle = "#f7d380";
  ctx.shadowColor = "#efcf76"; ctx.shadowBlur = 20;
  roundBox(ctx, x - 7, y + 17, 14, 20, 3, "#edbd63", "#4e3526");
  ctx.shadowBlur = 0;
}
function stair(ctx, x1, y1, x2, y2) {
  line(ctx, x1, y1 - 3, x2, y2 - 3, "#422c22", 33);
  line(ctx, x1, y1 - 3, x2, y2 - 3, "#b48650", 26);
  for (let i = 0; i <= 12; i++) {
    const t = i / 12, x = x1 + (x2 - x1) * t, y = y1 + (y2 - y1) * t;
    line(ctx, x - 12, y + 8, x + 12, y - 8, "#5b3826", 3);
  }
  line(ctx, x1 - 9, y1 - 43, x2 - 9, y2 - 43, "#e0b976", 4);
  for (let i = 0; i <= 4; i++) {
    const t = i / 4, x = x1 + (x2 - x1) * t, y = y1 + (y2 - y1) * t;
    line(ctx, x - 9, y - 43, x - 9, y - 11, "#8c5934", 3);
  }
}

function background(ctx, w, h, cameraX, elapsed) {
  const sky = ctx.createLinearGradient(0, 0, 0, h);
  sky.addColorStop(0, "#aac9c1"); sky.addColorStop(.5, "#74a9ac"); sky.addColorStop(1, "#2f6675");
  ctx.fillStyle = sky; ctx.fillRect(0, 0, w, h);
  ctx.save(); ctx.globalAlpha = .22;
  ctx.fillStyle = "#f4e9cb";
  for (let i = -1; i < 6; i++) {
    const x = i * 320 - ((cameraX * .12) % 320);
    ctx.beginPath(); ctx.ellipse(x + 75, 74 + (i % 2) * 35, 89, 15, 0, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
  ctx.fillStyle = "#2e7486"; ctx.fillRect(0, h - 44, w, 44);
  ctx.strokeStyle = "rgba(208,240,229,.65)"; ctx.lineWidth = 2;
  for (let row = 0; row < 3; row++) {
    ctx.beginPath();
    for (let x = -20; x <= w + 20; x += 8) {
      const y = h - 38 + row * 15 + Math.sin(x * .028 + elapsed * .6 + row) * 3;
      if (x === -20) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
}

function ship(ctx, data) {
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(105, 208); ctx.lineTo(2550, 175); ctx.lineTo(2670, 320);
  ctx.lineTo(2600, 520); ctx.quadraticCurveTo(2570, 558, 2450, 558);
  ctx.lineTo(240, 558); ctx.quadraticCurveTo(150, 550, 115, 475);
  ctx.closePath(); ctx.fillStyle = "#493126"; ctx.fill();
  ctx.strokeStyle = "#251f1c"; ctx.lineWidth = 8; ctx.stroke();
  // Eight walkable spaces on three continuous decks; openings are at the beams.
  const rooms = [
    [150, 390, 240, 110, "#4b4a44"], [390, 390, 510, 110, "#65503b"],
    [900, 390, 465, 110, "#715540"], [150, 253, 370, 112, "#74604f"],
    [520, 253, 380, 112, "#94704e"], [900, 253, 465, 112, "#936d4b"],
    [150, 142, 890, 103, "#ae885f"], [1040, 142, 325, 103, "#b48b5d"],
  ];
  for(const [zone,[name,color]] of Object.entries(data.rules.rooms)) {
    const [left,right,y]=data.rules.floors[zone];
    rooms.push([left,y===500?390:y===365?253:142,right-left, y===245?103: y===365?112:110,color]);
  }
  for (const [x,y,w,h,color] of rooms) { ctx.fillStyle=color; ctx.fillRect(x,y,w,h); }
  for (const y of [245,365,500]) {
    line(ctx, 145, y + 2, 2580, y + 2, "#2c221e", 13);
    line(ctx, 145, y - 2, 2580, y - 2, "#d1a06a", 5);
  }
  for (const [x,top,bottom] of [[150,140,500],[520,253,365],[900,253,500],[1040,140,245],[2580,140,500]]) {
    line(ctx,x,top,x,bottom-65,"#452f25",10);
    line(ctx,x-2,top,x-2,bottom-65,"#c08c55",2);
  }
  for(const [zone] of Object.entries(data.rules.rooms)) {
    const [x,,y]=data.rules.floors[zone];
    // High doorway lintels leave a full-height walking opening below.
    line(ctx,x,y-112,x,y-83,"#4b3428",10);
    line(ctx,x-20,y-83,x+20,y-83,"#b18b5c",6);
  }
  line(ctx, 120, 207, 2620, 196, "#3b2b23", 8);
  for (let x=140;x<2610;x+=38) line(ctx,x,202,x,240,"#664630",3);
  line(ctx, 760, 20, 760, 241, "#5d3c29", 17);
  line(ctx, 760, 20, 760, 241, "#ae8255", 5);
  line(ctx,717,60,803,60,"#563927",13);
  for(let y=215;y>=75;y-=22) line(ctx,747,y,773,y,"#d2ad74",3);
  line(ctx,760,50,445,211,"#665341",2); line(ctx,760,50,1060,211,"#665341",2);
  ctx.fillStyle="rgba(250,230,187,.25)";
  ctx.beginPath();ctx.moveTo(748,61);ctx.lineTo(548,210);ctx.lineTo(746,210);ctx.fill();
  drawGalleyWall(ctx);
  // A complete bed and searchable cargo. Round barrels are hiding places.
  roundBox(ctx,176,456,118,12,2,"#a57b51","#3a2a21");
  roundBox(ctx,183,432,104,25,4,"#6d8180","#38423c");
  roundBox(ctx,188,434,24,14,5,"#ded2b5","#756f60");
  line(ctx,180,467,180,492,"#583b2c",7);line(ctx,288,467,288,492,"#583b2c",7);
  for (const [name,zone,x] of data.rules.crates) {
    const y=data.rules.floors[zone][2];
    crate(ctx,x-28,y,56,44);
    if(name==="crate_hold_b" && data.lamp_revealed) {
      line(ctx,x-27,y-48,x+27,y-48,"#d5b27b",5);
      if(!data.has_lamp) lamp(ctx,x,y-56);
    }
  }
  for(const [,zone,x] of data.rules.barrels) barrel(ctx,x,data.rules.floors[zone][2],1);
  expandedDecor(ctx,data.rules);
  // Stacked hammocks in the cabin.
  for (const y of [268,335]) {
    line(ctx,197,y-9,203,y+9,"#d3ac77",3); line(ctx,392,y-9,386,y+9,"#d3ac77",3);
    ctx.beginPath(); ctx.moveTo(202,y);ctx.quadraticCurveTo(295,y+22,388,y);
    ctx.strokeStyle="#d9d0ae";ctx.lineWidth=8;ctx.stroke();
    line(ctx,202,y-3,388,y-3,"#5d3d2c",2);
  }
  // The wardrobe has a hinged wooden front; the uniform hangs inside.
  roundBox(ctx,426,274,65,88,3,"#4d3227","#2e211e");
  if (!data.wardrobe_open) {
    roundBox(ctx,431,279,54,78,2,"#9b7046","#38291e");
    line(ctx,438,284,438,351,"#c49158",2);
    ctx.fillStyle="#e6c278";ctx.beginPath();ctx.arc(477,319,3,0,Math.PI*2);ctx.fill();
  } else {
    ctx.fillStyle="#231f1d";ctx.fillRect(434,281,48,73);
    line(ctx,436,284,479,284,"#c99b66",3);
    if (data.wardrobe_contents!=="player_clothes") {
      line(ctx,458,286,458,294,"#c8b397",2);
      line(ctx,449,296,467,296,"#c8b397",2);
      ctx.fillStyle="#a6453a";ctx.beginPath();ctx.moveTo(450,297);ctx.lineTo(438,311);
      ctx.lineTo(446,319);ctx.lineTo(446,343);ctx.lineTo(472,343);
      ctx.lineTo(472,319);ctx.lineTo(480,311);ctx.lineTo(468,297);ctx.fill();
      line(ctx,446,326,472,326,"#d3aa69",3);
    } else {
      // The sailor's old clothes remain hanging where the uniform belonged.
      ctx.fillStyle="#32727b";ctx.beginPath();ctx.moveTo(450,297);ctx.lineTo(439,312);
      ctx.lineTo(447,320);ctx.lineTo(447,344);ctx.lineTo(471,344);
      ctx.lineTo(471,320);ctx.lineTo(479,312);ctx.lineTo(468,297);ctx.fill();
      line(ctx,447,326,471,326,"#b5c9be",3);
    }
    label(ctx,"OPEN",435,270,10);
  }
  // Dining tables and galley.
  roundBox(ctx,990,326,155,12,2,"#754f33","#30251f");
  line(ctx,1012,339,1012,361,"#67432d",8);line(ctx,1124,339,1124,361,"#67432d",8);
  roundBox(ctx,1190,320,120,11,2,"#754f33","#30251f");
  line(ctx,1210,332,1210,361,"#67432d",7);line(ctx,1290,332,1290,361,"#67432d",7);
  ctx.fillStyle="#d8be86";for (const x of [1020,1060,1220]) {ctx.beginPath();ctx.ellipse(x,324,18,4,0,0,Math.PI*2);ctx.fill();}
  // A small bench, bowl and cooking pot make the dining guard's routine legible.
  roundBox(ctx,1078,348,56,8,2,"#785337","#35281f");
  ctx.fillStyle="#e1c48a";ctx.beginPath();ctx.ellipse(1100,317,16,5,0,0,Math.PI*2);ctx.fill();
  drawGalley(ctx,data);
  // The chest keeps its body and rim even after the pistol is taken.
  roundBox(ctx,1078,460,85,40,3,"#8b5a35","#34251e");
  line(ctx,1083,482,1158,482,"#c59157",3);
  if (data.chest_open) {
    roundBox(ctx,1077,426,86,12,2,"#9c7045","#34251e");
    line(ctx,1081,440,1081,458,"#c59157",4);
  } else roundBox(ctx,1077,448,86,15,2,"#9c7045","#34251e");
  ctx.fillStyle="#5691ce";ctx.fillRect(1113,467,13,13);
  if (data.chest_open && !data.has_pistol) { ctx.fillStyle="#242423";ctx.fillRect(1102,451,42,6);ctx.fillRect(1130,445,8,10); }
  if (!data.chest_open) label(ctx,"BLUE LOCK",1091,430,10);
  else label(ctx,data.has_pistol?"EMPTY":"OPEN",1097,430,10);
  for(const values of Object.values(data.rules.stairs)) stair(ctx,...values);
  label(ctx,"CELL",165,403,14);label(ctx,"HOLD",650,408,14);
  label(ctx,"CHEST ROOM",1180,408,14);label(ctx,"CABIN",166,271,14);
  label(ctx,"MIDDLE DECK",650,273,14);label(ctx,"MESS HALL",1140,274,14);
  label(ctx,"UPPER DECK",680,164,14);label(ctx,"GALLEY",1252,167,15);
  for(const [zone,[name]] of Object.entries(data.rules.rooms)) {
    const [left,,y]=data.rules.floors[zone];label(ctx,name,left+24,y-91,14);
  }
  ctx.restore();
}

// The galley is a planked deckhouse on the upper deck (x 1040-1370, floor 245).
// The wall is drawn before the barrels so the galley barrel stays in front.
function drawGalleyWall(ctx) {
  ctx.fillStyle="#6b4a32";ctx.fillRect(1046,150,318,94);
  for(let y=163;y<244;y+=13) line(ctx,1046,y,1364,y,"#583c29",2);
  for(const x of [1120,1252,1318]) line(ctx,x,150,x,244,"#5f412c",2);
  line(ctx,1043,150,1367,150,"#3a281e",9);
  for(const x of [1047,1363]) line(ctx,x,150,x,244,"#3a281e",6);
  // A brass porthole lets in a little sky.
  ctx.fillStyle="#2c4a58";ctx.beginPath();ctx.arc(1080,188,13,0,Math.PI*2);ctx.fill();
  ctx.fillStyle="rgba(190,220,230,.25)";ctx.beginPath();ctx.arc(1076,184,6,0,Math.PI*2);ctx.fill();
  ctx.strokeStyle="#c9a35f";ctx.lineWidth=4;ctx.beginPath();ctx.arc(1080,188,13,0,Math.PI*2);ctx.stroke();
}
// The iron range, the crew's stew pot and the cook's tools. Fire, bubbles and
// steam move with time; a drugged stew shows pale specks of crushed pills.
function drawGalley(ctx,data,now=performance.now()) {
  const t=now/1000,drugged=Boolean(data.story?.voyage?.stew_drugged);
  const flicker=.78+.22*Math.sin(t*9.1)*Math.sin(t*5.3+1.2);
  ctx.save();
  // Warm firelight on the wall behind the range.
  const glow=ctx.createRadialGradient(1192,228,6,1192,228,120);
  glow.addColorStop(0,`rgba(255,150,60,${.32*flicker})`);glow.addColorStop(1,"rgba(255,150,60,0)");
  ctx.fillStyle=glow;ctx.fillRect(1072,150,240,94);
  // Pans and a ladle hang from a rail; onions and herbs dry beside them.
  line(ctx,1104,160,1156,160,"#3f2c21",4);
  for(const [x,r] of [[1114,10],[1140,8]]) {
    line(ctx,x,160,x,174-r,"#2f2a26",2);
    ctx.fillStyle="#2b2927";ctx.beginPath();ctx.arc(x,174,r,0,Math.PI*2);ctx.fill();
    line(ctx,x,174-r,x,164,"#2b2927",3);
    ctx.strokeStyle="#55504a";ctx.lineWidth=1.5;ctx.beginPath();ctx.arc(x,174,r-2,Math.PI*.9,Math.PI*1.6);ctx.stroke();
  }
  line(ctx,1153,161,1153,186,"#a58a62",2);ctx.fillStyle="#a58a62";ctx.beginPath();ctx.ellipse(1153,189,4,3,0,0,Math.PI*2);ctx.fill();
  line(ctx,1352,152,1352,192,"#8f7a4c",2);
  for(let i=0;i<4;i++){ctx.fillStyle=i%2?"#c9874a":"#d79b56";ctx.beginPath();ctx.ellipse(1352+(i%2?3:-3),160+i*8,5,5.5,0,0,Math.PI*2);ctx.fill();}
  // A shelf of jars, crocks and plates above the prep table.
  roundBox(ctx,1252,186,64,6,1,"#7d5838","#3a281e");
  for(const [x,h,c] of [[1258,13,"#c9b98e"],[1270,17,"#7f8f73"],[1284,11,"#b56c46"]]) roundBox(ctx,x,186-h,10,h,3,c,"#3c2d22");
  for(const x of [1300,1308]){ctx.fillStyle="#e3d7b6";ctx.beginPath();ctx.ellipse(x,178,4,8,0,0,Math.PI*2);ctx.fill();ctx.strokeStyle="#8a7a5a";ctx.lineWidth=1;ctx.stroke();}
  // Chimney pipe through the deckhouse roof.
  line(ctx,1234,206,1234,150,"#262626",10);line(ctx,1234,206,1234,150,"#3a3a3a",3);
  for(const y of [170,192]) line(ctx,1228,y,1240,y,"#1b1b1b",3);
  // Brick hearth and the cast iron range.
  roundBox(ctx,1154,236,92,9,2,"#8b4a35","#4a2a20");
  for(const x of [1170,1192,1214,1236]) line(ctx,x,237,x,244,"#5e3326",1.5);
  roundBox(ctx,1160,204,80,34,4,"#2d2e2d","#141414");
  roundBox(ctx,1156,201,88,7,2,"#454746","#181818");
  // Firebox: glowing coals behind an iron grate.
  ctx.fillStyle=`rgb(255,${110+70*flicker|0},40)`;ctx.shadowColor="#ff8a3a";ctx.shadowBlur=14*flicker;
  roundBox(ctx,1172,213,32,19,3,ctx.fillStyle,"#151515");ctx.shadowBlur=0;
  for(let i=0;i<4;i++){const fx=1177+i*8,fh=5+4*Math.abs(Math.sin(t*7+i*1.7));ctx.fillStyle="rgba(255,226,120,.9)";ctx.beginPath();ctx.moveTo(fx-3,231);ctx.quadraticCurveTo(fx,231-fh*2,fx+3,231);ctx.fill();}
  for(const x of [1180,1188,1196]) line(ctx,x,213,x,232,"#1b1b1b",2);
  // Oven door with a brass latch, and rivets along the range.
  roundBox(ctx,1211,212,22,20,2,"#383938","#151515");
  line(ctx,1215,222,1229,222,"#c8a25a",3);
  ctx.fillStyle="#6a6b69";for(const x of [1164,1236])for(const y of [208,234]){ctx.beginPath();ctx.arc(x,y,1.6,0,Math.PI*2);ctx.fill();}
  // The big stew pot on the range: iron body, handles, rim and stew surface.
  ctx.fillStyle="#222";ctx.beginPath();ctx.moveTo(1170,181);ctx.lineTo(1230,181);
  ctx.quadraticCurveTo(1233,202,1214,202);ctx.lineTo(1186,202);ctx.quadraticCurveTo(1167,202,1170,181);ctx.fill();
  ctx.strokeStyle="#4b4b4b";ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(1175,185);ctx.quadraticCurveTo(1174,197,1186,199);ctx.stroke();
  for(const s of [-1,1]){ctx.strokeStyle="#3c3c3c";ctx.lineWidth=3;ctx.beginPath();ctx.arc(1200+s*33,186,5,s>0?-Math.PI/2:Math.PI/2,s>0?Math.PI/2:Math.PI*1.5);ctx.stroke();}
  ctx.fillStyle=drugged?"#a07a52":"#8a552b";ctx.beginPath();ctx.ellipse(1200,181,29,5,0,0,Math.PI*2);ctx.fill();
  ctx.fillStyle="rgba(240,170,90,.35)";ctx.beginPath();ctx.ellipse(1194,180,12,2,0,0,Math.PI*2);ctx.fill();
  if(drugged) for(let i=0;i<7;i++){const a=t*.8+i*.9;ctx.fillStyle="rgba(238,232,255,.85)";ctx.beginPath();ctx.arc(1200+Math.cos(a)*(8+i*2.4),181+Math.sin(a)*1.8,1.2,0,Math.PI*2);ctx.fill();}
  for(let i=0;i<5;i++){const p=(t*1.2+i*.37)%1,bx=1184+i*8+Math.sin(i*2.1)*3;
    ctx.strokeStyle=`rgba(${drugged?'225,210,190':'200,140,80'},${.9*(1-p)})`;ctx.lineWidth=1.2;ctx.beginPath();ctx.arc(bx,180-p*1.5,1+2.2*p,0,Math.PI*2);ctx.stroke();}
  ctx.strokeStyle="#5a5a5a";ctx.lineWidth=3;ctx.beginPath();ctx.ellipse(1200,181,30,5.5,0,0,Math.PI*2);ctx.stroke();
  // A wooden ladle rests in the stew.
  line(ctx,1210,181,1236,160,"#9a774e",3);ctx.fillStyle="#9a774e";ctx.beginPath();ctx.arc(1237,159,2.5,0,Math.PI*2);ctx.fill();
  // Steam curls up and fades under the roof.
  for(let i=0;i<3;i++){const p=(t*.35+i/3)%1,sx=1188+i*11+Math.sin(t*1.6+i*2)*5*p;
    ctx.fillStyle=`rgba(235,230,220,${.32*(1-p)*Math.min(1,p*4)})`;
    ctx.beginPath();ctx.arc(sx,176-p*24,4+7*p,0,Math.PI*2);ctx.fill();}
  // Firewood by the range.
  for(const [x,y] of [[1136,239],[1146,239],[1141,231]]){ctx.fillStyle="#7a4f30";ctx.beginPath();ctx.ellipse(x,y,6,4.5,0,0,Math.PI*2);ctx.fill();ctx.fillStyle="#c49766";ctx.beginPath();ctx.ellipse(x,y,3,2.2,0,0,Math.PI*2);ctx.fill();}
  // Prep table: cutting board, a fish, a knife and bread.
  roundBox(ctx,1252,212,58,7,2,"#7b5435","#35291f");
  line(ctx,1258,219,1258,243,"#5a3d2a",5);line(ctx,1304,219,1304,243,"#5a3d2a",5);
  line(ctx,1258,232,1304,232,"#5a3d2a",3);
  roundBox(ctx,1257,207,30,5,1,"#c9a46b","#6d5233");
  ctx.fillStyle="#9fb1b5";ctx.beginPath();ctx.ellipse(1270,204,10,3.5,0,0,Math.PI*2);ctx.fill();
  ctx.beginPath();ctx.moveTo(1259,204);ctx.lineTo(1253,200);ctx.lineTo(1253,208);ctx.fill();
  ctx.fillStyle="#222";ctx.beginPath();ctx.arc(1276,203,.9,0,Math.PI*2);ctx.fill();
  line(ctx,1283,209,1296,207,"#cfd3d3",2);line(ctx,1296,207,1301,206,"#4a3324",3);
  ctx.fillStyle="#c08446";ctx.beginPath();ctx.ellipse(1300,207,8,4.5,0,Math.PI,0);ctx.fill();
  // Sacks of flour and potatoes by the door.
  for(const [x,c] of [[1066,"#d6c49a"],[1088,"#b59a6a"]]){ctx.fillStyle=c;ctx.beginPath();ctx.moveTo(x-11,243);ctx.quadraticCurveTo(x-13,222,x-5,216);ctx.lineTo(x+5,216);ctx.quadraticCurveTo(x+13,222,x+11,243);ctx.closePath();ctx.fill();line(ctx,x-5,219,x+5,219,"#6e5a3a",2);}
  ctx.restore();
}
function expandedDecor(ctx,rules) {
  // Original, simple furnishings identify rooms without adding invisible walls.
  for(const x of [1510,1570,1630]) {
    roundBox(ctx,x,409,42,20,9,"#d9c8a2","#6d604b");
    line(ctx,x+20,410,x+20,428,"#a38d64",3);
  }
  for(const x of [1880,1990,2090]) {
    line(ctx,x,422,x+44,422,"#4a3329",5);
    line(ctx,x+5,397,x+28,438,"#ccd0bd",5);
    line(ctx,x+26,413,x+40,405,"#cfae68",4);
  }
  for(const x of [2250,2310,2370,2430]) {
    roundBox(ctx,x,399,31,25,7,"#c2a46f","#574834");
    line(ctx,x+3,409,x+28,409,"#66573e",3);
  }
  for(const x of [1510,1620]) {
    roundBox(ctx,x,326,87,18,3,"#d9dac4","#636e60");
    roundBox(ctx,x+5,329,21,10,4,"#f0e5c9","#959c80");
    line(ctx,x+3,344,x+3,360,"#5b4936",5);line(ctx,x+82,344,x+82,360,"#5b4936",5);
  }
  ctx.fillStyle="#d6ded0";ctx.fillRect(1457,281,37,28);
  line(ctx,1475,284,1475,305,"#a54c40",7);line(ctx,1465,295,1485,295,"#a54c40",7);
  roundBox(ctx,1870,321,130,12,3,"#674c37","#352922");
  for(const x of [1885,1970]) {line(ctx,x,333,x,359,"#674c37",6);roundBox(ctx,x-10,346,33,7,2,"#916842","#453126");}
  for(const x of [2250,2330]) {
    roundBox(ctx,x,276,48,42,3,"#4c5146","#b99860");
    ctx.fillStyle="#d4b875";ctx.beginPath();ctx.arc(x+24,296,11,0,Math.PI*2);ctx.fill();
  }
  // Coiled rope and a spare spar on the exposed aft deck.
  for(const x of [1770,1820]) {ctx.strokeStyle="#d0b17a";ctx.lineWidth=4;ctx.beginPath();ctx.ellipse(x,226,22,10,0,0,Math.PI*2);ctx.stroke();}
  line(ctx,1750,213,1870,213,"#6a492e",9);
  roundBox(ctx,2100,188,123,19,3,"#73563c","#332820");
  ctx.fillStyle="#e5d5ac";ctx.fillRect(2113,177,95,14);
  line(ctx,2130,180,2180,187,"#4f8180",2);line(ctx,2140,188,2198,180,"#ad7046",2);
  line(ctx,2110,208,2110,240,"#62432d",6);line(ctx,2211,208,2211,240,"#62432d",6);
  roundBox(ctx,2395,212,90,16,4,"#984f46","#4d332b");
  roundBox(ctx,2395,185,14,56,3,"#654533","#d1af69");
  line(ctx,2480,228,2480,241,"#63452c",6);
  ctx.strokeStyle="#d2b273";ctx.lineWidth=3;ctx.beginPath();ctx.arc(1980,187,20,0,Math.PI*2);ctx.stroke();
  for(let i=0;i<8;i++){const a=i*Math.PI/4;line(ctx,1980,187,1980+Math.cos(a)*26,187+Math.sin(a)*26,"#d2b273",3);}
}

function speechBubble(ctx,x,y,text) {
  ctx.save();ctx.font='600 11px system-ui';const width=ctx.measureText(text).width+20;
  roundBox(ctx,x-width/2,y-22,width,25,7,'#fff1d2','#785c3b');
  ctx.fillStyle='#fff1d2';ctx.beginPath();ctx.moveTo(x-4,y+2);ctx.lineTo(x,y+9);ctx.lineTo(x+6,y+2);ctx.fill();
  ctx.fillStyle='#382d25';ctx.textAlign='center';ctx.fillText(text,x,y-5);ctx.restore();
}
function crouchingPerson(ctx,x,y,guard,elapsed,held,facing,moving,disguised,variant="patrol",style=null) {
  const pace=moving?Math.sin(elapsed*9)*2:0,coat=style?.color||(disguised?'#9c3d33':'#2d6b73');
  ctx.save();ctx.translate(x,y);ctx.scale(facing==='left'?-1:1,1);
  ctx.fillStyle='rgba(15,18,20,.27)';ctx.beginPath();ctx.ellipse(0,2,18,4,0,0,Math.PI*2);ctx.fill();
  line(ctx,-8,-23,-14+pace,-12,'#302b28',7);line(ctx,-14+pace,-12,-8+pace,-2,'#302b28',7);
  line(ctx,2,-23,12-pace,-13,'#302b28',7);line(ctx,12-pace,-13,10-pace,-2,'#302b28',7);
  line(ctx,-8+pace,-2,-15+pace,0,'#241f1e',5);line(ctx,10-pace,-2,18-pace,0,'#241f1e',5);
  ctx.save();ctx.translate(-3,-32);ctx.rotate(.58);roundBox(ctx,-11,-16,22,31,5,coat,'#2c2927');ctx.restore();
  line(ctx,5,-36,17,-23,coat,6);line(ctx,17,-23,23,-24,'#d0a173',5);
  ctx.fillStyle='#d0a173';ctx.beginPath();ctx.arc(13,-41,9,0,Math.PI*2);ctx.fill();
  ctx.fillStyle=disguised?'#332c29':'#263940';ctx.beginPath();ctx.moveTo(-1,-49);ctx.lineTo(5,-56);ctx.lineTo(14,-53);ctx.lineTo(23,-55);ctx.lineTo(29,-47);ctx.closePath();ctx.fill();
  line(ctx,-2,-49,29,-47,disguised?'#dbb36e':'#b5c9be',3);
  ctx.fillStyle='#272622';ctx.beginPath();ctx.arc(18,-42,1.5,0,Math.PI*2);ctx.fill();
  line(ctx,-10,-26,7,-18,'#3d2c22',4);if(style?.badge)label(ctx,style.badge,-3,-28,10);
  if(held==='pistol'){roundBox(ctx,21,-27,23,6,1,'#242c2c','#d7c19b');line(ctx,25,-23,25,-16,'#3b2b24',4);}
  else if(held==='lamp')lamp(ctx,27,-18);
  else if(held?.includes('key')){const c=held==='blue_key'?'#6cb6ff':'#ffe296';ctx.strokeStyle=c;ctx.lineWidth=3;ctx.beginPath();ctx.arc(27,-22,4,0,Math.PI*2);ctx.stroke();line(ctx,29,-18,33,-10,c,3);}
  ctx.restore();
}
function person(ctx, x, feetY, guard, elapsed, held = "none", facing = "right", moving = true, disguised = false, variant="patrol", style=null, shadow=true) {
  const pace = moving ? Math.sin(elapsed * (guard ? 10 : 11)) * 3 : 0;
  const uniform = guard || disguised;
  ctx.save(); ctx.translate(x, feetY);
  if (shadow) {
    ctx.fillStyle = "rgba(15,18,20,.27)";
    ctx.beginPath(); ctx.ellipse(0, 3, 15, 4, 0, 0, Math.PI * 2); ctx.fill();
  }
  line(ctx, -6, -17, -7 + pace, -2, "#2d2927", 6);
  line(ctx, 6, -17, 7 - pace, -2, "#2d2927", 6);
  line(ctx, -7 + pace, -2, -11 + pace, 0, "#241f1e", 6);
  line(ctx, 7 - pace, -2, 11 - pace, 0, "#241f1e", 6);
  const coat=style?.color||(guard||disguised?'#9c3d33':'#2d6b73');
  roundBox(ctx, -12, -47, 24, 32, 5, coat, "#2c2927");
  line(ctx, -10, -39, -17 - pace * .5, -21, coat, 6);
  line(ctx, 10, -39, 17 + pace * .5, -22, coat, 6);
  ctx.fillStyle = "#d0a173";
  ctx.beginPath(); ctx.arc(0, -56, 10, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = uniform ? "#332c29" : "#263940";
  ctx.beginPath(); ctx.moveTo(-16, -65); ctx.lineTo(-10, -73); ctx.lineTo(0, -69);
  ctx.lineTo(11, -73); ctx.lineTo(17, -65); ctx.closePath(); ctx.fill();
  line(ctx, -18, -65, 18, -65, uniform ? "#dbb36e" : "#b5c9be", 3);
  ctx.fillStyle = "#272622"; ctx.beginPath(); ctx.arc(facing === "left" ? -4 : 4, -57, 1.5, 0, Math.PI * 2); ctx.fill();
  line(ctx, -10, -30, 12, -30, "#3d2c22", 5);
  if(style?.badge) label(ctx,style.badge,-6,-35,10);
  if (guard && held === "cell_key") {
    ctx.shadowColor = "#ffe296"; ctx.shadowBlur = 13;
    ctx.strokeStyle = "#ffe296"; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(17, -30, 6, 0, Math.PI * 2); ctx.stroke();
    line(ctx, 20, -25, 20, -15, "#ffe296", 3);
    line(ctx, 20, -17, 25, -17, "#ffe296", 2);
    ctx.shadowBlur = 0;
  }
  if(guard && held==="bowl") {roundBox(ctx,11,-27,19,9,5,"#e8d1a2","#5b3d29");}
  if(guard && held==='pistol') {
    const side=facing==='left'?-1:1;
    line(ctx,side*10,-40,side*19,-60,coat,6);
    line(ctx,side*19,-60,side*25,-62,'#d0a173',5);
    roundBox(ctx,side>0?20:-44,-67,24,6,1,'#242c2c','#e8c893');
    line(ctx,side*24,-62,side*24,-55,'#3b2b24',4);
  }
  if (!guard && held !== "none") {
    const side=facing === "left" ? -1 : 1;
    if (held === "lamp") {
      lamp(ctx,side*23,-30);
    } else if (held === "pistol") {
      roundBox(ctx,side>0?16:-37,-23,23,7,1,"#242c2c","#f0cf8b");
      line(ctx,side*22,-18,side*22,-8,"#3b2b24",5);
    } else {
      const color=held === "blue_key" ? "#6cb6ff" : "#ffe296";
      ctx.shadowColor=color;ctx.shadowBlur=12;ctx.strokeStyle=color;ctx.lineWidth=3;
      ctx.beginPath();ctx.arc(side*22,-19,5,0,Math.PI*2);ctx.stroke();
      line(ctx,side*24,-15,side*27,-6,color,3);line(ctx,side*27,-8,side*32,-9,color,2);
      ctx.shadowBlur=0;
    }
  }
  ctx.restore();
}

function lyingPerson(ctx, x, y, color, keyVisible = false) {
  ctx.save();ctx.translate(x,y);
  // Bent torso and knees rest along the sagging cloth rather than its rope.
  ctx.beginPath();ctx.moveTo(-35,-5);ctx.quadraticCurveTo(-3,8,22,1);
  ctx.strokeStyle="#392b29";ctx.lineWidth=17;ctx.lineCap="round";ctx.stroke();
  ctx.strokeStyle=color;ctx.lineWidth=13;ctx.stroke();
  ctx.fillStyle="#d0a173";ctx.beginPath();ctx.arc(-43,-7,9,0,Math.PI*2);ctx.fill();
  line(ctx,-49,-17,-34,-15,"#272c31",5);
  ctx.beginPath();ctx.moveTo(22,1);ctx.quadraticCurveTo(35,-8,47,-6);
  ctx.strokeStyle="#302b28";ctx.lineWidth=7;ctx.stroke();
  if (keyVisible) {
    ctx.strokeStyle="#6cb6ff";ctx.lineWidth=3;ctx.beginPath();ctx.arc(17,0,5,0,Math.PI*2);ctx.stroke();
    line(ctx,21,3,25,10,"#6cb6ff",2);
  }
  ctx.restore();
}

function fallen(ctx,x,feetY,color="#9c3d33") {
  ctx.save();ctx.translate(x,feetY);
  roundBox(ctx,-28,-13,55,14,6,color,"#3a2824");
  ctx.fillStyle="#d0a173";ctx.beginPath();ctx.arc(-34,-6,9,0,Math.PI*2);ctx.fill();
  line(ctx,23,-3,40,-1,"#2d2927",6);ctx.restore();
}

function cellBars(ctx, open) {
  ctx.save();
  ctx.fillStyle = "rgba(12,19,20,.14)"; ctx.fillRect(150, 389, 240, 112);
  for (let x = 151; x < 387; x += 25) {
    line(ctx, x, 387, x, 501, "#1e2b2b", 7);
    line(ctx, x - 1, 387, x - 1, 501, "#8d9c8e", 2);
  }
  line(ctx, 150, 407, 389, 407, "#25302d", 7);
  line(ctx, 150, 470, 389, 470, "#25302d", 7);
  line(ctx, 389, 385, 389, 501, "#1b2929", 8);
  if (open) {
    ctx.fillStyle="rgba(11,27,28,.32)";ctx.fillRect(390,411,21,87);
    // The upright leaf rests against the fixed cell bars, away from the
    // walkable doorway at x=390..410.
    ctx.strokeStyle="#2a3935";ctx.lineWidth=6;ctx.strokeRect(360,409,25,89);
    for (let x=364;x<=380;x+=8) line(ctx,x,411,x,496,"#9daaa0",4);
    line(ctx,360,438,385,438,"#293734",5);line(ctx,360,478,385,478,"#293734",5);
    ctx.fillStyle="#e6c277";ctx.font="700 12px system-ui";ctx.fillText("OPEN",360,402);
  } else {
    ctx.fillStyle = "rgba(16,31,31,.75)"; ctx.fillRect(390, 410, 20, 89);
    for (let x = 393; x <= 407; x += 7) line(ctx, x, 411, x, 498, "#a0a89b", 4);
    line(ctx, 388, 435, 411, 435, "#25302d", 6);
    line(ctx, 388, 481, 411, 481, "#25302d", 6);
    ctx.fillStyle = "#efc56e"; ctx.beginPath(); ctx.arc(400, 456, 6, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#4a3525"; ctx.fillRect(398, 455, 4, 8);
    ctx.fillStyle = "#e6c277"; ctx.font = "700 12px system-ui"; ctx.fillText("LOCKED", 404, 402);
  }
  ctx.restore();
}

function pathLength(path) {
  let total=0;for(let i=1;i<path.length;i++) total+=Math.hypot(path[i][0]-path[i-1][0],path[i][1]-path[i-1][1]);
  return total;
}
function pointOnPath(path,distance) {
  let left=Math.max(0,distance);
  for(let i=1;i<path.length;i++){
    const a=path[i-1],b=path[i],length=Math.hypot(b[0]-a[0],b[1]-a[1]);
    if(left<=length || i===path.length-1){const f=length?clamp(left/length,0,1):1;return {x:a[0]+(b[0]-a[0])*f,y:a[1]+(b[1]-a[1])*f};}
    left-=length;
  }
  return {x:path[0][0],y:path[0][1]};
}
function advanceCapture(client,dt,action){
  if(client.data.capture_phase!=="active") {client.capture=null;return;}
  if(!client.capture){
    const [approach,escort]=client.data.capture_paths;
    client.capture={approach,escort,phase:"approach",distance:0,guard:pointOnPath(approach,0),
      player:pointOnPath(escort,0),kind:client.data.capture_guard,sent:false,startedAt:performance.now()};
  }
  const c=client.capture;
  const elapsed=Math.max(0,(performance.now()-c.startedAt)/1000),approachSeconds=pathLength(c.approach)/230;
  if(elapsed<approachSeconds){
    c.distance=Math.min(pathLength(c.approach),elapsed*230);
    c.guard=pointOnPath(c.approach,c.distance);
    if(c.distance>=pathLength(c.approach)){c.phase="escort";c.distance=0;}
  } else {
    c.phase='escort';
    c.distance=Math.min(pathLength(c.escort),Math.max(0,elapsed-approachSeconds)*175);
    c.player=pointOnPath(c.escort,c.distance);
    c.guard=pointOnPath(c.escort,c.distance+Math.min(24,c.distance));
    if(c.distance>=pathLength(c.escort) && !c.sent){c.sent=true;action("capture_complete");}
  }
}

function cameraFor(player,w,h,zone) {
  if(zone==="cell") {
    // Keep the letter, bars and lower half of the stair in one stable close-up.
    // Taking the key does not move the camera; crossing the cell boundary does.
    const zoom=Math.min(2.8,w/350);
    return {zoom,x:495-w/zoom,y:500-h*.78/zoom};
  }
  const zoom=["upper_deck","aft_deck","mast","mast_top"].includes(zone)?1.10:1.22;
  return {zoom,x:player.x-w/(2*zoom),y:player.y-h*.64/zoom};
}

// Multiplayer: two browsers share live positions through Ably. The Streamlit
// server is not polled; it only signs a short-lived token for the room's
// channel. Connections outlive Streamlit reruns, keyed by component key.
const rooms = globalThis.__teamPlotTwistRooms ??= new Map();
const PARTNER_SEND_MS=125,PARTNER_HEARTBEAT_MS=5000,PARTNER_TOKEN_FRESH_MS=30000;
function loadAbly(url) {
  if(globalThis.AblyPubSub) return Promise.resolve(globalThis.AblyPubSub);
  return globalThis.__teamPlotTwistAbly ??= new Promise((resolve,reject)=>{
    const script=document.createElement('script');script.src=url;script.async=true;
    script.onload=()=>resolve(globalThis.AblyPubSub);script.onerror=()=>{globalThis.__teamPlotTwistAbly=null;reject(new Error('Ably SDK did not load'));};
    document.head.appendChild(script);
  });
}
function closeMultiplayer(key) {
  const mp=rooms.get(key);if(!mp)return;
  rooms.delete(key);mp.closed=true;
  try{Promise.resolve(mp.channel?.presence.leave()).catch(()=>{});}catch(_){}
  try{mp.realtime?.close();}catch(_){}
}
function refreshPartners(mp) {
  if(!mp.channel)return;
  mp.channel.presence.get().then(members=>{
    if(mp.closed)return;
    const ordered=[...members].sort((a,b)=>a.timestamp-b.timestamp);
    const mine=ordered.findIndex(m=>m.clientId===mp.clientId);
    mp.full=mine>=MAX_ROOM_PLAYERS;
    // Names follow the order players entered the room, so a reload or a
    // second Join never gives two players the same name.
    const otherIndex=ordered.findIndex(m=>m.clientId!==mp.clientId);
    mp.partnerName=otherIndex<0?null:`Player ${otherIndex+1}`;
    if(!other)mp.partner=null;
  }).catch(()=>{});
}
const MAX_ROOM_PLAYERS=2;
function syncMultiplayer(client,data,key,setTriggerValue) {
  const m=data.multiplayer;
  if(!m){closeMultiplayer(key);return;}
  let mp=rooms.get(key);
  if(mp&&mp.room!==m.room){closeMultiplayer(key);mp=null;}
  if(mp){
    mp.client=client;mp.setTrigger=setTriggerValue;mp.token={request:m.token_request,at:performance.now()};
    if(mp.pendingAuth){const done=mp.pendingAuth;mp.pendingAuth=null;done(m.token_request);}
    noteShipVersion(mp,Number(m.world_version)||0);
    return;
  }
  mp={key,room:m.room,clientId:m.client_id,client,setTrigger:setTriggerValue,shipVersion:Number(m.world_version)||0,syncWanted:0,status:'connecting',partner:null,partnerName:null,
      token:{request:m.token_request,at:performance.now()},pendingAuth:null,lastSent:'',lastSentAt:0,forceSend:true};
  rooms.set(key,mp);
  loadAbly(m.sdk_url).then(AblyPubSub=>{
    if(mp.closed)return;
    mp.realtime=AblyPubSub.createClient({clientId:m.client_id,echoMessages:false,authCallback:(params,callback)=>{
      // A token request is single-use and must be fresh; ask the server for a
      // new one (one Streamlit run) only when the last one is used or old.
      const t=mp.token;
      if(t.request!==mp.usedRequest&&performance.now()-t.at<PARTNER_TOKEN_FRESH_MS){mp.usedRequest=t.request;callback(null,t.request);return;}
      mp.pendingAuth=request=>{mp.usedRequest=request;callback(null,request);};
      setTriggerValue('ably',{room:m.room,at:Date.now()});
    }});
    mp.realtime.connection.on(change=>{mp.status=change.current;if(change.current==='connected'){mp.forceSend=true;publishPosition(mp.client,mp.key,performance.now());}});
    mp.channel=mp.realtime.channels.get(m.channel);
    // The partner changed the shared ship: fetch it with one Streamlit run.
    mp.channel.subscribe('ship',message=>{
      const v=Number(message.data?.v)||0;
      if(mp.closed||message.clientId===mp.clientId||v<=mp.shipVersion||v<=mp.syncWanted)return;
      mp.syncWanted=v;mp.setTrigger('sync',{v,at:Date.now()});
    });
    mp.channel.subscribe('pos',message=>{
      if(mp.closed||message.clientId===mp.clientId)return;
      const p=message.data||{};
      if(typeof p.x!=='number'||typeof p.y!=='number')return;
      const before=mp.partner;
      mp.partner={...p,receivedAt:performance.now(),shownX:before?.shownX??p.x,shownY:before?.shownY??p.y,
        movedAt:before&&(before.x!==p.x||before.y!==p.y)?performance.now():before?.movedAt??0};
    });
    // A newcomer must see us at once, even if our tab is in the background
    // and its animation frames (and so the regular sends) are paused.
    mp.channel.presence.subscribe(member=>{
      if(member.clientId!==mp.clientId){mp.forceSend=true;publishPosition(mp.client,mp.key,performance.now());}
      refreshPartners(mp);
    });
    mp.channel.presence.enter({}).then(()=>refreshPartners(mp)).catch(()=>{mp.status='failed';});
  }).catch(error=>{mp.status='failed';console.error('Team Plot Twist multiplayer could not start',error);});
}
// A newer ship version in our own data means our action changed the shared
// ship: tell the partner. Versions only grow, so the partner never echoes back.
function noteShipVersion(mp,version) {
  if(version>=mp.syncWanted)mp.syncWanted=0;
  if(version<=mp.shipVersion)return;
  mp.shipVersion=version;
  if(mp.channel&&mp.status==='connected')mp.channel.publish('ship',{v:version}).catch(()=>{});
}
function partnerSnapshot(client) {
  const d=client.data,xy=positionXY(client.position,d.rules),vv=d.story?.voyage||{};
  return {x:Math.round(xy.x),y:Math.round(xy.y),f:client.facing==='left'?-1:1,
    h:Boolean(d.hidden_barrel||d.in_hammock||client.position.zone==='hammock'||vv.escort?.hidden),
    c:Boolean(vv.duck||vv.escort),g:Boolean(d.disguised),cap:Boolean(vv.captain_worn),e:Boolean(d.ending)};
}
// Send only when something changed (at most 8 a second) plus a slow heartbeat,
// so standing still or reading a letter costs almost no Ably messages.
function publishPosition(client,key,now) {
  const mp=rooms.get(key);
  if(!mp?.channel||mp.status!=='connected'||mp.full)return;
  const snap=JSON.stringify(partnerSnapshot(client));
  const changed=snap!==mp.lastSent;
  if(!(mp.forceSend||changed&&now-mp.lastSentAt>=PARTNER_SEND_MS||now-mp.lastSentAt>=PARTNER_HEARTBEAT_MS))return;
  mp.forceSend=false;mp.lastSent=snap;mp.lastSentAt=now;
  mp.channel.publish('pos',JSON.parse(snap)).catch(()=>{});
}
function drawPartner(ctx,client) {
  const mp=rooms.get(client.key),p=mp?.partner;
  if(!p||!mp.partnerName||p.h||p.e)return;
  const now=performance.now(),dt=Math.min(.1,(now-(p.drawnAt??now))/1000);p.drawnAt=now;
  // Ease toward the latest position so 8 updates a second look smooth.
  const far=Math.hypot(p.x-p.shownX,p.y-p.shownY)>220,k=far?1:Math.min(1,dt*14);
  p.shownX+=(p.x-p.shownX)*k;p.shownY+=(p.y-p.shownY)*k;
  const moving=performance.now()-p.movedAt<300,style=p.cap?client.data.rules.guard_styles.officer:{color:p.g?'#9c3d33':'#7a4f9a'};
  const args=[ctx,p.shownX,p.shownY,false,performance.now()/1000,'none',p.f<0?'left':'right',moving,p.g,'patrol',style];
  if(p.c)crouchingPerson(...args);else person(...args);
}
// The name tag is drawn after the cell bars so it is never hidden behind them.
function drawPartnerName(ctx,client) {
  const mp=rooms.get(client.key),p=mp?.partner;
  if(!p||!mp.partnerName||p.h||p.e||p.shownX===undefined)return;
  const text=String(mp.partnerName),y=p.shownY-(p.c?72:90);
  ctx.save();ctx.font='bold 11px Georgia, serif';
  const width=ctx.measureText(text).width+12;
  roundBox(ctx,p.shownX-width/2,y-12,width,16,6,'rgba(122,79,154,.85)','rgba(240,225,255,.7)');
  ctx.fillStyle='#fbf3ff';ctx.fillText(text,p.shownX-width/2+6,y);ctx.restore();
}
function drawRoomBadge(ctx,w,client) {
  const mp=rooms.get(client.key);if(!mp)return;
  const status=mp.full?'ROOM FULL':mp.status==='failed'?'OFFLINE':mp.status!=='connected'?'CONNECTING…':mp.partnerName?`${mp.partnerName.toUpperCase()} IS HERE`:'WAITING FOR PLAYER 2';
  const text=`ROOM ${mp.room} · ${status}`;
  ctx.save();ctx.font='bold 12px Georgia, serif';
  const width=ctx.measureText(text).width+20;
  roundBox(ctx,w-width-12,12,width,24,8,'rgba(20,24,28,.72)','rgba(230,205,150,.6)');
  ctx.fillStyle=mp.full||mp.status==='failed'?'#f0a08a':'#f1dfb4';ctx.fillText(text,w-width-2,28);ctx.restore();
}

function draw(client, canvas, stage, guards) {
  const dpr = window.devicePixelRatio || 1;
  const w = Math.max(320, stage.clientWidth), h = stage.clientHeight;
  if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
    canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
  }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  if(client.data.ending) { drawEnding(ctx,w,h,client); return; }
  if(client.scope) { drawScope(ctx,w,h,client.scope.pan,performance.now()); return; }
  const player = client.capture?.player || positionXY(client.position, client.data.rules);
  const camera=cameraFor(player,w,h,client.position.zone);
  const cameraX=camera.x;
  const elapsed = guardElapsed(client.data);
  background(ctx, w, h, cameraX, elapsed);
  ctx.save(); ctx.scale(camera.zoom,camera.zoom); ctx.translate(-camera.x,-camera.y);
  const fired=client.data.story?.voyage?.cannon_fired;
  if(fired!==undefined){const shake=cannonMotion(gameNow(client.data)-fired).shake;if(shake)ctx.translate((Math.random()-.5)*shake*2,(Math.random()-.5)*shake*2);}
  ship(ctx, client.data);
  storyDecor(ctx,client.data);
  for(const rat of client.rats||[])drawRat(ctx,rat,performance.now());
  // The hat belongs to the scenery layer; a passing guard walks in front.
  const anim=client.ambushAnim;
  if(anim&&(!client.data.hidden_barrel||client.capture||performance.now()-anim.start>=AMBUSH_MS))client.ambushAnim=null;
  if(client.ambushAnim)drawAmbush(ctx,client,client.ambushAnim,performance.now());
  else if(client.data.hidden_barrel && !client.capture) {
    ctx.fillStyle=client.data.disguised?"#302b29":"#273a40";
    ctx.beginPath();ctx.moveTo(player.x-17,player.y-47);ctx.lineTo(player.x-9,player.y-59);
    ctx.lineTo(player.x+8,player.y-59);ctx.lineTo(player.x+17,player.y-47);ctx.fill();
    line(ctx,player.x-20,player.y-47,player.x+20,player.y-47,"#c6b180",4);
  }
  if (!client.capture) for(const [kind,guard] of Object.entries(guards)) {
    if(!client.data[`${kind}_alive`]) continue;
    if(guard.name==='sleep')continue;

    const dir=guard.facing;
    ctx.fillStyle=gameNow(client.data)<client.data.alert_until_ms?"rgba(241,81,60,.15)":"rgba(255,218,120,.12)";
    const sight=client.data.rules.guard_styles[kind].vision*(client.data.story?.voyage?.armed?1.3:1)*(client.data.has_lamp&&client.data.lamp_lit&&client.data.held_item==="lamp"?client.data.rules.lamp_vision_multiplier:1);
    const height=client.data.rules.vision_height;
    if(guard.name!=='feast_sleep')ctx.fillRect(guard.x+(dir<0?-sight:12),guard.y-55-height,sight-12,height*2);
    const eating=kind==="dining"&&guard.name==="eating";
    if(guard.name.startsWith('feast_')) {
      drawFeastCrew(ctx,kind,guard,client.data,elapsed);
      if(guard.name==='feast_serve'&&gameNow(client.data)-client.data.story.voyage.feast.gather<4000)speechBubble(ctx,guard.x,guard.y-110,"Stew's ready! Come and eat!");
    }
    else if(eating) { ctx.save();ctx.translate(guard.x,guard.y);ctx.scale(1,.72);
      person(ctx,0,0,true,elapsed,"bowl",dir<0?"left":"right",false,false,kind,client.data.rules.guard_styles[kind]);ctx.restore(); }
    else person(ctx,guard.x,guard.y,true,elapsed,
      client.data.story?.voyage?.armed?"pistol":kind==="patrol"&&!client.data.has_key?"cell_key":kind==="dining"&&["dining_to_stair","dining_upper_up","bowl_to_pot","pot_to_stair","dining_upper_down","stair_to_table"].includes(guard.name)?"bowl":"none",
      dir<0?"left":"right",!guard.name.includes("pause"),false,kind,client.data.rules.guard_styles[kind]);
    if(kind==="patrol" && client.data.wardrobe_suspected) {
      ctx.save();ctx.shadowColor="#ffe191";ctx.shadowBlur=8;label(ctx,"?",guard.x-5,guard.y-82,26);ctx.restore();
      if(client.data.suspect_started_ms) {
        const progress=clamp((gameNow(client.data)-client.data.suspect_started_ms)/client.data.rules.inspection_ms,0,1);
        line(ctx,guard.x-22,guard.y-106,guard.x+22,guard.y-106,"#352b26",5);
        line(ctx,guard.x-22,guard.y-106,guard.x-22+44*progress,guard.y-106,"#f4c267",5);
      }
    } else if(gameNow(client.data)<client.data.alert_until_ms) label(ctx,"!",guard.x-5,guard.y-79,25);
    if(guard.name==='guide_farewell') speechBubble(ctx,guard.x,guard.y-110,'Good luck');
    if(guard.name==='guiding_wait') speechBubble(ctx,guard.x,guard.y-110,'Wait… stay low.');
    if(client.data.roles?.[kind]&&guard.name!=='feast_eat'&&guard.name!=='feast_sleep') label(ctx,client.data.roles[kind].toUpperCase(),guard.x-25,guard.y-70,8);
  }
  if(client.capture)drawCaptor(ctx,client,player,elapsed);
  for(const kind of Object.keys(client.data.guard_routes))
    if(client.data[`${kind}_corpse_x`]!=null && !client.data.story?.voyage?.concealed?.[kind]) fallen(ctx,client.data[`${kind}_corpse_x`],client.data[`${kind}_corpse_y`],client.data.rules.guard_styles[kind].color);
  for(const kind of ['sleeper','cargo']) {
    if(!client.data[kind+'_alive'])continue;
    const wp=watchCrew(client.data,kind);if(!wp)continue;
    if(wp.name==='sleep') {lyingPerson(ctx,300,337,kind==='sleeper'?'#a4483e':'#617947',kind==='sleeper'&&!client.data.has_blue_key);label(ctx,'Zzz',235,310,15);}
    else if(kind==='sleeper'&&wp.name.startsWith('feast_')){if(wp.name!=='feast_sleep'){const sight=160;ctx.fillStyle='rgba(255,218,120,.12)';ctx.fillRect(wp.x+(wp.facing<0?-sight:12),wp.y-55-client.data.rules.vision_height,sight-12,client.data.rules.vision_height*2);}drawFeastCrew(ctx,'sleeper',wp,client.data,elapsed);}
    else if(kind==='sleeper'){person(ctx,wp.x,wp.y,true,elapsed,client.data.story?.voyage?.armed?'pistol':'none',wp.facing>0?'right':'left',true);drawWatchKey(ctx,client.data,wp);}
  }
  if(!client.data.sleeper_alive&&!client.data.story?.voyage?.concealed?.sleeper)fallen(ctx,300,365);
  const vv=client.data.story?.voyage||{};
  const inGuideCover=vv.escort?.hidden;
  if (client.data.in_hammock || client.position.zone === "hammock")lyingPerson(ctx,300,270,vv.captain_worn?client.data.rules.guard_styles.officer.color:client.data.disguised?"#9c3d33":"#2d6b73");
  else if ((!client.data.hidden_barrel && !inGuideCover) || client.capture) {
    const args=[ctx,player.x,player.y,false,performance.now()/1000,client.data.held_item,client.facing,Boolean(client.capture || vv.escort&&!vv.escort.paused || performance.now()<client.motionUntil),client.data.disguised,"patrol",vv.captain_worn?client.data.rules.guard_styles.officer:null];
    if(vv.duck || vv.escort)crouchingPerson(...args);else person(...args);
  } else if(inGuideCover) {
    // A small glimpse of the hat makes it clear where the guide has concealed you.
    line(ctx,player.x-14,player.y-36,player.x+14,player.y-36,'#b5c9be',4);
  }
  drawPartner(ctx,client);
  for(const b of vv.shots||[]) {
    const age=(gameNow(client.data)-b.born)/1000;
    if(age<0){label(ctx,'!',b.x-5,b.y-25,22);continue;}
    if(age>3)continue;
    const bx=b.x+b.dir*320*age;line(ctx,bx-b.dir*13,b.y,bx,b.y,'#ff936b',4);
  }
  for (const bullet of client.bullets || []) {
    ctx.fillStyle="#ffe6a0";ctx.shadowColor="#ffe49b";ctx.shadowBlur=12;
    ctx.beginPath();ctx.arc(bullet.x,bullet.y,4,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;
  }
  cellBars(ctx, Boolean(client.data.door_open || client.capture?.phase==="escort" || gameNow(client.data)>=client.data.alert_started_ms&&gameNow(client.data)<client.data.alert_until_ms&&guards.patrol.x<390&&guards.patrol.y===500));
  drawPartnerName(ctx,client);
  ctx.restore();
  const dim=client.data.bright_view?.25:.61;
  const radius=(client.data.has_lamp&&client.data.lamp_lit&&client.data.held_item==="lamp"?295:205)*camera.zoom;
  const playerScreenY=(player.y-camera.y-25)*camera.zoom;
  const shade=ctx.createRadialGradient(w/2,playerScreenY,50,w/2,playerScreenY,radius);
  shade.addColorStop(0,"rgba(8,16,25,0)");shade.addColorStop(.58,`rgba(8,16,25,${dim*.28})`);
  shade.addColorStop(1,`rgba(8,16,25,${dim})`);
  ctx.fillStyle=shade;ctx.fillRect(0,0,w,h);
  drawRoomBadge(ctx,w,client);
}

function editingTarget(target) {
  if (!(target instanceof Element)) return false;
  return Boolean(target.closest("input, textarea, select, [contenteditable='true'], [role='textbox']"));
}
function controlKey(key) {
  const lower = key.toLowerCase();
  return ["a", "d", "w", "s", "e", "f", "i", "j", "b", "l", "t", "r", "escape", " ", "arrowleft", "arrowright", "arrowup", "arrowdown"].includes(lower);
}
function snapshot(position) {
  return { zone: position.zone, value: Math.round(position.value * 1000) / 1000 };
}
function introCaption(t) {
  if(t<7)return 'A peaceful morning. You sit and fish with your dog.';
  if(t<11)return 'A flash below the water—the dog spots a fish and leaps into the waves!';
  if(t<15.3)return 'You dive in and swim after him, reaching through the waves.';
  if(t<19.4)return 'Small pirate boats surround you and your dog. The pirates close in.';
  if(t<22.5)return '';
  if(t<29)return 'You wake in the cell, frightened and alone.';
  return 'The adventure begins.';
}
function introPerson(ctx,x,y,scale=1,{reach=0,bound=false,sack=false,scared=false,seated=false,color='#2d6b73'}={}) {
  // Keep the cutscene figures close to the scale and proportions of sprites in the game.
  ctx.save();ctx.translate(x,y);ctx.scale(scale*.55,scale*.55);ctx.lineCap='round';
  ctx.strokeStyle='#302b29';ctx.lineWidth=11;if(seated){line(ctx,-10,-39,-19,-17,'#514238',11);line(ctx,-19,-17,8,-17,'#514238',11);line(ctx,10,-39,23,-18,'#514238',11);line(ctx,23,-18,42,-18,'#514238',11);}else{line(ctx,-10,-39,-17,-5,'#514238',11);line(ctx,10,-39,18,-5,'#514238',11);}
  roundBox(ctx,-24,-84,48,49,13,color,'#2c2927');
  line(ctx,-23,-72,reach<0?-60:-38,-51,'#d19a71',10);
  line(ctx,23,-72,reach>0?60:bound?31:43,-50,'#d19a71',10);
  ctx.fillStyle='#cb9270';ctx.beginPath();ctx.arc(0,-103,22,0,Math.PI*2);ctx.fill();
  ctx.fillStyle='#263940';ctx.beginPath();ctx.arc(0,-111,23,Math.PI,Math.PI*2);ctx.lineTo(21,-103);ctx.lineTo(-20,-103);ctx.closePath();ctx.fill();line(ctx,-20,-101,20,-101,'#b5c9be',5);
  ctx.fillStyle='#272322';ctx.beginPath();ctx.arc(-7,-103,scared?3:2,0,Math.PI*2);ctx.arc(7,-103,scared?3:2,0,Math.PI*2);ctx.fill();
  line(ctx,-1,-98,3,-94,'#86563f',2);if(scared){ctx.fillStyle='#4d2525';ctx.beginPath();ctx.ellipse(0,-87,5,7,0,0,Math.PI*2);ctx.fill();}else line(ctx,-6,-88,6,-88,'#7b413b',2);
  if(bound){line(ctx,-25,-53,25,-53,'#d7b77c',5);line(ctx,-12,-59,-18,-47,'#d7b77c',3);line(ctx,12,-59,18,-47,'#d7b77c',3);}
  if(sack){
    ctx.fillStyle='#b99b6c';ctx.strokeStyle='#574633';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(-27,-112);ctx.quadraticCurveTo(-31,-139,0,-137);ctx.quadraticCurveTo(31,-139,27,-112);ctx.quadraticCurveTo(18,-91,0,-87);ctx.quadraticCurveTo(-20,-92,-27,-112);ctx.closePath();ctx.fill();ctx.stroke();
    line(ctx,-19,-113,18,-113,'#6b543a',4);line(ctx,-3,-137,4,-146,'#b99b6c',6);
  }
  ctx.restore();
}
function introDog(ctx,x,y,scale=1,rotation=0,{wet=false,fade=1,paddling=0}={}) {
  ctx.save();ctx.globalAlpha=fade;ctx.translate(x,y);ctx.rotate(rotation);ctx.scale(scale,scale);
  ctx.fillStyle='#d8964d';ctx.strokeStyle='#623e2c';ctx.lineWidth=3;
  ctx.beginPath();ctx.ellipse(0,-17,35,20,-.12,0,Math.PI*2);ctx.fill();ctx.stroke();
  // A distinct chest, four legs, floppy ears, muzzle and nose make the dog readable at a glance.
  ctx.fillStyle='#efc58e';ctx.beginPath();ctx.ellipse(22,-17,9,15,-.2,0,Math.PI*2);ctx.fill();
  ctx.strokeStyle='#623e2c';ctx.fillStyle='#d8964d';ctx.beginPath();ctx.arc(29,-32,17,0,Math.PI*2);ctx.fill();ctx.stroke();
  ctx.beginPath();ctx.moveTo(18,-43);ctx.quadraticCurveTo(9,-61,25,-49);ctx.quadraticCurveTo(29,-42,25,-37);ctx.closePath();ctx.fillStyle='#74452f';ctx.fill();ctx.stroke();
  ctx.beginPath();ctx.moveTo(33,-44);ctx.quadraticCurveTo(49,-57,45,-38);ctx.quadraticCurveTo(42,-34,37,-35);ctx.closePath();ctx.fillStyle='#8a5635';ctx.fill();ctx.stroke();
  ctx.fillStyle='#dba76d';ctx.beginPath();ctx.ellipse(43,-26,14,9,-.08,0,Math.PI*2);ctx.fill();ctx.stroke();
  ctx.fillStyle='#25211e';ctx.beginPath();ctx.arc(35,-35,2.6,0,Math.PI*2);ctx.arc(55,-28,3.4,0,Math.PI*2);ctx.fill();
  ctx.fillStyle='#fff1d3';ctx.beginPath();ctx.arc(35.7,-35.8,.8,0,Math.PI*2);ctx.fill();
  line(ctx,-27,-19,-43,-34,'#b66e3a',7);
  const kick=Math.sin(paddling*8);line(ctx,-20,-4,-23,7+kick*5,'#74452f',6);line(ctx,4,-3,7,7-kick*5,'#74452f',6);line(ctx,18,-5,22,6+Math.sin(paddling*8+1)*5,'#74452f',6);line(ctx,31,-6,34,5-Math.sin(paddling*8+1)*5,'#74452f',6);
  line(ctx,-3,-34,20,-31,'#b84037',5);ctx.fillStyle='#efc58e';ctx.beginPath();ctx.ellipse(8,-31,5,8,-.2,0,Math.PI*2);ctx.fill();
  if(wet){ctx.fillStyle='rgba(198,231,231,.72)';ctx.beginPath();ctx.ellipse(2,-4,39,7,0,0,Math.PI*2);ctx.fill();}
  ctx.restore();
}
function introFish(ctx,x,y,scale=1) {
  ctx.save();ctx.translate(x,y);ctx.scale(scale,scale);ctx.fillStyle='#e8b96d';ctx.strokeStyle='#704c35';ctx.lineWidth=2;
  ctx.beginPath();ctx.ellipse(0,0,17,9,0,0,Math.PI*2);ctx.fill();ctx.stroke();
  ctx.beginPath();ctx.moveTo(-15,0);ctx.lineTo(-27,-9);ctx.lineTo(-27,9);ctx.closePath();ctx.fill();ctx.stroke();
  ctx.fillStyle='#25211e';ctx.beginPath();ctx.arc(10,-2,1.7,0,Math.PI*2);ctx.fill();
  line(ctx,4,-7,4,7,'#a87845',1.5);ctx.restore();
}
function introSkiff(ctx,x,y,scale,player,dog,t) {
  ctx.save();ctx.translate(x,y);ctx.scale(scale,scale);
  ctx.fillStyle='#724a32';ctx.strokeStyle='#392a23';ctx.lineWidth=5;ctx.beginPath();ctx.moveTo(-176,-10);ctx.quadraticCurveTo(0,28,176,-10);ctx.lineTo(144,37);ctx.quadraticCurveTo(0,60,-144,37);ctx.closePath();ctx.fill();ctx.stroke();
  line(ctx,-158,-7,158,-7,'#dfb77a',5);roundBox(ctx,-80,-29,160,18,4,'#a6784b','#4b3527');
  // Fishing rod, line and bobber make the opening action readable at a glance.
  line(ctx,-42,-26,-74,-119,'#553a2c',6);line(ctx,-74,-119,22,-7,'#ddcc9a',2);
  ctx.fillStyle='#e65a46';ctx.beginPath();ctx.arc(22,-5,5,0,Math.PI*2);ctx.fill();
  if(player)introPerson(ctx,-46,-26,1.12,{reach:player.reach,bound:player.bound,sack:player.sack,seated:player.seated});
  if(dog)introDog(ctx,dog.x,dog.y,dog.scale,dog.rotation,{wet:dog.wet,fade:dog.fade,paddling:dog.paddling});
  ctx.restore();
}
function introPirate(ctx,x,y,scale=1) {
  introPerson(ctx,x,y,scale,{color:'#9c3d33'});
  ctx.save();ctx.translate(x,y);ctx.scale(scale*.55,scale*.55);ctx.fillStyle='#302724';ctx.beginPath();ctx.moveTo(-29,-72);ctx.lineTo(0,-87);ctx.lineTo(30,-72);ctx.closePath();ctx.fill();line(ctx,-18,-70,20,-70,'#d4b878',4);
  line(ctx,12,-42,34,-76,'#d9e0e4',4);line(ctx,12,-42,19,-34,'#9a7948',5);line(ctx,34,-76,39,-84,'#fff0cb',2);ctx.restore();
}
function drawIntroCell(ctx,w,h,t,clamp01) {
  const fade=clamp01((t-21.3)/1.2);if(!fade)return;
  ctx.save();ctx.globalAlpha=fade;ctx.fillStyle='#101c20';ctx.fillRect(0,0,w,h);
  const wall=ctx.createLinearGradient(0,0,0,h);wall.addColorStop(0,'#344248');wall.addColorStop(1,'#191e20');ctx.fillStyle=wall;ctx.fillRect(0,0,w,h);
  for(let y=34;y<h;y+=48)line(ctx,0,y,w,y,'#4f4b3e',3);
  const cx=w*.52,doorW=Math.min(w*.64,470),left=cx-doorW/2,top=h*.16,bottom=h*.81;
  ctx.fillStyle='#282b27';ctx.fillRect(left,top,doorW,bottom-top);
  ctx.fillStyle='#403d33';ctx.fillRect(left+8,bottom-29,doorW-16,27);
  // A high barred porthole and brass-lit seams locate the brig beneath deck.
  ctx.fillStyle='#112e38';ctx.beginPath();ctx.arc(cx,h*.31,Math.min(48,w*.08),Math.PI,Math.PI*2);ctx.lineTo(cx+Math.min(48,w*.08),h*.36);ctx.lineTo(cx-Math.min(48,w*.08),h*.36);ctx.closePath();ctx.fill();
  for(let i=-2;i<=2;i++)line(ctx,cx+i*18,h*.26,cx+i*18,h*.39,'#aa9568',4);line(ctx,cx-50,h*.35,cx+50,h*.35,'#aa9568',4);
  // The captive is left alone, still hooded and bound. No dog appears in the brig.
  introPerson(ctx,cx,h*.78,Math.min(1.25,w/650),{scared:true,color:'#2d6b73'});
  for(let i=0;i<7;i++)line(ctx,left+doorW*(i+.5)/7,top,left+doorW*(i+.5)/7,bottom,'#b29868',5);
  line(ctx,left,top,left,bottom,'#b29868',8);line(ctx,left+doorW,top,left+doorW,bottom,'#b29868',8);
  ctx.restore();
}
function drawIntroScene(ctx,w,h,t) {
  const clamp01=x=>Math.max(0,Math.min(1,x));
  const mix=(a,b,f)=>Math.round(a+(b-a)*f);
  const dawn=clamp01(t/7),cellFade=clamp01((t-21.3)/1.2),sea=h*.53;
  const boatX=w*.44,boatY=sea-h*.035,unit=Math.min(w/900,h/500);
  const jump=clamp01((t-8.7)/1.3),pirateReveal=clamp01((t-15.3)/1.8),zoom=t<8?1.55:t<10.5?1.55+.75*clamp01((t-8)/2.5):t<15.2?2.3-.32*clamp01((t-10.5)/4.7):t<17.7?1.98-1.03*clamp01((t-15.2)/2.5):t<19.4? .95:1;
  let focusX=boatX,focusY=boatY-h*.07;
  if(t>=8&&t<11.2){const f=clamp01((t-8)/.9);focusX=boatX+unit*(92+250*clamp01((t-8.7)/1.3))*f;focusY=sea+h*.02;}
  else if(t>=11.2&&t<15.2){focusX=boatX+unit*330;focusY=sea+h*.02;}
  else if(t>=15.2&&t<19.4){const reveal=clamp01((t-15.2)/2.5);focusX=boatX+unit*330+(w*.5-(boatX+unit*330))*reveal;focusY=sea+h*.02+(sea-h*.08-(sea+h*.02))*reveal;}
  ctx.save();ctx.translate(w*.5,h*.5);ctx.scale(zoom,zoom);ctx.translate(-focusX,-focusY);
  const sky=ctx.createLinearGradient(0,0,0,h);
  sky.addColorStop(0,`rgb(${mix(39,19,dawn)},${mix(79,42,dawn)},${mix(111,62,dawn)})`);
  sky.addColorStop(.64,`rgb(${mix(218,150,dawn)},${mix(151,106,dawn)},${mix(114,86,dawn)})`);
  sky.addColorStop(1,'#173b4b');ctx.fillStyle=sky;ctx.fillRect(0,0,w,h);
  ctx.fillStyle='#f4c67f';ctx.globalAlpha=.85;ctx.beginPath();ctx.arc(w*.78,h*.23,Math.min(28,w*.05),0,Math.PI*2);ctx.fill();ctx.globalAlpha=1;
  const water=ctx.createLinearGradient(0,sea,0,h);water.addColorStop(0,'#287185');water.addColorStop(1,'#102f42');ctx.fillStyle=water;ctx.fillRect(0,sea,w,h-sea);
  for(let i=0;i<12;i++){const yy=sea+12+i*i*2.1,xx=(i*97+performance.now()*.012)%(w+120)-60;line(ctx,xx,yy,xx+w*.13,yy,'rgba(230,222,188,.3)',2);}
  if(pirateReveal>0){
    const positions=[[w*.14,.32],[w*.38,.29],[w*.62,.3],[w*.91,.33]];
    ctx.save();ctx.beginPath();ctx.rect(-w,-h,w*3,sea+h);ctx.clip();
    positions.forEach(([sx,ss],i)=>{
      const approach=clamp01((t-15.5-i*.2)/1.35),px=sx+(w*.5-sx)*approach*(i===3?.08:.25),boatScale=ss*unit*2.3,py=sea-boatScale*8+Math.sin(t*2+i)*1.5;
      ctx.save();ctx.globalAlpha=pirateReveal;ctx.translate(px,py);ctx.scale(boatScale,boatScale);
      ctx.fillStyle='#563c30';ctx.strokeStyle='#241e1c';ctx.lineWidth=5;ctx.beginPath();ctx.moveTo(-125,-6);ctx.quadraticCurveTo(0,22,125,-6);ctx.lineTo(99,25);ctx.quadraticCurveTo(0,43,-99,25);ctx.closePath();ctx.fill();ctx.stroke();
      ctx.fillStyle='#271f1d';ctx.beginPath();ctx.moveTo(-22,-5);ctx.lineTo(-20,-148);ctx.lineTo(0,-135);ctx.closePath();ctx.fill();ctx.beginPath();ctx.moveTo(23,-5);ctx.lineTo(20,-132);ctx.lineTo(48,-30);ctx.closePath();ctx.fill();
      // One pirate stands on each deck, with a raised sword instead of mast-like stray lines.
      introPirate(ctx,0,8,1.05);line(ctx,-19,-122,29,-94,'rgba(231,211,164,.7)',2);ctx.restore();
    });
    ctx.restore();
  }
  const dogFade=1-clamp01((t-19.4)/.8);
  if(t<19.4){
    if(t<14.3){
      introSkiff(ctx,boatX,boatY,unit,t<11?{reach:t>=8?1:0,seated:t<8}:null,null,t);
      // Let the water cover the submerged half of the hull and the character's legs.
      const surface=ctx.createLinearGradient(0,sea,0,h);surface.addColorStop(0,'#287185');surface.addColorStop(1,'#102f42');ctx.fillStyle=surface;ctx.fillRect(0,sea,w,h-sea);
      line(ctx,0,sea+2,w,sea+2,'rgba(230,222,188,.42)',2);
    }
    if(t>=6.8&&t<10.4)introFish(ctx,boatX+150*unit,sea+h*.065+Math.sin(t*4)*4,unit*.7);
    const dogStart=boatY-42*unit,dogWater=sea+h*.02,dy=dogStart+(dogWater-dogStart)*jump-Math.sin(Math.PI*jump)*h*.055+(t>=10?Math.sin(t*7)*2:0);
    const swim=clamp01((t-10)/.8),dx=boatX+unit*(92+250*jump+24*swim+Math.sin(t*3)*7*swim);
    if(t<8.7)introDog(ctx,boatX+92*unit,boatY-42*unit,unit*.82,Math.sin(t*4)*.04,{fade:1});
    else if(t<19.4){introDog(ctx,dx,dy,unit*.82,jump<1?-.2*jump:.02*Math.sin(t*4),{wet:t>=10,fade:dogFade,paddling:t});
      if(t>=9.9&&t<12.5){ctx.save();ctx.strokeStyle='rgba(230,245,237,.9)';ctx.lineWidth=3;for(let i=0;i<7;i++){ctx.beginPath();ctx.arc(dx+(i-3)*12,dy-8,6+i%2*5,Math.PI*1.1,Math.PI*1.9);ctx.stroke();}ctx.restore();}}
    if(t>=11&&t<19.4){
      const hx=boatX+unit*(390+Math.sin(t*2)*8),hy=sea+h*.02+Math.sin(t*5)*3;
      ctx.save();ctx.translate(hx,hy);ctx.rotate(Math.PI/2);introPerson(ctx,0,0,unit,{reach:1,color:'#2d6b73'});ctx.restore();
      ctx.save();ctx.strokeStyle='rgba(230,245,237,.85)';ctx.lineWidth=3;for(let i=0;i<8;i++){ctx.beginPath();ctx.arc(hx+(i-4)*15,hy+Math.sin(t*3+i)*5,5+i%2*5,Math.PI*1.1,Math.PI*1.9);ctx.stroke();}ctx.restore();
    }
  }
  ctx.restore();
  if(cellFade>0)drawIntroCell(ctx,w,h,t,clamp01);
  if(t>=19.4&&t<22.5){
    const darkness=t<20.4?clamp01((t-19.4)/1):t<21.3?1:1-clamp01((t-21.3)/1.2);ctx.fillStyle=`rgba(0,0,0,${darkness})`;ctx.fillRect(0,0,w,h);
  }
  if(t>=28.6){
    ctx.save();ctx.globalAlpha=clamp01((t-28.6)/.8);ctx.fillStyle='rgba(5,12,16,.4)';ctx.fillRect(0,0,w,h);
    ctx.textAlign='center';ctx.fillStyle='#f2cd84';ctx.font=`800 ${Math.max(12,Math.min(16,w*.017))}px system-ui`;
    ctx.fillText('TEAM PLOT TWIST',w/2,h*.22);ctx.fillStyle='#fff4dc';ctx.font=`bold ${Math.max(22,Math.min(36,w*.038))}px Georgia`;
    ctx.fillText('Escape from the pirate ship',w/2,h*.31);ctx.restore();
  }
}
function introProgress(client,now=performance.now()) {
  if(client.introStartedAt==null)return null;
  const elapsed=(now-client.introStartedAt)/1000;
  if(elapsed>=30){client.introPausedMs+=now-client.introStartedAt;client.introStartedAt=null;return null;}
  return elapsed;
}

export default function ({ data, parentElement, key, setTriggerValue, setStateValue }) {
  // A Streamlit rerun updates `data`; it must not pull a moving player back to
  // an older database snapshot. A new run_id intentionally starts fresh.
  const runId = String(data.run_id ?? "") + ":" + String(data.revision ?? "");
  let client = clients.get(key);
  if (!client || client.runId !== runId) {
    let introStartedAt=null;
    if(data.intro){
      let seen=false;
      try{const seenKey=`team-pt-intro-${data.run_id}`;seen=sessionStorage.getItem(seenKey)==='seen';if(!seen)sessionStorage.setItem(seenKey,'seen');}catch(_){}
      if(!seen)introStartedAt=performance.now();
    }
  client = {
      runId, position: { zone: data.position.zone, value: Number(data.position.value) },
      keys: new Set(), lastSent: snapshot(data.position), lastReportAt: performance.now(),
      lastFeedbackSeq: data.feedback?.seq ?? 0, flashText: "", flashUntil: 0,
      bullets: [], lastShotAt: -10000, facing: data.facing || "right",
      inventoryOpen:false, motionUntil:0, capture:null, capturePending:false,
      requestPrefix:globalThis.crypto?.randomUUID?.()||String(Math.random()),nextRequest:0,delivery:0,inFlightPayload:null,lastDeliveryAt:0,
      alertPending:false, nextAlertAttempt:0, actionInFlight:false, pendingActions:[],
      suspectPending:false, nextSuspectAttempt:0, readingPending:false, endingStartedAt:performance.now(),
      introStartedAt,introPausedMs:0,introSplashPlayed:false,
    };
    clients.set(key, client);
  }
  data.parsedAlertPaths=JSON.parse(data.alert_paths || "{}");
  data.parsedAlertResume=JSON.parse(data.alert_resume || "{}");
  client.wasEscorted=Boolean(client.data?.story?.voyage?.escort);
  client.data = data;
  client.data.guard_started_ms=Number(data.guard_started_ms||0)+client.introPausedMs;
  client.key = key;
  syncMultiplayer(client,data,key,setTriggerValue);
  if (data.feedback?.seq !== client.lastFeedbackSeq) {
    client.lastFeedbackSeq = data.feedback?.seq;
    const matching=!client.actionInFlight || data.feedback?.request_id===undefined || data.feedback.request_id===client.inFlightPayload?.request_id;
    if(matching) {
    if(data.feedback?.text || !['voyage_tick','capture_tick'].includes(client.inFlightKind)) {
      client.flashText = data.feedback?.text || "";
      client.flashUntil = performance.now() + 3000;
    }
    client.readingPending = false;
    client.capturePending = false;
    client.alertPending = false;
    client.suspectPending = false;
    client.actionInFlight = false;
    client.inFlightPayload = null;
    if (data.feedback?.accepted) {
      if(client.inFlightKind==='ambush'&&client.ambushSnap){const b=positionXY(client.position,data.rules);
        client.ambushAnim={...client.ambushSnap,bx:b.x,by:b.y,start:performance.now()};}
      if ((client.inFlightKind!=="voyage_tick" || data.story?.voyage?.escort || client.wasEscorted) && ["restart_prompt","barrel","hammock","capture","capture_complete","story_inspect","journal","story_finish","voyage_tick","bribe"].includes(client.inFlightKind)) {
      client.position = { zone: data.position.zone, value: Number(data.position.value) };
      client.lastSent = snapshot(client.position);
      client.facing = data.facing || client.facing;
      } else { client.lastSent = snapshot(data.position); }
    }
  }

    }
  if(data.ending && data.ending!==client.lastEnding) client.endingStartedAt=performance.now();
  client.lastEnding=data.ending;
  if(data.reading || data.ending) { client.keys.clear();client.pendingActions=[]; }
  // Defensive cleanup also covers data-driven reinitialization of the same DOM.
  if (parentElement.__teamPlotTwistCleanup) parentElement.__teamPlotTwistCleanup();
  const stage = parentElement.querySelector(".pt-stage");
  const canvas = parentElement.querySelector(".pt-canvas");
  const location = parentElement.querySelector(".pt-location");
  const inventory = parentElement.querySelector(".pt-inventory");
  const prompt = parentElement.querySelector(".pt-prompt");
  const feedback = parentElement.querySelector(".pt-feedback");
  const alertBanner = parentElement.querySelector(".pt-alert");
  const alertSeconds = parentElement.querySelector(".pt-alert-seconds");
  const cutsceneBanner = parentElement.querySelector(".pt-cutscene");
  const inventoryPanel = parentElement.querySelector(".pt-inventory-panel");
  const itemButtons = Array.from(parentElement.querySelectorAll("[data-item]"));
  const documentPanel=parentElement.querySelector(".pt-document-panel");
  const documentClose=parentElement.querySelector(".pt-document-close");
  const endingConfirm=parentElement.querySelector(".pt-ending-confirm");
  const journalButton=parentElement.querySelector(".pt-journal-button");
  const endingPanel=parentElement.querySelector(".pt-ending-panel");
  const replayScene=parentElement.querySelector(".pt-replay-scene");
  const introUi=parentElement.querySelector('.pt-intro-ui'),introText=parentElement.querySelector('.pt-intro-caption'),introSkip=parentElement.querySelector('.pt-intro-skip'),introMusicButton=parentElement.querySelector('.pt-intro-music');
  const fullscreenButton=parentElement.querySelector('.pt-fullscreen-button');
  async function toggleFullscreen(){
    try {
      if(document.fullscreenElement)await document.exitFullscreen();
      else await parentElement.querySelector('.pt-game').requestFullscreen({navigationUI:'hide'});
      stage.focus({preventScroll:true});
    } catch(error) {client.flashText='Fullscreen is unavailable here. Open the game in your regular browser.';client.flashUntil=performance.now()+4000;}
  }
  fullscreenButton.addEventListener('click',toggleFullscreen);
  const restartButton=parentElement.querySelector('.pt-restart-button');
  function restartPrompt(){if(client.data.ending){client.restartPrompt=true;renderStoryPanels(parentElement,client);}else action('restart_prompt');}
  restartButton.addEventListener('click',restartPrompt);
  function skipIntro(){if(client.introStartedAt!=null){client.introPausedMs+=performance.now()-client.introStartedAt;client.introStartedAt=null;}client.keys.clear();}
  introSkip.addEventListener('click',skipIntro);
  const music=musicEngine(),musicButton=parentElement.querySelector('.pt-music-button'),volume=parentElement.querySelector('.pt-music-volume');
  async function toggleMusic(){await music.toggle();stage.focus({preventScroll:true});}
  function changeVolume(){music.volume=Number(volume.value);try{localStorage.setItem('team-pt-music-volume',String(music.volume));}catch(_){}const p=introProgress(client);music.touch(client.data,p!==null,p??0,finaleDarkNow(client.data));}
  musicButton.addEventListener('click',toggleMusic);volume.addEventListener('input',changeVolume);volume.value=music.volume;
  introMusicButton.addEventListener('click',toggleMusic);
  renderStoryPanels(parentElement,client);

  let raf = 0, lastFrameAt = performance.now(), lastPrompt = null;

  function reportPosition(force = false) {
    if (client.data.ending || client.data.reading || client.readingPending || client.data.story?.voyage?.escort) return;
    if (client.actionInFlight) return; // Keep position updates from replacing an unacknowledged action.
    const next = snapshot(client.position);
    if (next.zone === client.lastSent.zone && next.value === client.lastSent.value) return;
    const now = performance.now();
    if (!force && now - client.lastReportAt < 800) return;
    client.lastReportAt = now;
    client.lastSent = next;
    setStateValue("position", {...next,run_id:String(client.data.run_id??'')});
  }
  function setPrompt(text) {
    if (text === lastPrompt) return;
    lastPrompt = text;
    prompt.hidden = !text;
    prompt.textContent = text;
  }
  function deliver(payload) {
    client.actionInFlight=true;client.inFlightKind=payload.kind;
    client.inFlightPayload=payload;client.lastDeliveryAt=performance.now();
    setTriggerValue('action',{...payload,delivery:++client.delivery});
  }
  function action(kind, item = null) {
    if(client.data.ending&&!['restart_game','finale_start','finale_report','finale_retry'].includes(kind)) return;
    if((kind==='restart_prompt'||kind==='journal'||kind==='story_inspect'&&!['chest','coins','helm'].includes(client.data.rules.story_points?.[item]?.kind)) && !client.actionInFlight) {
      client.readingPending=true;client.keys.clear();client.data.uiPauseAt=Date.now();
    }
    const payload = {
      request_id:`${runId}:${client.requestPrefix}:${++client.nextRequest}`,
      run_id:String(client.data.run_id??''),
      kind,
      position: snapshot(client.position),
      guard_elapsed: guardElapsed(client.data,kind==="capture"?item||"patrol":"patrol"),
      facing: client.facing,
      item,
    };
    if (client.actionInFlight) {
      if(!['voyage_tick','capture_tick'].includes(kind)) client.pendingActions.push(payload);
      return;
    }
    deliver(payload);
  }
  function nearDoor() {
    const r=client.data.rules;
    return (client.position.zone === "cell" && client.position.value >= r.cell_key_player_min)
      || (client.position.zone === "hold" && client.position.value >= r.door_block_max && client.position.value <= r.door_hold_near_max);
  }
  function eAction() { return interactionKind(client.data,client.position,"e",client.data.rules); }
  function fAction() { return interactionKind(client.data,client.position,"f",client.data.rules); }
  function shoot(now) {
    if (now - client.lastShotAt < 420) return;
    client.lastShotAt = now;
    if (client.data.held_item === "pistol" && client.position.zone !== "hammock" && !client.data.hidden_barrel) {
      const xy = positionXY(client.position,client.data.rules), dir = client.facing === "right" ? 1 : -1;
      let stop = dir > 0 ? client.data.rules.world_max : client.data.rules.floors.cell[0];
      const doorX = client.data.rules.door_x;
      if (!client.data.door_open && xy.y === 500 && ((dir > 0 && xy.x < doorX) || (dir < 0 && xy.x > doorX))) stop = doorX;
      client.bullets.push({ x: xy.x + dir * 15, y: xy.y - 30, dir, stop, born: now });
    }
    action("shoot");
  }
  function onKeyDown(event) {
    if (event.metaKey || event.ctrlKey || event.altKey || editingTarget(event.target)) return;
    const k = event.key.toLowerCase();
    if (!controlKey(k)) return;
    if (k.startsWith("arrow") || k === " ") event.preventDefault();
    if(introProgress(client)!==null){if(k==='escape')skipIntro();return;}
    if(client.restartPrompt){if((k==='f'||k==='escape')&&!event.repeat)closeDocument();event.preventDefault();return;}
    if(client.data.ending) { if(controlKey(k)) event.preventDefault();finaleKey(client,k,event.repeat,finaleRetry);return; }
    if(client.data.reading) {
      if(controlKey(k)) event.preventDefault();
      if((k==="f"||k==="escape") && !event.repeat) action("close_reading");
      return;
    }
    if(client.readingPending) { if(controlKey(k)) event.preventDefault();return; }

    if(k === "escape"){client.inventoryOpen=false;client.scope=null;return;}
    if(k === "j" && !event.repeat) {event.preventDefault();action("journal");return;}
    if(client.data.capture_phase === "active" || client.capturePending) return;
    if(client.ambushAnim && (k==='e'||k==='f')) {event.preventDefault();return;}
    if(client.data.hidden_barrel && k==='e') {
      event.preventDefault();if(event.repeat)return;
      const target=ambushTarget(client);
      client.ambushSnap=target?{kind:target[0],x:target[1].x,y:target[1].y}:null;
      action('ambush',target?.[0]||'');return;
    }
    if(client.data.hidden_barrel && k !== "f") {
      if(!event.repeat){client.flashText="Press F to leave the barrel first.";client.flashUntil=performance.now()+1800;}
      return;
    }
    if(client.data.story?.voyage?.escort)return;
    if(client.scope) {
      event.preventDefault();
      if(['f','escape','s','arrowdown','w','arrowup','e'].includes(k)&&!event.repeat&&k!=='e')client.scope=null;
      else if(['a','d','arrowleft','arrowright'].includes(k))client.keys.add(k);
      return;
    }
    if(k==='f'&&!event.repeat&&storyPoint(client.position,client.data.rules,client.data)?.[1].kind==='telescope') {
      event.preventDefault();client.keys.clear();client.scope={pan:850+(client.facing==='left'?-600:0)};return;
    }
    if(k===' ') {
      event.preventDefault();if(!event.repeat)action('toggle_duck');return;
    }
    if(k==='t'&&!event.repeat) {
      const xy=positionXY(client.position,client.data.rules);
      const choice=[['cook','dining'],['boatswain','boatswain']].find(([,kind])=>{const q=guardPose(client.data,kind);return Math.abs(q.x-xy.x)<65&&Math.abs(q.y-xy.y)<25;});
      if(choice)action('bribe',choice[0]);else {client.flashText='Move near the cook (2 coins) or boatswain (3 coins).';client.flashUntil=performance.now()+2500;}return;
    }
    if(k === "i" && !event.repeat){client.inventoryOpen=!client.inventoryOpen;event.preventDefault();return;}
    if(client.inventoryOpen) return;
    if(k==="b"&&!event.repeat){event.preventDefault();action("whistle");return;}
    if(k==="l"&&!event.repeat){event.preventDefault();action("toggle_lamp");return;}
    if (k === "e" || k === "f") {
      event.preventDefault();
      if (!event.repeat) {
        const kind=k === "e" ? eAction() : fAction();
        action(kind,kind.startsWith("story_")?storyPoint(client.position,client.data.rules,client.data)?.[0]:null);
      }
      return;
    }
    if (k === "r") {
      if (!event.repeat) shoot(performance.now());
      return;
    }
    // A short physical tap (or automated pressKey) may end before the next
    // animation frame. Give its first keydown a small, visible movement step.
    if (!event.repeat && !client.keys.has(k)) {
      const h = Number(k === "d" || k === "arrowright") - Number(k === "a" || k === "arrowleft");
      const v = Number(k === "w" || k === "arrowup") - Number(k === "s" || k === "arrowdown");
      const before = client.position;
      const after = move(before, Boolean(client.data.door_open), h, v, .09*(client.data.story?.voyage?.duck ? .45 : 1), client.data.rules);
      if (h) client.facing = h > 0 ? "right" : "left";
      if (after.zone !== before.zone || after.value !== before.value) {
        client.position = after;
        client.motionUntil=performance.now()+150;
        reportPosition(after.zone !== before.zone);
      }
    }
    client.keys.add(k);
  }
  function onKeyUp(event) {
    const k = event.key.toLowerCase();
    if (!controlKey(k)) return;
    if ((k.startsWith("arrow") || k === " ") && !editingTarget(event.target)) event.preventDefault();
    client.keys.delete(k);
    reportPosition(true);
  }
  function onBlur() { client.keys.clear(); reportPosition(true); }
  function onPointerDown() { stage.focus({ preventScroll: true }); }
  function onItemClick(event){
    const item=event.currentTarget.dataset.item;
    if(client.data.ending || client.data.reading || client.data.capture_phase==="active" || client.data.hidden_barrel) return;
    action("select_item",item);
  }
  function closeDocument(){if(client.restartPrompt){client.restartPrompt=false;renderStoryPanels(parentElement,client);}else if(!client.actionInFlight) action('close_reading');}
  function confirmEnding(){if(client.data.reading==='restart_confirm'||client.restartPrompt){action('restart_game');return;} if(!client.actionInFlight) action("story_finish",client.data.reading==="confirm_castaway"?"cell_floor":client.data.reading==="confirm_dinghy"?"lifeboat":client.data.reading==="confirm_takeover"?"helm":"return_crate"); }
  function openJournal(){ if(!client.data.reading) action("journal"); }
  function replay(){ client.endingStartedAt=performance.now(); }
  function finaleRetry(){ if(client.data.finale?.status==='lost'&&!client.actionInFlight) action('finale_retry'); }
  const finaleRetryButton=parentElement.querySelector('.pt-finale-retry');
  finaleRetryButton.addEventListener('click',finaleRetry);
  function trapDocumentFocus(event){
    if(event.key!=="Tab") return;
    const stops=[...documentPanel.querySelectorAll('button:not([hidden]),summary')].filter(el=>!el.disabled);
    const current=event.composedPath()[0],i=stops.indexOf(current);
    if(!stops.length) return;
    if(event.shiftKey && i<=0){event.preventDefault();stops.at(-1).focus();}
    else if(!event.shiftKey && (i<0||i===stops.length-1)){event.preventDefault();stops[0].focus();}
  }
  documentPanel.addEventListener('keydown',trapDocumentFocus);
  documentClose.addEventListener("click",closeDocument);
  endingConfirm.addEventListener("click",confirmEnding);
  journalButton.addEventListener("click",openJournal);
  replayScene.addEventListener("click",replay);
  itemButtons.forEach(button=>button.addEventListener("click",onItemClick));
  // Consecutive key presses must be applied in order. Streamlit otherwise
  // receives only the last trigger when two actions happen before its rerun.
  if (!client.actionInFlight && client.pendingActions.length) {
    const next=client.pendingActions.shift();
    if(['barrel','hammock'].includes(next.kind))next.position=snapshot(client.position);
    next.guard_elapsed=guardElapsed(client.data);
    deliver(next);
  }

  function frame(now) {
    const dt = clamp((now - lastFrameAt) / 1000, 0, .05);
    lastFrameAt = now;
    if(client.actionInFlight&&client.inFlightPayload&&now-client.lastDeliveryAt>1500)deliver(client.inFlightPayload);
    const introTime=introProgress(client,now);
    music.touch(client.data,introTime!==null,introTime??0,finaleDarkNow(client.data));
    if(introTime!==null&&introTime>=9.9&&!client.introSplashPlayed){client.introSplashPlayed=true;music.playSplash();}
    if(music.error&&music.error!==client.musicError){client.flashText=music.error;client.flashUntil=now+6000;}client.musicError=music.error;
    musicButton.textContent=music.enabled?'Music: on ♫':'Music: off ♫';musicButton.setAttribute?.('aria-pressed',String(music.enabled));
    introMusicButton.textContent=music.enabled?'Sound: on ♫':'Sound: off ♫';introMusicButton.setAttribute('aria-pressed',String(music.enabled));
    const e=client.data.story?.voyage?.escort;
    if(e&&!client.data.reading){const p=guidePosition(e,gameNow(client.data)),before=positionXY(client.position,client.data.rules);client.position=positionAtXY(p,client.data.rules);if(Math.abs(p.x-before.x)>.01)client.facing=p.x>before.x?'right':'left';}
    const frozen=Boolean(introTime!==null || client.data.ending || client.data.reading || client.readingPending);
    if(!frozen && !client.actionInFlight && now>=(client.nextVoyageTick||0) && client.data.capture_phase==='none' && crewTickNeeded(client.data,client.position)) {
      client.nextVoyageTick=now+(client.data.story?.voyage?.armed||client.data.story?.voyage?.escort?250:1000);action('voyage_tick');
    }
    if(!frozen && client.data.capture_phase==='active' && !client.actionInFlight && now>=(client.nextCaptureTick||0)) {
      client.nextCaptureTick=now+1000;action('capture_tick');
    }
    if(!frozen) advanceCapture(client,dt,action);
    const keys = client.keys;
    const horizontal = Number(keys.has("d") || keys.has("arrowright")) - Number(keys.has("a") || keys.has("arrowleft"));
    const vertical = Number(keys.has("w") || keys.has("arrowup")) - Number(keys.has("s") || keys.has("arrowdown"));
    if(client.scope&&(frozen||client.position.zone!=='mast_top'||client.capture||client.capturePending||client.data.capture_phase!=='none'))client.scope=null;
    if(client.scope) client.scope.pan=(client.scope.pan+horizontal*420*dt+SCOPE_WIDTH)%SCOPE_WIDTH;
    else if (!frozen && (horizontal || vertical) && !client.capture && !client.capturePending && !client.inventoryOpen && !client.data.hidden_barrel && !client.data.story?.voyage?.escort) {
      if (horizontal) client.facing = horizontal > 0 ? "right" : "left";
      const before = client.position;
      const after = move(before, Boolean(client.data.door_open), horizontal, vertical, dt*(client.data.story?.voyage?.duck ? .45 : 1), client.data.rules);
      if (after.zone !== before.zone || after.value !== before.value) {
        client.position = after;
        client.motionUntil=now+100;
        reportPosition(after.zone !== before.zone);
      }
    }
    client.bullets = client.bullets.filter(bullet => {
      bullet.x += bullet.dir * 780 * dt;
      return now - bullet.born < 4000 && (bullet.dir > 0 ? bullet.x < bullet.stop : bullet.x > bullet.stop);
    });
    const guards=Object.fromEntries(Object.keys(client.data.guard_routes).map(kind=>[kind,guardPose(client.data,kind)]));
    const guard=guards.patrol;
    const threats=Object.entries(guards).filter(([kind])=>client.data[kind+'_alive']).map(([,g])=>g);
    if(!client.data.hidden_barrel)threats.push(positionXY(client.position,client.data.rules));
    client.rats=stepRats(client.rats||initRats(),frozen?0:dt,threats,now);
    if(!frozen && !client.capture && !client.capturePending && client.data.capture_phase==="none" && !client.data.story?.voyage?.escort?.hidden){
      const spotted=Object.entries(guards).find(([kind,pose])=>guardCanSee(client,pose,kind));
      if(spotted){
        client.capturePending=true;client.keys.clear();action("capture",spotted[0]);
      } else if(guardNoticesDoor(client,guard) && !client.alertPending && now>=client.nextAlertAttempt){
        client.alertPending=true;client.nextAlertAttempt=now+1200;action("alert");
      } else {
        const suspicious=investigating(client,guard);
        if(now>=client.nextSuspectAttempt && !client.suspectPending && !client.actionInFlight) {
          if(wardrobeInSight(client,guard)) {
            client.suspectPending=true;client.nextSuspectAttempt=now+300;action("notice_wardrobe");
          } else if((suspicious&&!client.data.suspect_started_ms) ||
              (suspicious&&client.data.suspect_started_ms&&gameNow(client.data)-client.data.suspect_started_ms>client.data.rules.inspection_ms+30) ||
              (!suspicious&&client.data.suspect_started_ms)) {
            client.suspectPending=true;client.nextSuspectAttempt=now+150;
            action("suspicion");
          }
        }
      }
    }
    const stage2=feastStage(client.data);
    if(stage2!==client.feastStage){
      const say={gathering:"The cook rings the bell: \"Stew's ready!\" Stay out of sight.",eating:'The crew eat the stew. Wait for the pills to work…',asleep:'The whole crew is asleep! You have two minutes: the dinghy or the helm.',waking:'The crew are waking up…'}[stage2];
      if(say&&client.feastStage!==undefined){client.flashText=say;client.flashUntil=now+4500;}
      client.feastStage=stage2;
    }
    const fin=finaleStep(client,now);
    if(client.data.ending&&client.data.ending!=='free'&&!client.data.finale&&!endingPreludeActive(client)&&now-client.endingStartedAt>=3000&&!client.actionInFlight&&now>=(client.nextFinaleStart||0)){
      client.nextFinaleStart=now+2500;action('finale_start');
    }
    if(fin&&fin.over&&client.data.finale.status==='active'&&!client.actionInFlight&&now>=fin.nextReportAt&&fin.reports<6){
      fin.nextReportAt=now+2000;fin.reports++;action('finale_report',JSON.stringify(fin.moves));
    }
    finaleRetryButton.hidden=client.data.finale?.status!=='lost';
    reportPosition();
    publishPosition(client,key,now);
    if(introTime!==null){
      const ctx=canvas.getContext('2d'),dpr=window.devicePixelRatio||1,w=Math.max(320,stage.clientWidth),h=stage.clientHeight;
      if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);}
      ctx.setTransform(dpr,0,0,dpr,0,0);drawIntroScene(ctx,w,h,introTime);
      introUi.hidden=false;const caption=introCaption(introTime);if(introText.textContent!==caption)introText.textContent=caption;
    }else{introUi.hidden=true;draw(client, canvas, stage, guards);}
    endingPanel.hidden=!client.data.ending||endingPreludeActive(client)||finaleGate(client.data);
    parentElement.querySelector('.pt-game').classList.toggle('is-complete',Boolean(client.data.ending));
    fullscreenButton.textContent=document.fullscreenElement?'Exit fullscreen':'Fullscreen ⛶';
    parentElement.querySelector('.pt-ready').textContent=client.data.ending?'Journey complete':'Keyboard ready';
    location.textContent = ZONE_NAMES[client.position.zone] || "Ship";
    parentElement.querySelector('.pt-stage-label').textContent=introTime!==null?'THE BEGINNING':client.data.ending?(client.data.finale&&client.data.finale.status!=='won'?'THE GUARDS ARE BACK':endingPreludeActive(client)?cinematicLabel(client):'EPILOGUE · FREEDOM'):`PIRATE SHIP · ${(ZONE_NAMES[client.position.zone] || 'SHIP').toUpperCase()}${client.feastStage==='asleep'||client.feastStage==='dozing'?` · CREW ASLEEP ${Math.floor(feastSecondsLeft(client.data)/60)}:${String(feastSecondsLeft(client.data)%60).padStart(2,'0')}`:''}`;
    inventory.classList.toggle("has-key", Boolean(client.data.has_key || client.data.has_blue_key || client.data.has_pistol || client.data.has_lamp));
    inventory.lastElementChild.textContent = [`🪙 ${client.data.story?.voyage?.coins||0}`,`♥ ${client.data.story?.voyage?.hp??2}`,client.data.has_key && "🗝️ Cell", client.data.has_blue_key && "🔵 Chest", client.data.has_pistol && "🔫 Pistol",client.data.has_lamp && "🏮 Lamp",client.data.story?.voyage?.captain_worn?"★ Captain":client.data.disguised && "🥼 Uniform"].filter(Boolean).join(" · ") || "Empty";
    inventoryPanel.hidden=!client.inventoryOpen || frozen;
    journalButton.disabled=Boolean(client.data.ending || client.data.reading || client.data.capture_phase!=="none");
    documentClose.disabled=client.actionInFlight;endingConfirm.disabled=client.actionInFlight;
    const itemNames={none:"Empty",cell_key:"🗝️ Cell key",blue_key:"🔵 Blue key",pistol:"🔫 Pistol",lamp:"🏮 Lamp"};
    inventoryPanel.querySelector(".pt-hand-slot strong").textContent=itemNames[client.data.held_item] || "Empty";
    inventoryPanel.querySelector(".pt-outfit-status").textContent="Outfit: "+(client.data.story?.voyage?.captain_worn?"Captain uniform":client.data.disguised?"Guard uniform":"Sailor");
    for(const button of itemButtons){
      const item=button.dataset.item;
      button.disabled=!(item==="cell_key"?client.data.has_key:item==="blue_key"?client.data.has_blue_key:item==="lamp"?client.data.has_lamp:client.data.has_pistol);
      button.classList.toggle("selected",client.data.held_item===item);
    }
    alertBanner.hidden=frozen || gameNow(client.data)>=Number(client.data.alert_until_ms);
    if(!alertBanner.hidden) alertSeconds.textContent=String(Math.ceil((client.data.alert_until_ms-gameNow(client.data))/1000));
    cutsceneBanner.hidden=!client.capture && !client.capturePending;
    if(frozen || client.capture || client.capturePending) setPrompt("");
    else if(client.data.hidden_barrel){
      const target=ambushTarget(client),occupied=Object.values(client.data.story?.voyage?.concealed||{}).includes(client.data.hidden_barrel);
      setPrompt(target?`E · Ambush ${client.data.roles[target[0]]||'crew member'} · F · Leave barrel`:occupied?'Body concealed · F · Leave barrel':'Wait for passing crew · E ambush · F leave');
    }
    else if(fAction()==='wardrobe')setPrompt(client.data.wardrobe_open?'F · Close wardrobe · E · Change clothes':'F · Open wardrobe');
    else if(client.position.zone==='hammock')setPrompt('F · Get up');
    else if(client.scope) setPrompt('');
    else if(storyPoint(client.position,client.data.rules)?.[1].kind==='telescope') setPrompt('F · Look through the telescope');
    else if(storyPoint(client.position,client.data.rules)?.[1].kind==='stew') setPrompt(client.data.story?.voyage?.stew_drugged?'The stew is drugged':(client.data.story?.items||[]).includes('sleeping_pills')?'F · Crush the sleeping pills into the stew':'F · Look at the stew pot');
    else if(storyPoint(client.position,client.data.rules,client.data)?.[1].kind==='cell_floor') setPrompt('F · Swallow the sleeping pills and lie down');
    else if(storyPoint(client.position,client.data.rules)?.[1].kind==='cannon') setPrompt(client.data.story?.voyage?.cannon_fired!==undefined?'The cannon is empty':client.data.has_lamp&&client.data.lamp_lit&&client.data.held_item==='lamp'?'F · Light the fuse and fire the cannon!':'Loaded cannon · hold a lit lamp to light the fuse');
    else if(storyPoint(client.position,client.data.rules,client.data)) {
      const [id,p]=storyPoint(client.position,client.data.rules,client.data);
      const owned=client.data.story?.items || [];
      setPrompt(p.item==='captain_uniform'&&owned.includes(p.item)&&!client.data.story?.voyage?.captain_worn?'E · Wear captain uniform':p.item && (client.data.story?.inspected || []).includes(id) && !owned.includes(p.item)
        ?`E · Take ${client.data.rules.story_items[p.item].name}${p.kind==='chest'?'':' · F inspect'}`
        :p.kind==='chest'?((client.data.story?.inspected || []).includes(id)?'Empty chest':`F · Open ${p.name}`):`F · ${p.name}`);
    }
    else if(client.data.hidden_barrel) setPrompt("");
    else if (canSteal(client, guard)) setPrompt("Press E to steal the key");
    else if(blueKeyPrompt(client))setPrompt(blueKeyPrompt(client));
    else if(fAction()==='hammock')setPrompt('F · Rest in upper hammock');
    else if (nearProp(client.position,client.data.rules.barrels,client.data.rules.barrel_range)) setPrompt("Press F to hide in the barrel");
    else if (nearProp(client.position,client.data.rules.crates,client.data.rules.crate_range)) {
      const crate=nearProp(client.position,client.data.rules.crates,client.data.rules.crate_range);
      setPrompt(crate[0]==="crate_hold_b"&&client.data.lamp_revealed&&!client.data.has_lamp
        ?"Press E to take the lamp · F searches the crate":(client.data.story?.voyage?.armed?"F · Hide in crate":"Press F to search the crate"));
    }
    else {
      const xy=positionXY(client.position,client.data.rules);
      const helper=[['Cook','dining',2],['Boatswain','boatswain',3]].find(([,kind])=>{const q=guardPose(client.data,kind);return client.data[kind+'_alive']&&Math.abs(q.x-xy.x)<65&&Math.abs(q.y-xy.y)<25;});
      const stair=Object.values(client.data.rules.stairs).find(([x1,y1,x2,y2])=>(xy.y===y1&&client.position.zone!=='cell'&&xy.x>=x1-45&&xy.x<=x2+20)||(xy.y===y2&&xy.x>=x1-20&&xy.x<=x2+45));
      setPrompt(helper?`T · Bribe ${helper[0]} · ${helper[2]} coins`:'');
    }
    feedback.hidden = Boolean(client.data.ending || client.data.reading) || !client.flashText || now >= client.flashUntil;
    if (!feedback.hidden) feedback.textContent = client.flashText;
    documentPanel.querySelector(".pt-document-feedback").textContent=client.data.reading?client.flashText:"";
    raf = requestAnimationFrame(frame);
  }

  window.addEventListener("keydown", onKeyDown, true);
  window.addEventListener("keyup", onKeyUp, true);
  window.addEventListener("blur", onBlur);
  stage.addEventListener("pointerdown", onPointerDown);
  raf = requestAnimationFrame(frame);
  const cleanup = () => {
    cancelAnimationFrame(raf);
    window.removeEventListener("keydown", onKeyDown, true);
    window.removeEventListener("keyup", onKeyUp, true);
    window.removeEventListener("blur", onBlur);
    stage.removeEventListener("pointerdown", onPointerDown);
    itemButtons.forEach(button=>button.removeEventListener("click",onItemClick));
    documentPanel.removeEventListener("keydown",trapDocumentFocus);
    documentClose.removeEventListener("click",closeDocument);
    endingConfirm.removeEventListener("click",confirmEnding);
    introSkip.removeEventListener('click',skipIntro);
    introMusicButton.removeEventListener('click',toggleMusic);
    journalButton.removeEventListener("click",openJournal);
    replayScene.removeEventListener("click",replay);
    finaleRetryButton.removeEventListener('click',finaleRetry);
    fullscreenButton.removeEventListener("click",toggleFullscreen);
    restartButton.removeEventListener('click',restartPrompt);musicButton.removeEventListener('click',toggleMusic);volume.removeEventListener('input',changeVolume);
    if (parentElement.__teamPlotTwistCleanup === cleanup) parentElement.__teamPlotTwistCleanup = null;
  };
  parentElement.__teamPlotTwistCleanup = cleanup;
  return cleanup;
}

function renderStoryPanels(parent,client) {
  const d=client.data,s=d.story;
  if(!s) return; // Old component protocol is still supported by regression tests.
  const panel=parent.querySelector('.pt-document-panel');
  const reading=client.restartPrompt?'restart_confirm':d.reading;
  panel.hidden=!reading;
  const confirm=['restart_confirm','confirm_crate','confirm_takeover','confirm_dinghy','confirm_castaway'].includes(reading);
  const doc=d.documents[reading];
  panel.querySelector('.pt-document-kicker').textContent=doc?.kicker || 'YOUR DISCOVERIES';
  panel.querySelector('.pt-document-title').textContent=doc?.title || 'Journal';
  panel.querySelector('.pt-document-body').textContent=doc?.body || 'Notes from your journey. Only discoveries you have made appear here.';
  let hint=doc?.hint || '';
  if(d.reading==='return_crate' || d.reading==='journal' && (s.inspected.includes('return_crate')||s.inspected.includes('manifest_desk'))) {
    const check=(yes,text)=>(yes?'✓ ':'○ ')+text;
    hint=[check(s.crate_open,'Open crate 07 with the crowbar or pay the cook two coins'),d.dining_alive?'✓ The cook is alive':'× The cook is dead'].join('\n');
  }
  panel.querySelector('.pt-document-hint').textContent=hint;
  const entries=panel.querySelector('.pt-journal-entries');
  entries.replaceChildren();
  if(d.reading==='journal') {
    for(const id of s.inspected) {
      const known=d.documents[id];if(!known || d.rules.story_points[id]?.kind==='chest') continue;
      const detail=document.createElement('details'), summary=document.createElement('summary'),p=document.createElement('p');
      summary.textContent=known.title;p.textContent=known.body;
      detail.append(summary,p);entries.append(detail);
    }
    if(!s.inspected.length) {
      const p=document.createElement('p');p.textContent='No clues yet. Look for the letter by the bed in the cell.';entries.append(p);
    }
  }
  const close=panel.querySelector('.pt-document-close');
  close.textContent=reading==='restart_confirm'?'Keep playing · F':confirm?'Keep exploring · F':'Back to the ship · F';
  const yes=panel.querySelector('.pt-ending-confirm');
  yes.hidden=!confirm;yes.textContent=reading==='restart_confirm'?'Restart game':d.reading==='confirm_castaway'?'Swallow the pills':d.reading==='confirm_dinghy'?'Lower the dinghy':d.reading==='confirm_takeover'?'Take over the ship':'Climb in and escape';
  if(reading) close.focus({preventScroll:true});
  const storyInventory=parent.querySelector('.pt-story-inventory');
  storyInventory.replaceChildren();
  for(const id of s.items) {
    const item=d.rules.story_items[id],node=document.createElement('div'),use=document.createElement('small');
    node.className='pt-story-item';node.textContent=item.icon+' '+item.name;
    use.textContent=item.use;node.append(use);storyInventory.append(node);
  }
  const end=parent.querySelector('.pt-ending-panel');end.hidden=!d.ending || endingPreludeActive(client) || finaleGate(d);
  if(d.ending) {
    const e=d.endings[d.ending];
    end.querySelector('.pt-ending-kicker').textContent=e.subtitle;
    end.querySelector('.pt-ending-title').textContent=e.title;
    end.querySelector('.pt-ending-body').textContent=e.body;
    const deaths=Number(!d.sleeper_alive)+Object.keys(d.guard_routes).filter(k=>!d[k+'_alive']).length;
    end.querySelector('.pt-ending-detail').textContent=(deaths===0?'You escaped without taking a life.':`${deaths} crew members did not survive the journey.`)+` You found ${s.inspected.length} clues and ${s.items.length} new items.`;
  }
}

function drawChestItem(ctx,item,x,y) {
  ctx.save();ctx.translate(x,y);
  if(item==='captain_uniform'){roundBox(ctx,-15,-14,30,29,3,'#b79545','#4a3924');line(ctx,-9,-12,-3,12,'#f0dca2',3);label(ctx,'★',3,4,14);}
  else if(item==='sail'){ctx.fillStyle='#f0dcab';ctx.beginPath();ctx.moveTo(-18,7);ctx.lineTo(-9,-12);ctx.lineTo(20,5);ctx.closePath();ctx.fill();line(ctx,-16,6,15,6,'#9e8153',2);}
  else if(item==='crowbar') {
    line(ctx,-18,7,12,-12,'#252d32',7);line(ctx,12,-12,18,-8,'#252d32',7);
    line(ctx,-18,7,-21,1,'#252d32',6);line(ctx,-15,4,11,-10,'#aab8bb',2);
  } else if(item==='rope') {
    ctx.strokeStyle='#dbbd83';ctx.lineWidth=4;
    for(let i=0;i<3;i++){ctx.beginPath();ctx.ellipse(-8+i*8,-1,9,6,0,0,Math.PI*2);ctx.stroke();}
  } else if(item==='whistle') {
    roundBox(ctx,-12,-8,20,13,4,'#d6b359','#715b2f');line(ctx,8,-3,19,-3,'#d6b359',6);
    ctx.fillStyle='#292e2e';ctx.fillRect(-5,-7,5,4);
  } else if(item==='sleeping_pills') {
    roundBox(ctx,-7,-14,14,22,4,'#7a4a24','#3b2412');roundBox(ctx,-5,-19,10,6,2,'#e8e2d2','#77705f');
    roundBox(ctx,-6,-7,12,8,1,'#efe2bd','#8a7a55');ctx.fillStyle='#d24b4b';ctx.fillRect(-3,-5,6,4);
  } else if(item==='seal') {
    roundBox(ctx,-12,0,24,7,2,'#b88f48','#56452e');line(ctx,0,0,0,-12,'#b88f48',8);
  }
  ctx.restore();
}

// The brass telescope in the crow's nest and the view through it.
function drawTelescope(ctx,x,y) {
  line(ctx,x-7,y,x,y-17,'#5b4330',3);line(ctx,x+7,y,x,y-17,'#5b4330',3);
  ctx.save();ctx.translate(x,y-19);ctx.rotate(-.32);
  roundBox(ctx,-4,-4,30,8,3,'#c39a52','#5c4426');roundBox(ctx,-12,-3,9,6,2,'#9c7a41','#5c4426');
  line(ctx,8,-4,8,4,'#7b5d33',2);ctx.restore();
}
const SCOPE_WIDTH=3000;
const SCOPE_SIGHTS=[
  {x:300,id:'whale',text:'A whale blows a fountain of spray far out at sea.'},
  {x:850,id:'island',text:'A small island with palm trees and a white beach. No smoke, no boats. Nobody lives there.'},
  {x:1650,id:'coast',text:'The coast. A harbour town with a fort and a lighthouse. The ship docks there tomorrow.'},
  {x:2450,id:'frigate',text:'A navy frigate patrols near the coast, flying the king’s colours.'},
];
function scopeWrap(dx){return ((dx%SCOPE_WIDTH)+SCOPE_WIDTH*1.5)%SCOPE_WIDTH-SCOPE_WIDTH/2;}
function scopeCaption(pan) {
  const near=SCOPE_SIGHTS.map(s=>({...s,d:Math.abs(scopeWrap(s.x-pan))})).sort((a,b)=>a.d-b.d)[0];
  return near.d<260?near.text:'Open sea in every direction.';
}
function drawScopeSight(ctx,id,x,y,t) {
  if(id==='whale'){ctx.fillStyle='#22343c';ctx.beginPath();ctx.ellipse(x,y+4,46,9,0,Math.PI,0);ctx.fill();
    const f=(t*0.6)%1;ctx.fillStyle=`rgba(235,245,250,${.8*(1-f)})`;for(const s of [-1,0,1]){ctx.beginPath();ctx.arc(x-20+s*9*f,y-14-34*f,5+6*f,0,Math.PI*2);ctx.fill();}}
  else if(id==='island'){ctx.fillStyle='#e6d29c';ctx.beginPath();ctx.ellipse(x,y+3,150,18,0,Math.PI,0);ctx.fill();
    ctx.fillStyle='#4f7a3e';ctx.beginPath();ctx.ellipse(x+10,y-6,95,24,0,Math.PI,0);ctx.fill();
    for(const [px,h,lean] of [[-40,78,-.18],[25,92,.12],[70,64,.25]]){ctx.save();ctx.translate(x+px,y-10);ctx.rotate(lean);
      line(ctx,0,0,4,-h,'#6b4d30',6);for(let i=0;i<5;i++){const a=-Math.PI*.95+i*Math.PI*.24+Math.sin(t*1.6+i)*.05;line(ctx,4,-h,4+Math.cos(a)*38,-h+Math.sin(a)*14+16,'#2f6b34',5);}ctx.restore();}}
  else if(id==='coast'){ctx.fillStyle='#6f7f62';ctx.beginPath();ctx.moveTo(x-420,y);ctx.lineTo(x-300,y-40);ctx.lineTo(x-120,y-58);ctx.lineTo(x+90,y-35);ctx.lineTo(x+420,y-48);ctx.lineTo(x+430,y);ctx.fill();
    for(let i=0;i<9;i++){const bx=x-150+i*30,bh=18+(i*37%25);roundBox(ctx,bx,y-bh-6,24,bh,2,i%2?'#d8c3a0':'#c7a07a','#6a5642');ctx.fillStyle='#8e4a3a';ctx.beginPath();ctx.moveTo(bx-2,y-bh-6);ctx.lineTo(bx+12,y-bh-18);ctx.lineTo(bx+26,y-bh-6);ctx.fill();}
    roundBox(ctx,x+150,y-52,46,46,2,'#8f8a7d','#4d4a43');for(let i=0;i<4;i++)ctx.fillRect(x+150+i*13,y-60,8,9);
    roundBox(ctx,x+290,y-110,18,104,3,'#ece6da','#7a7166');ctx.fillStyle='#b44a3a';ctx.fillRect(x+290,y-80,18,12);ctx.fillRect(x+290,y-48,18,12);
    ctx.fillStyle=`rgba(255,226,140,${.55+.45*Math.sin(t*3)})`;ctx.beginPath();ctx.arc(x+299,y-116,7,0,Math.PI*2);ctx.fill();}
  else if(id==='frigate'){const sx=x+Math.sin(t*.15)*60;ctx.fillStyle='#2c2b2a';ctx.beginPath();ctx.moveTo(sx-90,y-12);ctx.lineTo(sx+95,y-12);ctx.lineTo(sx+75,y+4);ctx.lineTo(sx-78,y+4);ctx.fill();
    line(ctx,sx-80,y-8,sx+88,y-8,'#d9c27b',2);for(let i=0;i<6;i++)ctx.fillRect(sx-62+i*24,y-6,6,4);
    for(const [mx,h] of [[-45,95],[5,120],[55,90]]){line(ctx,sx+mx,y-12,sx+mx,y-12-h,'#3a3029',3);for(const k of [.3,.62]){ctx.fillStyle='#f2ead8';ctx.fillRect(sx+mx-22,y-12-h*k-18,44,22);}}
    ctx.fillStyle='#2c4f9c';ctx.fillRect(sx+5,y-140,22,13);line(ctx,sx+5,y-133,sx+27,y-133,'#f2ead8',2);}
}
function drawScope(ctx,w,h,pan,now) {
  const t=now/1000,cx=w/2,cy=h*.47,r=Math.min(w*.44,h*.43);
  ctx.fillStyle='#07090b';ctx.fillRect(0,0,w,h);
  ctx.save();ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.clip();
  ctx.translate(cx,cy);ctx.rotate(Math.sin(t*.9)*.025);ctx.translate(0,Math.sin(t*1.3)*4);
  const horizon=18,sky=ctx.createLinearGradient(0,-r,0,horizon);sky.addColorStop(0,'#6fa6c7');sky.addColorStop(1,'#d9e7e4');
  ctx.fillStyle=sky;ctx.fillRect(-r*1.2,-r*1.2,r*2.4,r*1.2+horizon);
  ctx.fillStyle='#2f6f86';ctx.fillRect(-r*1.2,horizon,r*2.4,r*1.3);
  ctx.fillStyle='rgba(255,255,255,.55)';for(let i=0;i<5;i++){const x=scopeWrap(i*640+120-pan*.4)*.5;ctx.beginPath();ctx.ellipse(x,-r*.55+(i%2)*30,70,13,0,0,Math.PI*2);ctx.fill();}
  for(const s of SCOPE_SIGHTS){const x=scopeWrap(s.x-pan);if(Math.abs(x)<r+500)drawScopeSight(ctx,s.id,x,horizon,t);}
  ctx.strokeStyle='rgba(225,240,240,.45)';ctx.lineWidth=2;
  for(let row=1;row<9;row++){const y=horizon+row*row*4.5;ctx.beginPath();for(let x=-r;x<=r;x+=10){const yy=y+Math.sin(x*.03+t*1.4+row-pan*.03)*(1+row*.3);x===-r?ctx.moveTo(x,yy):ctx.lineTo(x,yy);}ctx.stroke();}
  for(let i=0;i<3;i++){const gx=scopeWrap(i*900+400-pan+t*25)*.9,gy=-r*.3+i*25+Math.sin(t*2+i)*6;line(ctx,gx-9,gy,gx,gy+4,'#2b2b2b',2);line(ctx,gx,gy+4,gx+9,gy,'#2b2b2b',2);}
  ctx.restore();
  const vignette=ctx.createRadialGradient(cx,cy,r*.62,cx,cy,r);vignette.addColorStop(0,'rgba(0,0,0,0)');vignette.addColorStop(1,'rgba(0,0,0,.75)');
  ctx.fillStyle=vignette;ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.fill();
  ctx.strokeStyle='#b8893f';ctx.lineWidth=10;ctx.beginPath();ctx.arc(cx,cy,r+5,0,Math.PI*2);ctx.stroke();
  ctx.strokeStyle='#5d4421';ctx.lineWidth=3;ctx.beginPath();ctx.arc(cx,cy,r+11,0,Math.PI*2);ctx.stroke();
  ctx.save();ctx.textAlign='center';ctx.font='600 16px system-ui';ctx.fillStyle='#f6e7c4';
  ctx.fillText(scopeCaption(pan),cx,Math.min(h-34,cy+r+34));
  ctx.font='13px system-ui';ctx.fillStyle='#bba98a';ctx.fillText('A / D · look around      F · put the telescope away',cx,Math.min(h-12,cy+r+56));ctx.restore();
}
// A loaded deck cannon aimed over the bow. Lit with a lamp it hisses, fires,
// kicks back on its carriage and leaves a drifting cloud of smoke.
function cannonMotion(age) {
  const s=age/1000;
  return {
    fuse:age<0,
    flash:age>=0&&age<160,
    recoil:age<0?0:age<120?22*age/120:22*Math.max(0,1-(age-120)/1500),
    ball:age>=0&&s<1.8?{dx:-30-620*s,dy:-26-150*s+260*s*s}:null,
    smoke:age>=0&&s<6?Array.from({length:6},(_,i)=>({dx:-40-i*14-s*(18+i*7),dy:-34-i*3-s*(10+i*4),r:6+i*2+s*(10+i*3),a:Math.max(0,.75-s*.13)*(1-i*.08)})):[],
    boom:age>=0&&age<1100,
    shake:age>=0&&age<600?7*(1-age/600):0,
  };
}
function drawCannon(ctx,x,y,firedAt,now) {
  const age=firedAt===undefined?null:now-firedAt,m=age===null?cannonMotion(-1e9):cannonMotion(age);
  if(age===null){m.fuse=false;}
  const cx=x+m.recoil;
  // Shot rack and powder bucket stay put.
  ctx.fillStyle='#2b2d2f';for(const [bx,by] of [[x+40,y-5],[x+52,y-5],[x+46,y-15]]){ctx.beginPath();ctx.arc(bx,by,5.5,0,Math.PI*2);ctx.fill();}
  roundBox(ctx,x+60,y-16,14,16,2,'#6c4a2f','#3a281c');
  // Carriage, wheels and iron barrel.
  roundBox(ctx,cx-22,y-22,46,13,2,'#6f4a2e','#3a281c');
  for(const wx of [cx-14,cx+14]){ctx.fillStyle='#4b3223';ctx.beginPath();ctx.arc(wx,y-6,6.5,0,Math.PI*2);ctx.fill();ctx.fillStyle='#b18452';ctx.beginPath();ctx.arc(wx,y-6,2,0,Math.PI*2);ctx.fill();}
  ctx.save();ctx.translate(cx+6,y-24);ctx.rotate(-.12);
  ctx.fillStyle='#2d3133';ctx.beginPath();ctx.moveTo(14,-8);ctx.lineTo(-44,-6);ctx.lineTo(-44,6);ctx.lineTo(14,8);ctx.closePath();ctx.fill();
  ctx.beginPath();ctx.arc(15,0,8,0,Math.PI*2);ctx.fill();
  roundBox(ctx,-48,-8,7,16,2,'#3b4043','#202426');line(ctx,-20,-7,-20,7,'#4c5357',3);line(ctx,2,-8,2,8,'#4c5357',3);
  if(m.fuse){const f=(age%200)/200;ctx.fillStyle=`rgba(255,${180+60*f},90,1)`;ctx.beginPath();ctx.arc(8,-10-3*f,2.5+2*f,0,Math.PI*2);ctx.fill();}
  if(m.flash){ctx.fillStyle='rgba(255,235,160,.95)';ctx.beginPath();ctx.ellipse(-62,0,22,13,0,0,Math.PI*2);ctx.fill();ctx.fillStyle='rgba(255,140,60,.8)';ctx.beginPath();ctx.ellipse(-56,0,12,8,0,0,Math.PI*2);ctx.fill();}
  ctx.restore();
  for(const p of m.smoke){ctx.fillStyle=`rgba(225,222,214,${p.a})`;ctx.beginPath();ctx.arc(x+p.dx,y-30+p.dy,p.r,0,Math.PI*2);ctx.fill();}
  if(m.ball){ctx.fillStyle='#1d1f20';ctx.beginPath();ctx.arc(x+m.ball.dx,y-30+m.ball.dy,4.5,0,Math.PI*2);ctx.fill();}
  if(m.fuse)label(ctx,'tsssss…',x-6,y-52,10);
  if(m.boom){ctx.save();ctx.globalAlpha=Math.max(0,1-age/1100);label(ctx,'BOOM!',x-70,y-70-age/40,30);ctx.restore();}
  label(ctx,age===null||age<0?'CANNON':'EMPTY CANNON',x-28,y-60,9);
}
function storyDecor(ctx,d) {
  const s=d.story || {items:[],inspected:[]};
  for(const [id,p] of Object.entries(d.rules.story_points || {})) {
    const y=p.zone==='mast_top'?d.rules.mast_top_y:d.rules.floors[p.zone][2],x=p.x;
    if(p.kind==='telescope'){drawTelescope(ctx,x,y);continue;}
    if(p.kind==='cannon'){drawCannon(ctx,x,y,s.voyage?.cannon_fired,gameNow(d));continue;}
    if(p.kind==='coins'){crate(ctx,x-20,y,40,27);if(!(s.voyage?.claimed||[]).includes(id)){ctx.fillStyle='#efc24c';ctx.beginPath();ctx.arc(x,y-35,7,0,Math.PI*2);ctx.fill();}label(ctx,'COINS',x-21,y-49,9);}
    else if(p.kind==='chest') {
      roundBox(ctx,x-25,y-32,50,30,4,'#536e68','#1f3835');
      const opened=s.inspected.includes(id);
      roundBox(ctx,x-27,y-(opened?49:40),54,10,3,'#9ea581','#3d5145');
      line(ctx,x-14,y-31,x-14,y-3,'#d8b271',3);line(ctx,x+14,y-31,x+14,y-3,'#d8b271',3);
      if(opened && !s.items.includes(p.item)) drawChestItem(ctx,p.item,x,y-18);
      label(ctx,opened&&s.items.includes(p.item)?'TAKEN':p.name.toUpperCase(),x-39,y-60,9);
    } else if(p.kind==='document') {
      roundBox(ctx,x-17,y-26,34,23,2,'#ebd7a6','#705937');
      for(let i=0;i<3;i++) line(ctx,x-10,y-20+i*5,x+10,y-20+i*5,'#8b7a55',1);
      label(ctx,id==='opening_letter'?'LETTER':id==='manifest_desk'?'MANIFEST':'JOURNAL',x-29,y-35,9);
    } else if(p.kind==='window') {
      roundBox(ctx,x-26,y-81,52,38,13,'#5995a2','#dbbb7c');
      line(ctx,x-22,y-62,x+22,y-62,'#d7bb83',3);line(ctx,x,y-78,x,y-46,'#d7bb83',3);
      label(ctx,'VIEW',x-19,y-90,9);
    } else if(p.kind==='return_crate') {
      crate(ctx,x-35,y,70,51);
      line(ctx,x-35,y-(s.crate_open?66:53),x+35,y-(s.crate_open?66:53),'#d8b580',6);
      roundBox(ctx,x-16,y-39,32,22,2,'#e6d1a5','#68543d');
      label(ctx,'07',x-9,y-23,14);
      if(s.crate_marked){ctx.strokeStyle='#984c3b';ctx.lineWidth=3;ctx.beginPath();ctx.arc(x+21,y-30,9,0,Math.PI*2);ctx.stroke();}
      label(ctx,s.crate_marked?'READY FOR SHORE':'RETURN CRATE',x-40,y-79,9);
    } else if(p.kind==='helm') {
      roundBox(ctx,x-12,y-35,24,34,3,'#76523b','#382b25');
      label(ctx,'HELM',x-23,y-93,10);
    }
  }
  // Davits, suspended boat and a winch give the next escape route a physical home.
  const bx=1660;
  for(const x of [bx-65,bx+65]) {
    line(ctx,x,245,x,180,'#514b3c',7);line(ctx,x,180,x+17,167,'#514b3c',7);
    line(ctx,x+17,167,x+17,298,'#d6bb82',2);
  }
  ctx.fillStyle='#9a633f';ctx.strokeStyle='#3c3027';ctx.lineWidth=3;
  ctx.beginPath();ctx.moveTo(bx-76,297);ctx.quadraticCurveTo(bx,350,bx+82,297);ctx.closePath();ctx.fill();ctx.stroke();
  line(ctx,bx-58,302,bx+60,302,'#e1bb7d',4);
  for(const x of [bx-30,bx,bx+30]) line(ctx,x,300,x,314,'#4e3829',4);
  roundBox(ctx,bx-16,218,32,22,3,'#676b58','#393e35');
  label(ctx,'DINGHY',bx-33,360,10);
}

const CRATE_NIGHT_SECONDS=8;
const CASTAWAY_SECONDS = 32;
const CASTAWAY_CELL_SECONDS = 5;
const CASTAWAY_DRIFT_START = 9;
const CASTAWAY_DAY_SECONDS = 4;
const CASTAWAY_SHORE_START = CASTAWAY_DRIFT_START + 4 * CASTAWAY_DAY_SECONDS;

function endingPreludeActive(client) {
  const t=(performance.now()-client.endingStartedAt)/1000;
  const reduced=typeof matchMedia==='function'&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  if(client.data.ending==='free')return !reduced&&t<RESCUE_SECONDS;
  return client.data.ending==='crate'?t<CRATE_NIGHT_SECONDS+16:!reduced&&t<(client.data.ending==='dinghy'?21:client.data.ending==='command'?24:client.data.ending==='castaway'?CASTAWAY_SECONDS:12);
}
function cinematicLabel(client) {
  const t=(performance.now()-client.endingStartedAt)/1000;
  if(client.data.ending==='free')return t<4?'A SMALL BOAT AT LAST':'FREE AT LAST';
  if(client.data.ending==='castaway'){const m=castawayMotion(1000,560,t);return m.phase==='cell'?(m.found?'THE GUARDS FIND YOU':'THE COLD FLOOR OF THE CELL'):m.phase==='overboard'?'OVER THE SIDE':m.phase==='adrift'?`ADRIFT · DAY ${m.day} OF 4`:'AT THE WATER’S EDGE';}
  if(client.data.ending==='lullaby')return 'THE CREW SLEEPS · THE HELM IS YOURS';
  return client.data.ending==='command'?'A CAPTAIN BY DECEPTION · HEADING HOME':client.data.ending==='crate'?(t<CRATE_NIGHT_SECONDS?'NIGHTFALL · WAITING FOR DAWN':'DAWN · THE RETURN DELIVERY'):client.data.ending==='dinghy'?'LOWERING THE DINGHY · FREEDOM AWAITS':'THE HELM IS YOURS · SETTING SAIL';
}
function cinematicShip(ctx,cx,water,width,{night=0,davits=false,player=false,crate07=false,sails=1,captain=false}={}) {
  // Match the playable ship's hull vertices, long three-deck body and mast position.
  const scale=width/2565;
  ctx.save();ctx.translate(cx,water);ctx.scale(scale,scale);ctx.translate(-1387.5,-558);
  const hull=()=>{ctx.beginPath();ctx.moveTo(105,208);ctx.lineTo(2550,175);ctx.lineTo(2670,320);ctx.lineTo(2600,520);ctx.quadraticCurveTo(2570,558,2450,558);ctx.lineTo(240,558);ctx.quadraticCurveTo(150,550,115,475);ctx.closePath();};
  hull();ctx.fillStyle='#493126';ctx.fill();ctx.strokeStyle='#251f1c';ctx.lineWidth=8;ctx.stroke();
  ctx.save();hull();ctx.clip();
  for(let y=220;y<560;y+=25)line(ctx,90,y,2700,y,'#674732',3);
  for(const y of [245,365,500]){line(ctx,145,y,2580,y,'#211e1b',13);line(ctx,145,y-5,2580,y-5,'#c99a62',5);}
  for(const y of [298,420,520])for(let x=230;x<2540;x+=145){
    roundBox(ctx,x,y-32,51,38,12,night?'#ffe0a0':'#203c43','#c5a16b');
    line(ctx,x+25,y-31,x+25,y+4,'#8b6e4b',3);
  }
  ctx.restore();
  roundBox(ctx,2300,111,262,87,6,'#73533b','#2c241e');
  for(const x of [2340,2435,2520])roundBox(ctx,x,135,34,35,8,night?'#ffe0a0':'#34545b','#cfb479');
  line(ctx,120,207,2620,196,'#d1a06a',9);
  for(let x=140;x<2610;x+=38)line(ctx,x,201,x,239,'#664630',4);
  line(ctx,760,-270,760,241,'#5d3c29',17);line(ctx,760,-270,760,241,'#ae8255',5);
  line(ctx,465,-145,1050,-145,'#563927',14);
  ctx.save();ctx.translate(760,-137);ctx.scale(1,Math.max(.015,sails));ctx.translate(-760,137);ctx.fillStyle='#ead5a4';ctx.beginPath();ctx.moveTo(480,-137);ctx.quadraticCurveTo(760,-100,1035,-137);ctx.lineTo(997,110);ctx.quadraticCurveTo(760,170,518,110);ctx.closePath();ctx.fill();ctx.restore();
  line(ctx,760,-245,260,204,'#978363',3);line(ctx,760,-245,1450,202,'#978363',3);
  ctx.fillStyle='#20292c';ctx.beginPath();ctx.moveTo(765,-265);ctx.lineTo(970,-237);ctx.lineTo(765,-204);ctx.fill();
  ctx.fillStyle='#f0e5c9';ctx.beginPath();ctx.arc(822,-237,15,0,Math.PI*2);ctx.fill();line(ctx,807,-220,840,-210,'#f0e5c9',5);line(ctx,840,-220,807,-210,'#f0e5c9',5);
  for(const x of [400,620,1000,1350,1800,2150])roundBox(ctx,x,181,55,25,5,'#514b3b','#c3a16c');
  line(ctx,1980,200,1980,155,'#8c6642',8);ctx.strokeStyle='#d6b978';ctx.lineWidth=5;ctx.beginPath();ctx.arc(1980,145,28,0,Math.PI*2);ctx.stroke();
  if(player)person(ctx,1925,200,false,0,'none','right',false,captain,'officer',captain?{color:'#b79545',badge:'★'}:null);
  if(crate07){crate(ctx,1225,200,80,60);label(ctx,'07',1248,183,28);}
  if(davits)for(const x of [1570,1750]){line(ctx,x,245,x,120,'#938465',12);line(ctx,x,120,x+30,90,'#938465',12);}
  ctx.restore();
  return {scale,point:(x,y)=>({x:cx+(x-1387.5)*scale,y:water+(y-558)*scale})};
}
function drawCratePrelude(ctx,w,h,t) {
  const night=clamp(t/2,0,1),dawn=clamp((t-6)/2,0,1);
  const mix=(a,b,f)=>a.map((x,i)=>Math.round(x+(b[i]-x)*f));
  const color=(dusk,dark,day)=>`rgb(${mix(mix(dusk,dark,night),day,dawn).join(',')})`;
  const sky=ctx.createLinearGradient(0,0,0,h);
  sky.addColorStop(0,color([100,74,96],[7,15,39],[103,163,184]));sky.addColorStop(1,color([223,151,95],[22,40,64],[244,195,129]));ctx.fillStyle=sky;ctx.fillRect(0,0,w,h);
  ctx.save();ctx.globalAlpha=night*(1-dawn);ctx.fillStyle='#fff0c5';
  for(let i=0;i<70;i++){const x=((i*137+71)%997)/997*w,y=((i*73+29)%431)/431*h*.6;ctx.beginPath();ctx.arc(x,y,i%4===0?2:1,0,Math.PI*2);ctx.fill();}
  ctx.beginPath();ctx.arc(w*.82,h*.18,22,0,Math.PI*2);ctx.fill();ctx.restore();
  if(dawn){ctx.save();ctx.globalAlpha=dawn;ctx.fillStyle='#ffe1a3';ctx.beginPath();ctx.arc(w*.8,h*(.63-dawn*.16),34,0,Math.PI*2);ctx.fill();ctx.restore();}
  ctx.fillStyle=color([39,64,81],[9,23,44],[54,113,129]);ctx.fillRect(0,h*.6,w,h*.4);
  cinematicShip(ctx,w*.5,h*.77,w*.9,{night:night*(1-dawn),crate07:true});
  for(let i=0;i<6;i++)line(ctx,w*.1+i*91,h*.8+i*9,w*.22+i*91,h*.8+i*9,'rgba(240,219,174,.25)',2);
  ctx.fillStyle='#fff0d2';ctx.font='600 18px system-ui';ctx.textAlign='center';ctx.fillText(t<2?'You settle inside crate 07…':t<6?'Night passes over the pirate ship…':'First light. The delivery is coming…',w/2,h*.93);ctx.textAlign='start';
}
function dinghyMotion(w,h,t) {
  const horizon=h*.34,water=h*.7,unit=Math.min(w/1000,h/540)*.9,shipX=w*.43,shipWidth=w*.76;
  const scale=shipWidth/2565,dock={x:shipX+(1660-1387.5)*scale,y:water+(245-558)*scale};
  const bow=shipX+(2670-1387.5)*scale,clearX=bow+70*unit+20,foreground=h*.87;
  const lower=clamp(t/4,0,1),sail=clamp((t-4)/2,0,1),along=clamp((t-6)/5,0,1),away=clamp((t-11)/10,0,1);
  return {x:dock.x+(clearX-dock.x)*along+(w*.96-clearX)*away,y:dock.y+(foreground-dock.y)*lower-away*(foreground-horizon-12),scale:unit*(1-away*.93),lower,sail,along,away,bow,clearX,horizon,water,shipX,shipWidth};
}
function drawDinghyEscape(ctx,w,h,t,client) {
  const m=dinghyMotion(w,h,t),sky=ctx.createLinearGradient(0,0,0,h);sky.addColorStop(0,'#304e6c');sky.addColorStop(.55,'#e4b28b');sky.addColorStop(1,'#f2d8ac');ctx.fillStyle=sky;ctx.fillRect(0,0,w,h);
  ctx.fillStyle='#ffe3a1';ctx.beginPath();ctx.arc(w*.85,m.horizon-18,29,0,Math.PI*2);ctx.fill();ctx.fillStyle='#366c7b';ctx.fillRect(0,m.horizon,w,h-m.horizon);
  const ship=cinematicShip(ctx,m.shipX,m.water,m.shipWidth,{davits:true});
  if(t<4.15)for(const x of [1570,1750]){const p=ship.point(x+30,90);line(ctx,p.x,p.y,p.x,m.y,'#dac598',2);}
  ctx.save();ctx.translate(m.x,m.y);ctx.scale(m.scale,m.scale);
  ctx.save();ctx.translate(-14,2);ctx.scale(.65,.65);person(ctx,0,0,false,0,'none','right',false,client.data.disguised);ctx.restore();
  ctx.fillStyle='#8c5d3c';ctx.beginPath();ctx.moveTo(-60,-2);ctx.quadraticCurveTo(0,12,60,-2);ctx.lineTo(42,23);ctx.quadraticCurveTo(0,36,-42,23);ctx.closePath();ctx.fill();line(ctx,-59,-2,59,-2,'#e1bc82',4);line(ctx,9,-5,9,-82*m.sail-5,'#654a32',4);
  if(m.sail>0){ctx.fillStyle='#f2dfb2';ctx.beginPath();ctx.moveTo(14,-80*m.sail);ctx.quadraticCurveTo(47,-40*m.sail,59,-8);ctx.lineTo(14,-8);ctx.closePath();ctx.fill();}ctx.restore();
  for(let i=0;i<11;i++){const y=m.horizon+13+i*i*2.5;line(ctx,(i*109%Math.max(w-80,1)),y,(i*109%Math.max(w-80,1))+70,y,'rgba(231,213,171,.3)',2);}
  if(t<21){ctx.save();ctx.textAlign='center';ctx.font='600 17px system-ui';ctx.fillStyle='#fff1cf';ctx.fillText(t<4?'Slowly, you lower the dinghy…':t<6?'The hull touches water. You hoist the sail…':t<11?'You steer along the hull and around the bow…':'A fair wind carries you towards the horizon.',w/2,h*.96);ctx.restore();}
}
function crateDeliveryMotion(w,h,t) {
  const top={x:w*.53,y:h*.5},bottom={x:w*.68,y:h*.78},drop={x:w*.7,y:h*.78};
  const lerp=(a,b,f)=>({x:a.x+(b.x-a.x)*f,y:a.y+(b.y-a.y)*f});
  let cook=t<4?lerp(top,bottom,clamp(t/4,0,1)):t<5?lerp(bottom,drop,t-4):t<6?lerp(drop,bottom,t-5):lerp(bottom,top,clamp((t-6)/4,0,1));
  const crate=t<5?{x:cook.x+34,y:cook.y-15+15*clamp(t-4,0,1)}:{x:drop.x+34,y:drop.y};
  return {top,bottom,drop,cook,crate,returning:t>=5,aboard:t>=10};
}
function drawCrateDelivery(ctx,w,h,t) {
  cinematicShip(ctx,w*.46,h*.6,w*.87,{});
  const m=crateDeliveryMotion(w,h,t),ground=h*.78;
  ctx.fillStyle='#756452';ctx.fillRect(0,ground,w,17);for(let x=30;x<w;x+=140)line(ctx,x,ground+17,x,h,'#4b4034',11);
  ctx.fillStyle='#756957';ctx.fillRect(w*.77,h*.4,w*.22,ground-h*.4);ctx.fillStyle='#453c34';ctx.fillRect(w*.82,ground-72,60,72);
  line(ctx,w*.75,h*.4,w*.88,h*.29,'#544d43',8);line(ctx,w*.88,h*.29,w,h*.4,'#544d43',8);
  line(ctx,m.top.x,m.top.y,m.bottom.x,m.bottom.y,'#c09a68',14);
  if(!m.aboard)person(ctx,m.cook.x,m.cook.y,true,t,'none',m.returning?'left':'right',true,false,'dining',{color:'#d4c4a5',badge:'K'});
  const cx=m.crate.x,cy=m.crate.y;crate(ctx,cx-27,cy,54,43);roundBox(ctx,cx-10,cy-35,20,15,1,'#e8d2a2','#68583e');label(ctx,'07',cx-7,cy-23,10);
  if(t>=10){line(ctx,cx-28,cy-55,cx-50,cy-80,'#bd935c',6);const px=cx+clamp((t-10)/5,0,1)*w*.18;if(px<w*.89)person(ctx,px,ground,false,t,'none','right',t<15);}
}
function drawCommandPrelude(ctx,w,h,client) {
  const p=positionXY(client.data.position,client.data.rules),camera=cameraFor(p,w,h,'aft_deck');
  background(ctx,w,h,camera.x,0);ctx.save();ctx.scale(camera.zoom,camera.zoom);ctx.translate(-camera.x,-camera.y);
  ship(ctx,client.data);storyDecor(ctx,client.data);
  person(ctx,p.x,p.y,false,0,'none','right',false,true,'officer',client.data.rules.guard_styles.officer);
  speechBubble(ctx,p.x,p.y-110,"All ahoy! We're heading home.");ctx.restore();
}
// The drifting barrel and the foreground water use the same wave height.
function castawayWave(x, t, level, scale, swell) {
  const distance = x / scale;
  return level + swell * (Math.sin(distance * .042 - t * 3.1)
    + .26 * Math.sin(distance * .074 + t * 2));
}

function castawayShoreX(w, h, y, island) {
  const depth = (y - h * .68) / h;
  const bend = (depth < 0 ? 5 : .85) * depth * depth;
  return w * (1.18 - .46 * island - .46 * depth + bend);
}

function castawayMotion(w, h, t) {
  const horizon = h * .45;
  if (t < CASTAWAY_CELL_SECONDS) {
    return {phase: 'cell', gateOpen: t >= 1.05, found: t >= 2.85,
      fade: clamp((t - 4.55) / .45, 0, 1)};
  }
  if (t < CASTAWAY_DRIFT_START) {
    const elapsed = t - CASTAWAY_CELL_SECONDS;
    return {phase: 'overboard', carry: clamp(elapsed / 1.55, 0, 1),
      air: clamp((elapsed - 1.55) / 1, 0, 1), splash: elapsed - 2.55};
  }

  const scale = Math.max(.1, Math.min(w / 1000, h / 560) * 2);
  const level = h * .69;
  const driftTime = t - CASTAWAY_DRIFT_START;
  const driftX = seconds => w * (.43 + .009 * seconds);
  if (t < CASTAWAY_SHORE_START) {
    const day = Math.floor(driftTime / CASTAWAY_DAY_SECONDS) + 1;
    const fraction = (driftTime % CASTAWAY_DAY_SECONDS) / CASTAWAY_DAY_SECONDS;
    const night = Math.min(clamp((fraction - .53) / .17, 0, 1), clamp((1 - fraction) / .10, 0, 1));
    const storm = day === 2 ? Math.sin(Math.PI * clamp(fraction / .9, 0, 1)) : 0;
    const peekStart = [.24, 0, .68, .28][day - 1];
    const peekTime = (fraction - peekStart) / .27;
    const peek = day !== 2 && peekTime > 0 && peekTime < 1 ? Math.sin(Math.PI * peekTime) : 0;
    const x = driftX(driftTime);
    const swell = scale * (3 + storm * 8);
    const waterline = castawayWave(x, t, level, scale, swell);
    return {phase: 'adrift', day, fraction, night, storm, peek, horizon, scale, level, swell, waterline,
      barrel: {x, y: waterline + 2 * scale, rot: Math.sin(t * 2.3) * (.13 + storm * .35)}};
  }

  const elapsed = t - CASTAWAY_SHORE_START;
  const island = easeInOut(clamp(elapsed / 2.5, 0, 1));
  const arrival = easeInOut(clamp((elapsed - .6) / 3, 0, 1));
  const tip = easeInOut(clamp((elapsed - 3.6) / .7, 0, 1));
  const crawl = clamp((elapsed - 4.3) / 2.25, 0, 1);
  const shoreX = castawayShoreX(w, h, level, 1);
  const startX = driftX(4 * CASTAWAY_DAY_SECONDS);
  const x = startX + (shoreX - 17 * scale - startX) * arrival;
  const swell = scale * (3 - 2 * arrival);
  const waterline = castawayWave(x, t, level, scale, swell);
  return {phase: 'ashore', island, arrival, crawl, shoreX, horizon, scale, level, swell, waterline,
    barrel: {x, y: level + (waterline - level) * (1 - arrival) + 2 * scale,
      rot: Math.sin(t * 2.3) * .13 * (1 - arrival) + tip * 1.32}};
}

function castawayGuards(data) {
  const kinds = new Set(['patrol', 'cargo', 'sleeper', ...Object.keys(data.guard_routes)]);
  return [...kinds].filter(kind => data[kind + '_alive']).slice(0, 2);
}

function drawCastawayCell(ctx, w, h, t, motion, data, coat) {
  const floor = data.rules.floors.cell[2];
  const x = data.position.zone === 'cell' ? data.position.value : data.rules.story_points.cell_floor.x;
  const player = {x, y: floor};
  const camera = cameraFor(player, w, h, 'cell');
  background(ctx, w, h, camera.x, t);
  ctx.save();
  ctx.scale(camera.zoom, camera.zoom);
  ctx.translate(-camera.x, -camera.y);
  ship(ctx, data);
  storyDecor(ctx, data);
  lyingPerson(ctx, x, floor - 10, coat);
  roundBox(ctx, x + 44, floor - 12, 6, 11, 2, '#87572d', '#412b20');

  castawayGuards(data).forEach((kind, index) => {
    const progress = clamp((t - .30 - index * .35) / 2.5, 0, 1);
    const startX = 465 + index * 30;
    const stopX = Math.min(x + 17, 323) + index * 34;
    const guardX = startX + (stopX - startX) * progress;
    const checking = index === 0 && motion.found;
    const body = checking ? crouchingPerson : person;
    body(ctx, guardX, floor, true, t, 'none', 'left', progress < 1,
      false, kind, data.rules.guard_styles[kind]);
  });
  cellBars(ctx, motion.gateOpen || data.door_open);
  if (motion.found) speechBubble(ctx, x + 45, floor - 108, "He's not breathing.");
  ctx.restore();

  const shade = ctx.createRadialGradient(w * .54, h * .63, h * .22, w * .54, h * .63, w * .67);
  shade.addColorStop(0, 'rgba(8,16,25,0)');
  shade.addColorStop(1, 'rgba(8,16,25,.62)');
  ctx.fillStyle = shade;
  ctx.fillRect(0, 0, w, h);
  if (motion.fade) {
    ctx.fillStyle = `rgba(0,0,0,${motion.fade})`;
    ctx.fillRect(0, 0, w, h);
  }
}

function drawBarrelProp(ctx, x, y, angle, scale, {open = false, peek = 0, coat, disguised, lookLeft} = {}) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(angle);
  ctx.scale(scale, scale);
  barrel(ctx, 0, 23);
  ctx.beginPath();
  ctx.ellipse(0, -23, 19, 6, 0, 0, Math.PI * 2);
  ctx.fillStyle = open ? '#282321' : '#b38a54';
  ctx.fill();
  ctx.strokeStyle = '#513727';
  ctx.lineWidth = 2;
  ctx.stroke();

  if (peek > 0) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(-24, -90, 48, 69);
    ctx.clip();
    ctx.translate(0, 17 * (1 - peek));
    if (lookLeft) ctx.scale(-1, 1);
    barrelLurker(ctx, 0, -21, peek * .84, null, coat,
      disguised ? '#332c29' : '#263940', disguised ? '#dbb36e' : '#b5c9be');
    ctx.restore();
  }

  ctx.beginPath();
  ctx.ellipse(0, -23, 19, 6, 0, 0, Math.PI);
  ctx.strokeStyle = '#d5a96c';
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.restore();
}

function drawCastawayCrawl(ctx, mouth, scale, progress, t, coat, disguised) {
  ctx.save();
  ctx.beginPath();
  ctx.rect(mouth.x - 1, mouth.y - 38 * scale, 126 * scale, 82 * scale);
  ctx.clip();
  ctx.translate(mouth.x + (-30 + 70 * easeInOut(progress)) * scale, mouth.y + 13 * scale);
  ctx.scale(scale, scale);
  const stride = Math.sin(t * 13) * 5 * Math.sin(Math.PI * progress);
  ctx.fillStyle = `rgba(69, 46, 28, ${.22 * progress})`;
  ctx.beginPath();
  ctx.ellipse(2, 1, 27, 3, 0, 0, Math.PI * 2);
  ctx.fill();
  line(ctx, -10, -13, -20 - stride, -3, '#2d2927', 6);
  line(ctx, -20 - stride, -3, -27 - stride, -1, '#241f1e', 5);
  line(ctx, -5, -12, -9 + stride, -2, '#2d2927', 6);
  line(ctx, -9 + stride, -2, -16 + stride, 0, '#241f1e', 5);
  ctx.save();
  ctx.rotate(-.16);
  roundBox(ctx, -14, -24, 30, 17, 5, coat, '#2c2927');
  ctx.restore();
  line(ctx, 10, -18, 17, -8, coat, 6);
  line(ctx, 17, -8, 27 + stride, -3, '#d0a173', 5);
  ctx.fillStyle = '#d0a173';
  ctx.beginPath();
  ctx.arc(20, -24, 8, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#272622';
  ctx.beginPath();
  ctx.arc(24, -24, 1.3, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = disguised ? '#332c29' : '#263940';
  ctx.beginPath();
  ctx.moveTo(7, -29);
  ctx.lineTo(14, -36);
  ctx.lineTo(21, -33);
  ctx.lineTo(27, -36);
  ctx.lineTo(33, -29);
  ctx.fill();
  line(ctx, 7, -29, 33, -29, disguised ? '#dbb36e' : '#b5c9be', 2);
  ctx.restore();
}

function castawayBeach(ctx, w, h, t, motion) {
  const coast = y => castawayShoreX(w, h, y, motion.island);
  const top = h * .47;
  const sand = (offset, color) => {
    ctx.beginPath();
    ctx.moveTo(w + 20, top);
    for (let y = top; y < h + 12; y += 8) ctx.lineTo(coast(y) + offset, y);
    ctx.lineTo(w + 20, h + 12);
    ctx.fillStyle = color;
    ctx.fill();
  };
  sand(0, '#c4a575');
  sand(w * .035, '#eddaa5');
  const inland = coast(h * .63) + w * .12;
  ctx.fillStyle = '#557347';
  ctx.beginPath();
  ctx.ellipse(inland + w * .18, h * .64, w * .25, h * .11, -.22, Math.PI, Math.PI * 2);
  ctx.fill();
  const treeScale = motion.scale * .65;
  for (const [offset, depth, height, lean] of [[.03, .66, 103, -.16], [.12, .63, 133, .09], [.21, .69, 112, .19]]) {
    ctx.save();
    ctx.translate(inland + offset * w, h * depth);
    ctx.scale(treeScale, treeScale);
    ctx.rotate(lean);
    line(ctx, 0, 0, 6, -height, '#725137', 7);
    for (let i = 0; i < 6; i++) {
      const angle = -Math.PI * .95 + i * Math.PI * .19 + Math.sin(t * 1.5 + i) * .05;
      const dx = Math.cos(angle) * 48;
      const dy = Math.sin(angle) * 25;
      ctx.beginPath();
      ctx.moveTo(6, -height);
      ctx.quadraticCurveTo(6 + dx * .6, -height + dy - 9, 6 + dx, -height + dy + 12);
      ctx.strokeStyle = i % 2 ? '#396042' : '#4d7748';
      ctx.lineWidth = 6;
      ctx.stroke();
    }
    ctx.restore();
  }
  for (let edge = 0; edge < 2; edge++) {
    ctx.beginPath();
    for (let y = top; y <= h + 9; y += 5) {
      const x = coast(y) - (3 + edge * 9 + Math.sin(y * .06 - t * 2.4) * 2) * motion.scale;
      if (y === top) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = edge ? 'rgba(212,236,230,.29)' : 'rgba(247,251,232,.75)';
    ctx.lineWidth = edge ? 2 : 3;
    ctx.stroke();
  }
}

function drawCastawayWaterBarrel(ctx, w, h, t, motion, coat, disguised) {
  const {barrel: b, scale, level, swell} = motion;
  const wave = x => castawayWave(x, t, level, scale, swell);
  const onBeach = x => motion.phase === 'ashore' && x >= castawayShoreX(w, h, wave(x), motion.island);
  const left = b.x - 52 * scale;
  const right = b.x + 52 * scale;
  ctx.save();
  // Draw the barrel only above the front wave, or where it rests on the sand.
  ctx.beginPath();
  ctx.moveTo(left, 0);
  ctx.lineTo(right, 0);
  for (let x = right; x >= left - scale; x -= 1.5 * scale) ctx.lineTo(x, onBeach(x) ? h : wave(x));
  ctx.closePath();
  ctx.clip();
  drawBarrelProp(ctx, b.x, b.y, b.rot, scale,
    {open: true, peek: motion.peek, coat, disguised, lookLeft: motion.night > .5});
  ctx.restore();

  // Short arcs overlap the barrel at the waterline and trail it down-current.
  for (const [start, end, offset, alpha] of [[-37, -8, 0, .8], [0, 34, 1, .78], [-42, 14, 8, .48], [-57, -9, 15, .28]]) {
    ctx.beginPath();
    let started = false;
    for (let dx = start; dx <= end; dx += 2) {
      const x = b.x + dx * scale;
      if (onBeach(x)) break;
      const y = wave(x) + offset * scale + Math.sin((dx - start) / (end - start) * Math.PI) * scale * 2;
      if (!started) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      started = true;
    }
    ctx.strokeStyle = `rgba(224,246,231,${alpha * (1 - (motion.night || 0) * .55)})`;
    ctx.lineWidth = scale * (offset ? 1 : 1.6);
    ctx.stroke();
  }
  if (motion.crawl > 0) {
    const mouth = {x: b.x + 23 * scale * Math.sin(b.rot), y: b.y - 23 * scale * Math.cos(b.rot)};
    drawCastawayCrawl(ctx, mouth, scale * .83, motion.crawl, t, coat, disguised);
  }
}

function drawCastaway(ctx, w, h, t, client) {
  const motion = castawayMotion(w, h, t);
  const {disguised} = client.data;
  const coat = disguised ? '#9c3d33' : '#2d6b73';
  const caption = text => {
    ctx.save();
    ctx.textAlign = 'center';
    ctx.font = '600 17px system-ui';
    const width = Math.min(ctx.measureText(text).width, w - 40);
    ctx.fillStyle = 'rgba(10,14,18,.65)';
    ctx.fillRect((w - width) / 2 - 14, h * .95 - 21, width + 28, 30);
    ctx.fillStyle = '#fff1cf';
    ctx.fillText(text, w / 2, h * .95, width);
    ctx.restore();
  };
  if (motion.phase === 'cell') {
    drawCastawayCell(ctx, w, h, t, motion, client.data, coat);
    caption(motion.found ? 'The guards find you on the cell floor.' : 'You swallow the pills and lie down…');
    return;
  }
  if (motion.phase === 'overboard') {
    const sky = ctx.createLinearGradient(0, 0, 0, h);
    sky.addColorStop(0, '#08111f');
    sky.addColorStop(1, '#1d3446');
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = '#f3e6c4';
    ctx.beginPath();
    ctx.arc(w * .16, h * .16, 20, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#10263a';
    ctx.fillRect(0, h * .62, w, h * .38);
    const ship = cinematicShip(ctx, w * .92, h * .79, w * 1.24, {night: 1});
    const rail = ship.point(700, 200);
    const drop = {x: w * .20, y: h * .83};
    const startX = ship.point(1150, 200).x;
    const carryX = startX + (rail.x - startX) * motion.carry;
    const scale = ship.scale * 1.5;
    const guards = castawayGuards(client.data);
    guards.forEach((kind, index) => {
      const offset = (index - (guards.length - 1) / 2) * 64 * scale;
      person(ctx, carryX + offset, rail.y, true, t, 'none', 'left',
        motion.carry < 1, false, kind, client.data.rules.guard_styles[kind]);
    });
    if (motion.air === 0) {
      drawBarrelProp(ctx, carryX, rail.y - 30 * scale, 0, scale);
    } else if (motion.air < 1) {
      const air = motion.air;
      const startY = rail.y - 30 * scale;
      const x = rail.x + (drop.x - rail.x) * air;
      const y = startY + (drop.y - startY) * air * air - 90 * scale * air * (1 - air);
      drawBarrelProp(ctx, x, y, air * 2.4, scale);
    } else {
      const splash = motion.splash;
      ctx.strokeStyle = `rgba(220,235,240,${Math.max(0, .85 - splash * .55)})`;
      ctx.lineWidth = 2;
      for (const ring of [1, 1.65]) {
        ctx.beginPath();
        ctx.ellipse(drop.x, drop.y, (13 + splash * 43) * ring, (3 + splash * 11) * ring, 0, 0, Math.PI * 2);
        ctx.stroke();
      }
      if (splash < .55) {
        for (const dx of [-1, -.62, .53, .94]) {
          const x = drop.x + dx * (14 + splash * 70);
          const y = drop.y - Math.sin(splash * Math.PI / .55) * (28 + Math.abs(dx) * 16);
          line(ctx, x, y, x + dx * 5, y - 7, '#cfebea', 2);
        }
      }
    }
    caption(motion.carry < 1 ? 'They carry you out in a barrel…' : '“Over the side with him.”');
    return;
  }

  const adrift = motion.phase === 'adrift';
  const night = motion.night || 0;
  const storm = motion.storm || 0;
  const mix = (a, b, amount) => a.map((value, i) => Math.round(value + (b[i] - value) * amount));
  const skyColor = (day, cloud, dark) => `rgb(${mix(mix(day, cloud, storm), dark, night)})`;
  const sky = ctx.createLinearGradient(0, 0, 0, motion.horizon);
  sky.addColorStop(0, skyColor([118, 170, 199], [70, 78, 86], [6, 12, 30]));
  sky.addColorStop(1, skyColor([226, 232, 214], [118, 124, 124], [22, 36, 60]));
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, w, motion.horizon + 2);
  if (night > 0) {
    ctx.save();
    ctx.globalAlpha = night;
    ctx.fillStyle = '#fff3cf';
    for (let i = 0; i < 60; i++) {
      ctx.beginPath();
      ctx.arc(((i * 137 + 71) % 997) / 997 * w, ((i * 73 + 29) % 431) / 431 * motion.horizon * .9,
        i % 5 === 0 ? 1.8 : 1, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.beginPath();
    ctx.arc(w * .2, h * .14, 16, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
  if (night < 1) {
    const sunY = adrift ? motion.horizon * (1 - .8 * Math.sin(Math.PI * clamp(motion.fraction / .65, 0, 1))) : motion.horizon * .36;
    ctx.save();
    ctx.globalAlpha = 1 - Math.max(night, storm * .9);
    ctx.fillStyle = motion.day === 3 ? '#fff2b0' : '#ffe39c';
    ctx.beginPath();
    ctx.arc(w * .78, sunY, motion.day === 3 ? 38 : 26, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  const sea = ctx.createLinearGradient(0, motion.horizon, 0, h);
  sea.addColorStop(0, skyColor([87, 149, 160], [69, 91, 103], [20, 38, 57]));
  sea.addColorStop(1, skyColor([36, 101, 120], [29, 45, 63], [8, 22, 40]));
  ctx.fillStyle = sea;
  ctx.fillRect(0, motion.horizon, w, h - motion.horizon);
  for (let row = 1; row <= 7; row++) {
    const y = motion.horizon + (h - motion.horizon) * (row / 7) ** 1.9;
    const spacing = w * (.095 + row * .012);
    const length = spacing * (.29 + row * .05);
    const offset = (t * (7 + row * 4) + row * 53) % spacing;
    for (let x = -spacing; x <= w + spacing; x += spacing) {
      const from = x + offset;
      const curl = Math.sin(x * .02 - t * 2.7 + row) * (2 + row * storm);
      ctx.beginPath();
      ctx.moveTo(from, y + curl);
      ctx.quadraticCurveTo(from + length * .54, y + curl - (1 + row * .3),
        from + length, y + curl + row * .2);
      ctx.strokeStyle = `rgba(226,244,232,${(.18 + row * .015) * (1 - night * .4)})`;
      ctx.lineWidth = 1 + row * .22;
      ctx.stroke();
    }
  }
  if (motion.day === 4 || !adrift) {
    for (let i = 0; i < 3; i++) {
      const x = ((i * 240 + t * 55) % (w + 200)) - 100;
      const y = h * .18 + i * 22 + Math.sin(t * 3 + i) * 8;
      line(ctx, x - 10, y, x, y + 5, '#f5f2ea', 2.5);
      line(ctx, x, y + 5, x + 10, y, '#f5f2ea', 2.5);
    }
  }
  if (!adrift) castawayBeach(ctx, w, h, t, motion);
  drawCastawayWaterBarrel(ctx, w, h, t, motion, coat, disguised);

  if (storm > .05) {
    ctx.save();
    ctx.globalAlpha = storm;
    ctx.fillStyle = '#4a5258';
    for (let i = 0; i < 6; i++) {
      ctx.beginPath();
      ctx.ellipse(((i * 211 + t * 40) % (w + 300)) - 150, h * .08 + (i % 3) * 28, 150, 34, 0, 0, Math.PI * 2);
      ctx.fill();
    }
    for (let i = 0; i < 90; i++) {
      const x = ((i * 53 + t * 420) % (w + 100)) - 50;
      const y = (i * 97 + t * 900) % h;
      line(ctx, x, y, x - 6, y + 16, 'rgba(200,215,225,.45)', 1.5);
    }
    if (Math.sin(t * 7.3) > .985) {
      ctx.fillStyle = 'rgba(255,255,240,.55)';
      ctx.fillRect(0, 0, w, h);
    }
    ctx.restore();
  }
  if (adrift) {
    ctx.save();
    ctx.globalAlpha = clamp(Math.min(motion.fraction * 6, (1 - motion.fraction) * 6), 0, 1);
    ctx.textAlign = 'center';
    ctx.font = '700 34px Georgia, serif';
    ctx.fillStyle = '#fff1cf';
    ctx.fillText(`Day ${motion.day}`, w / 2, h * .12);
    ctx.restore();
    const dayLines = ['The barrel drifts on the open sea.', 'A storm rocks the barrel.', 'Burning sun, no land in sight.', 'Seagulls. Land must be close…'];
    const nightLines = ['Your first night at sea.', 'The storm dies down in the dark.', 'Still no land.', 'You hear surf in the distance.'];
    const words = (night > .5 ? nightLines : dayLines)[motion.day - 1];
    caption(motion.peek > .45 && night > .5 ? 'You look out at the stars.' : words);
  } else if (motion.arrival < 1) {
    caption('The surf carries the barrel toward the beach…');
  } else {
    caption(motion.crawl < .25 ? 'The barrel catches at the water’s edge…' : 'You crawl onto the wet sand.');
  }
}
function drawEnding(ctx,w,h,client) {
  if(client.data.finale&&client.data.finale.status!=='won'){drawFinale(ctx,w,h,client);return;}
  if(client.data.ending==='free'){const still=typeof matchMedia==='function'&&matchMedia('(prefers-reduced-motion: reduce)').matches;drawRescue(ctx,w,h,still?5.4:Math.min(RESCUE_SECONDS,Math.max(0,(performance.now()-client.endingStartedAt)/1000)));return;}
  const reduced=typeof matchMedia==='function'&&matchMedia('(prefers-reduced-motion: reduce)').matches,elapsed=Math.max(0,(performance.now()-client.endingStartedAt)/1000);
  if(client.data.ending==='crate'&&elapsed<CRATE_NIGHT_SECONDS){drawCratePrelude(ctx,w,h,reduced?4:elapsed);return;}
  if(client.data.ending==='dinghy'){drawDinghyEscape(ctx,w,h,reduced?21:elapsed,client);return;}
  if(client.data.ending==='command'&&elapsed<3&&!reduced){drawCommandPrelude(ctx,w,h,client);return;}
  if(client.data.ending==='castaway'){drawCastaway(ctx,w,h,reduced?CASTAWAY_SECONDS:Math.min(elapsed,CASTAWAY_SECONDS),client);return;}
  const t=reduced?(client.data.ending==='command'?24:20):Math.max(0,elapsed-(client.data.ending==='crate'?CRATE_NIGHT_SECONDS:0));
  const sky=ctx.createLinearGradient(0,0,0,h);sky.addColorStop(0,'#325c70');sky.addColorStop(.48,'#dfaa75');sky.addColorStop(1,'#234d59');ctx.fillStyle=sky;ctx.fillRect(0,0,w,h);
  const seaY=h*.38;ctx.fillStyle='#f6d8a0';ctx.beginPath();ctx.arc(w*.8,seaY-25,40,0,Math.PI*2);ctx.fill();ctx.fillStyle='#346d77';ctx.fillRect(0,seaY,w,h-seaY);
  for(let row=0;row<7;row++){const y=seaY+row*25;line(ctx,0,y,w,y,'rgba(235,220,166,.17)',2);}
  if(client.data.ending==='takeover'||client.data.ending==='command'||client.data.ending==='lullaby') {
    const command=client.data.ending==='command',sail=command?clamp((t-3)/3,0,1):1,f=clamp((t-(command?6:2))/18,0,1);
    if(command||client.data.ending==='lullaby'){ctx.fillStyle='#263c3e';ctx.fillRect(w*.87,seaY-25,w*.12,28);line(ctx,w*.91,seaY,w*.91,seaY-60,'#314543',9);}
    ctx.save();ctx.globalAlpha=clamp((1-f)*5,0,1);const ship=cinematicShip(ctx,w*(.5+f*.22),h*.78-f*h*.37,w*.9*(1-f*.95),{player:true,captain:command,sails:sail});
    if(client.data.ending==='lullaby')for(let i=0;i<5;i++){const k=(t*.5+i*.2)%1,p=ship.point(700+i*300,190);ctx.globalAlpha=clamp((1-f)*5,0,1)*(1-k);label(ctx,'Z',p.x+k*18,p.y-k*55,16+k*14);}
    ctx.restore();
  } else drawCrateDelivery(ctx,w,h,t);
}

// ---- Cannon finale ------------------------------------------------------------------------
// After an ending the guards come back with cannons. The page plays the volley the server chose
// and reports the player's moves; the server judges them. Keep these numbers equal to finale.py.
const FINALE={balls:10,lives:3,endMs:37900,windowBefore:500,windowAfter:250};
const FINALE_TRAVEL_MS=1500;
const FINALE_MAX_MOVES=120;
const RESCUE_SECONDS=9;
function finaleBallResult(ball,moves){
  const counter=ball.lane==='low'?'jump':'duck';
  return moves.some(m=>m[1]===counter&&m[0]>=ball.at-FINALE.windowBefore&&m[0]<=ball.at+FINALE.windowAfter);
}
function finaleJudge(balls,moves){
  let dodged=0;for(const b of balls)if(finaleBallResult(b,moves))dodged++;
  return [dodged,balls.length-dodged];
}
function finaleDarkNow(data){return Boolean(data.ending&&data.finale&&data.finale.status!=='won');}
function finaleStep(client,now){
  const f=client.data.finale;
  if(!f||f.status==='won'){client.fin=null;return null;}
  const id=f.seed+':'+f.attempt;
  if(!client.fin||client.fin.id!==id)client.fin={id,t0:now,t:0,moves:[],results:[],hits:0,left:FINALE.balls,lives:FINALE.lives,
    over:false,reports:0,nextReportAt:0,jumpAt:-9999,duckAt:-9999,flashAt:-9999,seenHits:0,frozenT:null};
  const fin=client.fin;
  fin.t=fin.frozenT??Math.max(0,now-fin.t0);
  fin.results=f.balls.map(b=>fin.t>b.at+FINALE.windowAfter?finaleBallResult(b,fin.moves):null);
  fin.hits=fin.results.filter(r=>r===false).length;
  fin.left=fin.results.filter(r=>r===null).length;
  fin.lives=Math.max(0,FINALE.lives-fin.hits);
  if(fin.hits>fin.seenHits){fin.seenHits=fin.hits;fin.flashAt=now;}
  fin.down=fin.hits>=FINALE.lives;
  fin.over=f.status==='lost'||fin.down||fin.t>=FINALE.endMs;
  if(fin.over&&fin.frozenT==null)fin.frozenT=fin.t;
  return fin;
}
// Returns true when the key belongs to the finale (so the normal ending ignores it).
function finaleKey(client,k,repeat,retry){
  const f=client.data.finale,fin=client.fin;
  if(!f||f.status==='won')return false;
  if(f.status==='lost'){if(k==='f'&&!repeat)retry();return true;}
  if(!fin||fin.over||repeat)return true;
  const kind=(k==='w'||k==='arrowup')?'jump':(k===' '||k==='s'||k==='arrowdown')?'duck':null;
  const t=Math.round(performance.now()-fin.t0);
  if(kind&&t>=0&&fin.moves.length<FINALE_MAX_MOVES){
    fin.moves.push([t,kind]);
    if(kind==='jump')fin.jumpAt=performance.now();else fin.duckAt=performance.now();
  }
  return true;
}
function finaleCannon(ctx,x,y,unit,flash){
  ctx.save();ctx.translate(x,y);ctx.scale(unit,unit);
  roundBox(ctx,-30,-9,60,18,6,'#2b2c31','#0f0f12');line(ctx,-24,-3,24,-3,'#555a63',3);
  ctx.fillStyle='#4b3426';ctx.beginPath();ctx.arc(10,12,10,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#201710';ctx.lineWidth=3;ctx.stroke();
  if(flash>0){ctx.globalAlpha=flash;ctx.fillStyle='#ffd27a';ctx.beginPath();ctx.arc(-38,0,16+10*flash,0,Math.PI*2);ctx.fill();ctx.fillStyle='rgba(180,180,180,.7)';ctx.beginPath();ctx.arc(-52,-8,10,0,Math.PI*2);ctx.arc(-60,-14,7,0,Math.PI*2);ctx.fill();}
  ctx.restore();
}
function finaleBoat(ctx,x,y,unit,pirate){
  ctx.save();ctx.translate(x,y);ctx.scale(unit,unit);
  ctx.fillStyle='#4b2f25';ctx.strokeStyle='#1d130f';ctx.lineWidth=4;ctx.beginPath();ctx.moveTo(-90,-8);ctx.quadraticCurveTo(0,26,90,-8);ctx.lineTo(70,28);ctx.quadraticCurveTo(0,44,-70,28);ctx.closePath();ctx.fill();ctx.stroke();
  line(ctx,-84,-4,84,-4,'#c99a62',4);
  ctx.restore();
  if(pirate)introPirate(ctx,x-18*unit,y-8*unit,unit*1.05);
}
function drawFinale(ctx,w,h,client){
  const f=client.data.finale,fin=client.fin,now=performance.now(),t=fin?fin.t:0;
  const unit=Math.min(w/900,h/500),seaY=h*.44,gy=h*.8,px=w*.2,ps=1.35*unit;
  const lowY=gy-16*unit,highY=gy-78*unit,fireX=w*.76,slide=(1-clamp(t/1500,0,1))*w*.4;
  const sky=ctx.createLinearGradient(0,0,0,seaY);sky.addColorStop(0,'#150f22');sky.addColorStop(1,'#8c3a2b');ctx.fillStyle=sky;ctx.fillRect(0,0,w,seaY);
  ctx.fillStyle='#e8603a';ctx.globalAlpha=.55;ctx.beginPath();ctx.arc(w*.5,seaY,55*unit,Math.PI,0);ctx.fill();ctx.globalAlpha=1;
  ctx.fillStyle='#14303a';ctx.fillRect(0,seaY,w,h-seaY);
  for(let r=0;r<7;r++){const y=seaY+12+r*((h-seaY)/7);line(ctx,0,y+Math.sin(now/600+r)*3,w,y+Math.sin(now/600+r+1)*3,'rgba(240,150,110,.15)',2);}
  // The player's raft.
  ctx.fillStyle='#5b3d2a';ctx.fillRect(0,gy,w*.44,h-gy);line(ctx,0,gy,w*.44,gy,'#c99a62',5);
  for(let x=0;x<w*.44;x+=46*unit)line(ctx,x,gy,x,h,'#3b271b',3);
  // The guards: two stacked cannons on the nearest boat and more boats behind.
  finaleBoat(ctx,w*.9+slide,seaY+14*unit,unit*1.4,true);finaleBoat(ctx,w*.62+slide*1.3,seaY+8*unit,unit*1.0,true);
  const gx=fireX+slide;
  ctx.fillStyle='#4b2f25';ctx.strokeStyle='#1d130f';ctx.lineWidth=4;ctx.beginPath();ctx.moveTo(gx-40*unit,gy+6*unit);ctx.lineTo(gx+230*unit,gy+6*unit);ctx.lineTo(gx+190*unit,gy+78*unit);ctx.quadraticCurveTo(gx+80*unit,gy+96*unit,gx-10*unit,gy+78*unit);ctx.closePath();ctx.fill();ctx.stroke();
  line(ctx,gx-40*unit,gy+10*unit,gx+230*unit,gy+10*unit,'#c99a62',4);
  roundBox(ctx,fireX+30*unit+slide,highY-18*unit,54*unit,(gy-highY)+22*unit,4,'#3d281e','#170f0b');
  const fired=(fin&&f.balls||[]).map((b,i)=>({b,i,p:fin?(fin.t-(b.at-FINALE_TRAVEL_MS))/FINALE_TRAVEL_MS:-1}));
  const flashFor=lane=>{let m=0;for(const o of fired)if(o.b.lane===lane&&o.p>=0&&o.p<.18)m=Math.max(m,1-o.p/.18);return m;};
  finaleCannon(ctx,fireX+30*unit+slide,lowY,unit*1.1,flashFor('low'));finaleCannon(ctx,fireX+30*unit+slide,highY,unit*1.1,flashFor('high'));
  // Balls and warnings.
  const reduced=typeof matchMedia==='function'&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  for(const {b,i,p} of fired){
    if(p<=0||p>1.5)continue;
    const y=b.lane==='low'?lowY:highY,x=fireX+(px-fireX)*p,res=fin.results[i];
    if(res===false&&p>1.02)continue;
    if(p<1&&(p>.3||reduced)){const mx=px+70*unit;ctx.fillStyle='rgba(255,220,130,.9)';ctx.beginPath();ctx.moveTo(mx,y);ctx.lineTo(mx+14*unit,y-8*unit);ctx.lineTo(mx+14*unit,y+8*unit);ctx.closePath();ctx.fill();
      ctx.textAlign='left';label(ctx,b.lane==='low'?'JUMP!':'DUCK!',mx+20*unit,y+5*unit,Math.max(12,15*unit));}
    ctx.fillStyle='rgba(60,60,64,.35)';ctx.beginPath();ctx.arc(x+22*unit,y,8*unit,0,Math.PI*2);ctx.fill();
    ctx.fillStyle='#202227';ctx.beginPath();ctx.arc(x,y,10*unit,0,Math.PI*2);ctx.fill();ctx.fillStyle='rgba(255,255,255,.35)';ctx.beginPath();ctx.arc(x-3*unit,y-3*unit,3*unit,0,Math.PI*2);ctx.fill();
  }
  // The player: jump arc, duck squash, or knocked down after the third hit.
  const jumpU=clamp((now-(fin?fin.jumpAt:-9999))/550,0,1),inJump=jumpU>0&&jumpU<1,duck=fin&&now-fin.duckAt<650&&!inJump;
  ctx.save();ctx.translate(px,gy-(inJump?Math.sin(Math.PI*jumpU)*80*unit:0));
  if(fin&&fin.down){ctx.rotate(-Math.PI/2);ctx.translate(0,-14*unit);}
  else if(duck)ctx.scale(1,.55);
  introPerson(ctx,0,0,ps,{scared:Boolean(fin&&fin.hits>0),seated:Boolean(duck)});ctx.restore();
  if(fin&&now-fin.flashAt<420){ctx.fillStyle=`rgba(210,30,20,${.38*(1-(now-fin.flashAt)/420)})`;ctx.fillRect(0,0,w,h);}
  // Heads-up display.
  ctx.textAlign='left';label(ctx,`CANNONBALLS LEFT  ${fin?fin.left:FINALE.balls}`,16,h*.12,Math.max(14,18*unit));
  for(let i=0;i<FINALE.lives;i++){ctx.font=`700 ${Math.max(18,24*unit)}px system-ui`;ctx.fillStyle=fin&&i>=fin.lives?'rgba(255,255,255,.22)':'#e0483b';ctx.fillText('♥',16+i*30*unit,h*.12+30*unit);}
  ctx.textAlign='center';
  if(t<2200&&f.status==='active'){ctx.fillStyle='rgba(0,0,0,.35)';ctx.fillRect(0,h*.2,w,h*.16);label(ctx,'THE GUARDS FOUND YOU!',w/2,h*.3,Math.max(22,34*unit));}
  else if(f.status==='active'&&t>2200&&t<5500)label(ctx,'W / ↑ jump over low shots  ·  Space / S / ↓ duck under high ones',w/2,h*.2,Math.max(12,15*unit));
  if(f.status==='lost'){ctx.fillStyle='rgba(0,0,0,.55)';ctx.fillRect(0,0,w,h);label(ctx,'CAUGHT!',w/2,h*.4,Math.max(30,50*unit));
    label(ctx,'The guards drag you back to the ship…',w/2,h*.4+36*unit,Math.max(13,17*unit));}
  else if(fin&&fin.down){label(ctx,'Hit!',w/2,h*.4,Math.max(26,40*unit));}
  ctx.textAlign='left';
}
function drawRescue(ctx,w,h,t){
  const unit=Math.min(w/900,h/500),seaY=h*.46,gy=h*.8,px=w*.2,ease=x=>x*x*(3-2*x),k=clamp(t/RESCUE_SECONDS,0,1);
  const sky=ctx.createLinearGradient(0,0,0,seaY);sky.addColorStop(0,'#4a7f93');sky.addColorStop(1,'#f4b678');ctx.fillStyle=sky;ctx.fillRect(0,0,w,seaY);
  ctx.fillStyle='#fbe2a6';ctx.beginPath();ctx.arc(w*.16,seaY-(10+k*30)*unit,46*unit,0,Math.PI*2);ctx.fill();
  ctx.fillStyle='#2f6f7e';ctx.fillRect(0,seaY,w,h-seaY);
  for(let r=0;r<7;r++){const y=seaY+12+r*((h-seaY)/7);line(ctx,0,y+Math.sin(t*1.4+r)*3,w,y+Math.sin(t*1.4+r+1)*3,'rgba(245,230,180,.2)',2);}
  ctx.save();ctx.globalAlpha=clamp(1-t/6,0,1);finaleBoat(ctx,w*.88+t*26*unit,seaY+10*unit,unit*.9,true);finaleBoat(ctx,w*.7+t*34*unit,seaY+6*unit,unit*.7,true);ctx.restore();
  const arrive=ease(clamp(t/4,0,1)),leave=ease(clamp((t-5.4)/3.6,0,1)),boarded=t>=5.2;
  const sx=(-w*.25+(px+120*unit+w*.25)*arrive)*(1-leave)+(-w*.1)*leave,sy=seaY+(h-seaY)*.28-leave*(h-seaY)*.2,ss=unit*.9*(1-.55*leave);
  if(!boarded){ctx.fillStyle='#5b3d2a';ctx.fillRect(0,gy,w*.44,h-gy);line(ctx,0,gy,w*.44,gy,'#c99a62',5);}
  const dog={x:70,y:-26,scale:.82,rotation:0,wet:false,fade:1,paddling:t};
  introSkiff(ctx,sx,sy,ss,boarded?{reach:0,seated:true}:null,dog,t);
  if(!boarded){
    const u=clamp((t-4)/1.2,0,1),jx=px+(sx-46*ss-px)*u,jy=gy+(sy-26*ss-gy)*u-Math.sin(Math.PI*u)*60*unit;
    introPerson(ctx,u>0?jx:px,u>0?jy:gy,1.35*unit*(1-.3*u));
  }
  if(t>3.2&&t<5.2&&Math.sin(t*14)>0)label(ctx,'Woof!',sx+70*ss,sy-80*ss,Math.max(14,20*unit));
}
// The normal ending panel waits until the cannon finale is won ("free"); older endings go through it too.
function finaleGate(data){return Boolean(data.ending&&data.ending!=='free');}
