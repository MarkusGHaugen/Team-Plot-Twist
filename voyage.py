"""Escape economy, watch rotation and timed guard fire. All times are game milliseconds."""
import json, math
import logic as L
from dataclasses import replace

def progress(s):
 from logic import story_progress
 return {'coins':0,'claimed':[],'paid':[],'armed':False,'duck':False,'hp':2,'shots':[],'next_fire':{},**story_progress(s).get('voyage',{})}

def save(s,v):
 from logic import story_progress
 p=story_progress(s);p['voyage']=v
 return replace(s,story_state=json.dumps(p,separators=(',',':')))

def valid(v):
 if not isinstance(v,dict) or set(v)-{'coins','claimed','paid','armed','duck','hp','shots','next_fire','watch_start','last_tick','escort','capture_started','guide','concealed','captain_worn'}:return False
 concealed=v.get('concealed',{})
 if not isinstance(concealed,dict) or any(k not in (*L.GUARD_ROUTES,'sleeper') or b not in {x[0] for x in L.BARRELS} for k,b in concealed.items()):return False
 if len(set(concealed.values()))!=len(concealed) or type(v.get('captain_worn',False)) is not bool:return False
 claimed=v.get('claimed',[]);paid=v.get('paid',[])
 if not isinstance(claimed,list) or len(set(claimed))!=len(claimed) or any(x not in ('coins_hold','coins_provisions','coins_chart','coins_crew') for x in claimed):return False
 if not isinstance(paid,list) or len(set(paid))!=len(paid) or any(x not in ('cook','boatswain') for x in paid):return False
 if type(v.get('coins',0)) is not int or v.get('coins',0)!=len(claimed)-sum(2 if x=='cook' else 3 for x in paid) or v.get('coins',0)<0:return False
 if any(type(v.get(k,False)) is not bool for k in ('armed','duck')):return False
 if type(v.get('hp',2)) is not int or not 0<=v.get('hp',2)<=2:return False
 for k in ('watch_start','last_tick','capture_started'):
  if k in v and (type(v[k]) is not int or v[k]<0):return False
 if not isinstance(v.get('shots',[]),list) or len(v.get('shots',[]))>20:return False
 for b in v.get('shots',[]):
  if not isinstance(b,dict) or set(b)!={'x','y','dir','born'} or any(type(b[k]) not in (int,float) or not math.isfinite(b[k]) for k in b) or b['dir'] not in (-1,1) or b['born']<0:return False
 if not isinstance(v.get('next_fire',{}),dict) or any(k not in ('patrol','cargo','dining','lookout','sailor','armorer','medic','boatswain','officer','sleeper') or type(t) is not int or t<0 for k,t in v.get('next_fire',{}).items()):return False
 e=v.get('escort')
 if e is not None and (not isinstance(e,dict) or not {'kind','started','path'}<=set(e) or set(e)-{'kind','started','path','covers','distance','target','updated','paused','hidden','return_path','resume_elapsed'} or e['kind'] not in paid or type(e['started']) is not int or e['started']<0 or not isinstance(e['path'],list) or not 2<=len(e['path'])<=80 or any(not isinstance(p,list) or len(p)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>3000 for x in p) for p in e['path'])):return False
 if e and (e['path'][-1] != ([1260,245] if e['kind']=='cook' else [1660,245]) or any(not 160<=p[0]<=2580 or not 245<=p[1]<=500 for p in e['path'])):return False
 if e and set(e)!={'kind','started','path'}:
  if set(e)!={'kind','started','path','covers','distance','target','updated','paused','hidden','return_path','resume_elapsed'}:return False
  if any(type(e.get(k)) not in (int,float) or not math.isfinite(e[k]) or e[k]<0 for k in ('distance','target','updated','resume_elapsed')):return False
  total=sum(math.dist(a,b) for a,b in zip(e['path'],e['path'][1:]))
  if not 0<=e['distance']<=e['target']<=total+.01 or e['updated']<e['started']:return False
  if any(type(e.get(k)) is not bool for k in ('paused','hidden')) or e['hidden']!=e['paused']:return False
  stops=e.get('covers')
  if not isinstance(stops,list) or not 1<=len(stops)<=80 or any(type(x) not in (int,float) or not math.isfinite(x) or not 0<=x<=total+.01 for x in stops):return False
  if stops!=sorted(set(stops)) or stops[0]!=0 or abs(stops[-1]-total)>.01:return False
  if not path_valid(e.get('return_path')) or e['return_path'][0]!=e['path'][-1]:return False
 g=v.get('guide')
 if g is not None:
  if not isinstance(g,dict) or set(g)!={'kind','path','started','speech_until','resume_elapsed'} or g['kind'] not in paid or not path_valid(g['path']):return False
  if any(type(g[k]) not in (int,float) or not math.isfinite(g[k]) or g[k]<0 for k in ('started','speech_until','resume_elapsed')):return False
 return True

