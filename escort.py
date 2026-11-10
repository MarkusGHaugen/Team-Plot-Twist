"""Timed guided movement between cover, with a farewell and a return to duty."""
import math
from dataclasses import replace
import logic as L

SPEED=85.

def distances(path):
 out=[0.]
 for a,b in zip(path,path[1:]):out.append(out[-1]+math.dist(a,b))
 return out

def plan(state,target,home,kind,now):
 base=L.route_points(state.position,target);path=[list(base[0])];covers=[0.]
 props=[L.position_xy(L.Position(z,x)) for _,z,x in (*L.BARRELS,*L.CRATES)]
 for a,b in zip(base,base[1:]):
  if a[1]==b[1]:
   points=sorted((p for p in props if p[1]==a[1] and min(a[0],b[0])+1<p[0]<max(a[0],b[0])-1),key=lambda p:abs(p[0]-a[0]))
   for p in points:
    if math.dist(path[-1],p)<1:continue
    path.append(list(p));covers.append(distances(path)[-1])
  if math.dist(path[-1],b)>0:path.append(list(b))
 total=distances(path)[-1]
 if total==0:path.append(list(path[-1]))
 covers.append(total)
 return {'kind':kind,'started':now,'path':path,'covers':sorted(set(covers)),
         'distance':0.,'target':0.,'updated':now,'paused':True,'hidden':True,
         'return_path':[list(p) for p in L.route_points(target,home)],
         'resume_elapsed':L._nearest_route_time('dining' if kind=='cook' else 'boatswain',*L.position_xy(home))}

def pose(e,now):
 from voyage import along
 distance=e.get('distance',0.)
 if not e.get('paused',False):distance=min(e.get('target',float('inf')),distance+max(0,now-e.get('updated',now))/1000*SPEED)
 total=distances(e['path'])[-1]
 return along(e['path'],distance/max(total,1))

def visible(state,xy,now,elapsed,exclude):
 for kind in (*L.GUARD_ROUTES,'sleeper'):
  if kind==exclude or not getattr(state,kind+'_alive'):continue
  if kind in ('cargo','sleeper'):
   from voyage import watch_pose
   p,sleeping=watch_pose(state,kind,now)
   if sleeping:continue
  else:p=None
  p=p or L.guard_pose_at(state,kind,elapsed,now)
  if p.segment=='feast_sleep':continue
  vision=L.GUARD_STYLES.get(kind,{'vision':160})['vision']
  if abs(xy[1]-p.y)<=L.VISION_HEIGHT and -14<=(xy[0]-p.x)*p.facing<=vision+20:return True
 return False

def clear_leg(state,e,start,end,now,elapsed):
 from voyage import along
 total=distances(e['path'])[-1];duration=max(0,(end-start)/SPEED)
 exclude='dining' if e['kind']=='cook' else 'boatswain'
 steps=max(1,math.ceil(duration/.35))
 for i in range(steps+1):
  dt=duration*i/steps;distance=start+dt*SPEED
  for offset in (0,24):
   xy=along(e['path'],min(total,distance+offset)/max(total,1))
   if visible(state,xy,now+int(dt*1000),elapsed+dt,exclude):return False
 return True

def position(xy):
 return L._position_at_xy(*xy)

def tick(state,v,now,elapsed):
 from voyage import save,along
 e=dict(v['escort']);total=distances(e['path'])[-1]
 # Old saved guides continue from their elapsed travel time.
 if 'distance' not in e:
  e.update(distance=min(total,max(0,now-e['started'])/1000*SPEED),target=total,updated=now,paused=False,hidden=False,covers=[0.,total],return_path=list(reversed(e['path'])),resume_elapsed=0.)
 if not e['paused']:
  e['distance']=min(e['target'],e['distance']+max(0,now-e['updated'])/1000*SPEED)
  if e['distance']>=e['target']-.01:e.update(paused=True,hidden=True)
 e['updated']=now
 if e['distance']>=total-.01:
  if e['kind']=='cook':
   import json
   p=L.story_progress(state);p['crate_open']=True;state=replace(state,story_state=json.dumps(p))
  v['guide']={'kind':e['kind'],'path':e['return_path'],'started':now+2200,'speech_until':now+2200,'resume_elapsed':e['resume_elapsed']}
  v.pop('escort',None)
  return L.ActionResult(save(replace(state,position=position(e['path'][-1]),reached_kitchen=state.reached_kitchen or position(e['path'][-1]).zone=='kitchen'),v),True,'Your guide wishes you luck.')
 if e['paused']:
  next_stop=next((x for x in e['covers'] if x>e['distance']+.01),total)
  if clear_leg(state,e,e['distance'],next_stop,now,elapsed):e.update(target=next_stop,paused=False,hidden=False)
 v['escort']=e
 xy=along(e['path'],e['distance']/max(total,1))
 state=replace(state,position=position(xy),reached_kitchen=state.reached_kitchen or position(xy).zone=='kitchen')
 return L.ActionResult(save(state,v),True,'')

def guard_override(state,kind,now):
 from voyage import progress,along
 v=progress(state);e=v.get('escort');g=v.get('guide')
 if e and kind==('dining' if e['kind']=='cook' else 'boatswain'):
  total=distances(e['path'])[-1];distance=e.get('distance',max(0,now-e['started'])/1000*SPEED)
  if not e.get('paused',False):distance=min(e.get('target',total),distance+max(0,now-e.get('updated',now))/1000*SPEED)
  x,y=along(e['path'],min(total,distance+24)/max(total,1));q=along(e['path'],min(total,distance+32)/max(total,1))
  return L.GuardPose(x,y,'guiding_wait' if e.get('paused') else 'guiding',0.,1 if q[0]>=x else -1)
 if g and kind==('dining' if g['kind']=='cook' else 'boatswain'):
  if state.alert_started_ms>g['started'] or v['armed']:return None
  total=distances(g['path'])[-1];travel=min(24,total)+max(0,(now-g['started'])/1000*SPEED)
  if travel>=total:
   if state.alert_started_ms>g['started']:return None
   return L.guard_pose_for(kind,g['resume_elapsed']+(travel-total)/SPEED)
  x,y=along(g['path'],travel/max(total,1))
  target=along(g['path'],min(total,travel+5)/max(total,1))
  return L.GuardPose(x,y,'guide_farewell' if now<g['speech_until'] else 'returning_to_post',0.,1 if target[0]>=x else -1)
 return None