def path_valid(path):
 return isinstance(path,list) and 2<=len(path)<=80 and all(isinstance(p,(list,tuple)) and len(p)==2 and all(type(x) in (int,float) and math.isfinite(x) for x in p) and 160<=p[0]<=2580 and 245<=p[1]<=500 for p in path)

def along(path,f):
 lens=[math.dist(a,b) for a,b in zip(path,path[1:])];d=max(0,min(1,f))*sum(lens)
 for a,b,n in zip(path,path[1:],lens):
  if d<=n:return (a[0]+(b[0]-a[0])*d/max(n,1),a[1]+(b[1]-a[1])*d/max(n,1))
  d-=n
 return tuple(path[-1])

def watch_pose(s,kind,now):
 search=L.search_pose_at(s,kind,now)
 if search is not None:return search,False
 return normal_watch_pose(s,kind,now)

def normal_watch_pose(s,kind,now):
 from logic import GuardPose,Position,route_points
 v=progress(s);t=max(0,(now-v.get('watch_start',now))/1000)%104
 # No replacement is created when one member of the pair dies.
 if kind=='cargo' and 'watch_start' not in v:return None,False
 if not (s.sleeper_alive and s.cargo_alive):
  if kind=='sleeper':return GuardPose(300,365,'armed_watch' if v['armed'] else 'sleep',0,1 if L.position_xy(s.position)[0]>=300 else -1),not v['armed']
  return None,False
 sleeping=(t<45 if kind=='sleeper' else 52<=t<97)
 if sleeping:return GuardPose(300,365,'armed_watch' if v['armed'] else 'sleep',0,1 if L.position_xy(s.position)[0]>=300 else -1),not v['armed']
 path=route_points(Position('cabin',300),Position('chest_room',1320))
 if 45<=t<52: f=(t-45)/7 if kind=='sleeper' else 1-(t-45)/7
 elif 97<=t<104:f=1-(t-97)/7 if kind=='sleeper' else (t-97)/7
 else:
  duty=t if kind=='cargo' else t-52
  for i,p in enumerate(L.CARGO_WATCH_ROUTE):
   if duty<p.duration:
    f=duty/p.duration;previous=L.CARGO_WATCH_ROUTE[i-1]
    facing=(1 if previous.x2>=previous.x1 else -1) if p.x1==p.x2 else (1 if p.x2>p.x1 else -1)
    return GuardPose(p.x1+(p.x2-p.x1)*f,p.y1+(p.y2-p.y1)*f,p.name,f,facing),False
   duty-=p.duration
  return GuardPose(1320,500,'watch',0,1),False
 x,y=along(path,f);return GuardPose(x,y,'watch',f,1 if kind=='sleeper' else -1),False

def captain_ready(s):
 v=progress(s)
 return bool(v.get('captain_worn') and 'captain_uniform' in L.story_progress(s)['items'] and 'officer' in v.get('concealed',{}) and not s.officer_alive and s.disguised and not v['armed'])

def wear_captain(s):
 p=L.story_progress(s);v=progress(s)
 if 'officer' not in v.get('concealed',{}) or s.officer_alive:return L.ActionResult(s,False,'Conceal the officer first to unlock this uniform.')
 if v.get('captain_worn'):return L.ActionResult(s,False,'You are already wearing the captain uniform.')
 if 'captain_uniform' not in p['items']:p['items'].append('captain_uniform')
 v['captain_worn']=True;p['voyage']=v
 s=replace(s,story_state=json.dumps(p),disguised=True,wardrobe_contents='player_clothes',suspect_started_ms=0,suspect_guard_zone='',suspect_guard_value=0.)
 return L.ActionResult(s,True,'You put on the captain uniform. The crew will obey you at the helm once the search settles.')

def ambush(s,kind,now,elapsed):
 v=progress(s)
 def no(message):return L.ActionResult(s,False,message)
 barrel=next((b for b in L.BARRELS if b[0]==s.hidden_barrel),None)
 if not barrel or s.position!=L.Position(barrel[1],barrel[2]) or s.reading or s.ending or s.capture_phase!='none' or v.get('escort'):return no('Hide in a round barrel before ambushing.')
 if s.hidden_barrel in v.get('concealed',{}).values():return no('This barrel already conceals a body. Find another barrel.')
 if kind not in (*L.GUARD_ROUTES,'sleeper') or not getattr(s,kind+'_alive'):return no('Wait until a living crew member passes the barrel.')
 pose=L.guard_pose_at(s,kind,elapsed,now);x,y=L.position_xy(s.position)
 if abs(pose.x-x)>58 or abs(pose.y-y)>22:return no('Wait until the crew member is closer to the barrel.')
 v.setdefault('concealed',{})[kind]=s.hidden_barrel
 changes={kind+'_alive':False}
 if kind!='sleeper':changes.update({kind+'_corpse_x':x,kind+'_corpse_y':y})
 s=replace(s,**changes)
 if kind=='patrol' and not s.has_key:s=replace(s,has_key=True,held_item='cell_key')
 if kind=='sleeper' and not s.has_blue_key:s=replace(s,has_blue_key=True,held_item='blue_key')
 return L.ActionResult(save(s,v),True,'Silent ambush. The body is concealed inside the barrel.'+(' The captain uniform is now accessible in the captain cabin chest.' if kind=='officer' else ''))

def boat_ready(s):
 from logic import story_progress
 p=story_progress(s);v=progress(s)
 return 'sail' in p['items'] and ('rope' in p['items'] or 'boatswain' in v['paid'])

def voyage_action(s,kind,point,wall,elapsed=0):
 from logic import ActionResult,STORY_POINTS,Position,story_progress,game_now_ms,route_points,guard_pose_at,GUARD_ROUTES
 v=progress(s);p=story_progress(s);now=game_now_ms(s,wall)
 def no(msg):return ActionResult(s,False,msg)
 if s.ending or s.capture_phase!='none' or (s.reading and kind!='finish'):return no('You cannot do this now.')
 if kind=='tick':return crew_tick(s,now,elapsed)
 if kind in ('duck','stand','toggle_duck'):
  if s.hidden_barrel or s.in_hammock or v.get('escort'):return no('Leave cover before changing stance.')
  v['duck']=not v['duck'] if kind=='toggle_duck' else kind=='duck'
  return ActionResult(save(s,v),True,'Crouching. Space to stand.' if v['duck'] else 'Standing.')
 if kind=='bribe':
  if s.reading or s.hidden_barrel or s.in_hammock or v.get('escort'):return no('Leave cover before talking.')
  guard='dining' if point=='cook' else 'boatswain';cost=2 if point=='cook' else 3
  if point not in ('cook','boatswain') or not getattr(s,guard+'_alive'):return no('That crew member cannot help you.')
  pose=guard_pose_at(s,guard,elapsed,now);x,y=L.position_xy(s.position)
  if abs(x-pose.x)>65 or abs(y-pose.y)>25:return no('Move closer to talk.')
  if v['armed']:return no('They will not negotiate during a gunfight.')
  if point in v['paid']:return no('You have already paid.')
  if v['coins']<cost:return no(f'You need {cost} coins.')
  if point=='boatswain' and 'sail' not in p['items']:return no('Find a sail before asking for passage.')
  target=Position('kitchen',1260) if point=='cook' else Position('aft_deck',1660)
  v['coins']-=cost;v['paid'].append(point)
  from escort import plan
  v['escort']=plan(s,target,L._position_at_xy(pose.x,pose.y),point,now)
  return ActionResult(save(s,v),True,'Follow me. Stay close and keep quiet.')
 point_data=STORY_POINTS.get(point)
 if not point_data or s.position.zone!=point_data['zone'] or abs(s.position.value-point_data['x'])>point_data['reach']:return no('Move closer first.')
 if s.hidden_barrel or s.in_hammock:return no('Leave cover first.')
 if point.startswith('coins_'):
  if point in v['claimed']:return no('This cache is empty.')
  if kind!='inspect':return no('Open the cache with F.')
  v['claimed'].append(point);v['coins']+=1;return ActionResult(save(s,v),True,'You found one coin.')
 if point=='helm':
  if kind!='inspect' and s.reading!='confirm_takeover':return no('Use the helm with F.')
  if captain_ready(s):
   if now<s.alert_until_ms:return no('Wait until the search settles before commanding the crew.')
   return L.ActionResult(replace(s,ending='command',reading='',paused_at_ms=0),True,"All ahoy! We're heading home.")
  if L.opponents_remaining(s):return no('Defeat the remaining crew, or conceal the officer and wear the captain uniform.')
  return ActionResult(replace(s,ending='takeover',reading='',paused_at_ms=0,paused_total_ms=s.paused_total_ms+(max(0,wall-s.paused_at_ms) if s.paused_at_ms else 0)),True,'You take the helm.')
 if point=='lifeboat':
  if not boat_ready(s):return no('Find a sail and rope, or bring a sail and bribe the boatswain.')
  if kind=='finish':
   if s.reading!='confirm_dinghy':return no('Inspect the boat first.')
   return ActionResult(replace(s,ending='dinghy',reading='',paused_at_ms=0,paused_total_ms=s.paused_total_ms+max(0,wall-s.paused_at_ms)),True,'You sail for shore.')
  return ActionResult(replace(s,reading='confirm_dinghy',paused_at_ms=max(1,wall)),True,'Ready to lower the dinghy?')
 return no('Unknown action.')

def crew_tick(s,now,elapsed=0):
 from logic import ActionResult,Position,position_xy,guard_pose_at,GUARD_ROUTES,can_guard_see,route_points,STAIRS,_floor_zone
 v=progress(s)
 if s.ending or s.reading or s.capture_phase!='none':return ActionResult(s,False,'')
 if now-v.get('last_tick',0)<150:return ActionResult(s,False,'')
 before=v.get('last_tick',now);v['last_tick']=now;v.setdefault('watch_start',now)
 e=v.get('escort')
 if e:
  from escort import tick
  return tick(s,v,now,elapsed)
 if not v['armed']:
  pose,sleeping=watch_pose(s,'sleeper',now)
  x,y=position_xy(s.position)
  if s.sleeper_alive and not sleeping and not(s.disguised or s.hidden_barrel or s.in_hammock) and 12<=(x-pose.x)*pose.facing<=160 and abs(y-pose.y)<=25:
   s=replace(s,capture_phase='active',capture_guard='sleeper',capture_guard_zone=L._guard_position(0,'sleeper',s,now).zone,capture_guard_value=L._guard_position(0,'sleeper',s,now).value)
  return ActionResult(save(s,v),True,'')
 x,y=position_xy(s.position);shots=[];hit=False
 for b in v['shots']:
  if now-b['born']>3000:continue
  a=b['x']+b['dir']*320*max(0,before-b['born'])/1000;c=b['x']+b['dir']*320*max(0,now-b['born'])/1000
  top=y-(56 if v['duck'] else 80)
  vertical_hit=top-3<=b['y']<=y-3
  if now>=b['born'] and min(a,c)-12<=x<=max(a,c)+12 and vertical_hit and not(s.hidden_barrel or s.in_hammock):hit=True
  else:shots.append(b)
 v['shots']=shots
 for k in (*GUARD_ROUTES,'sleeper'):
  if not getattr(s,k+'_alive'):continue
  sleeping=False
  if k in ('sleeper','cargo'):pose,sleeping=watch_pose(s,k,now)
  else:pose=None
  pose=pose or guard_pose_at(s,k,elapsed,now)
  if sleeping or s.hidden_barrel or s.in_hammock:continue
  if abs(y-pose.y)>25 or not 12<=(x-pose.x)*pose.facing<=L.GUARD_STYLES.get(k,{'vision':160})['vision']*1.3:continue
  if now>=v['next_fire'].get(k,0):
   v['next_fire'][k]=now+2200
   v['shots'].append({'x':pose.x,'y':pose.y-64,'dir':pose.facing,'born':now+650})
 if hit:
  v['hp']-=1
  if v['hp']<=0:
   v['duck']=False
   s=replace(s,capture_phase='active',capture_guard='patrol',capture_guard_zone=s.position.zone,capture_guard_value=s.position.value,hidden_barrel='')
 return ActionResult(save(s,v),True,'Hit! Find cover or duck!' if hit else '')


def capture_heartbeat(s, now):
 from logic import ActionResult,capture_paths,finish_capture
 v=progress(s)
 if 'capture_started' not in v:
  v['capture_started']=now
  return ActionResult(save(s,v),True,'')
 approach,escort=capture_paths(s)
 length=lambda path:sum(math.dist(a,b) for a,b in zip(path,path[1:]))
 duration=(length(approach)/230+length(escort)/175)*1000+1000
 if now-v['capture_started']>=min(25000,duration):return finish_capture(s)
 return ActionResult(s,True,'')
