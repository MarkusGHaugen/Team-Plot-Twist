from dataclasses import replace
import json
from logic import initial_state,Position,shoot_guard,story_progress,GUARD_ROUTES
from voyage import voyage_action,crew_tick,watch_pose

def armed_player():
 s=replace(initial_state(),has_key=True,door_open=True,has_blue_key=True,chest_open=True,has_pistol=True,held_item='pistol',position=Position('hold',600),facing='right',disguised=True,wardrobe_contents='player_clothes')
 return s

def test_even_a_distant_shot_arms_every_living_guard():
 s=armed_player()
 for k in GUARD_ROUTES:s=replace(s,**{k+'_alive':False,k+'_corpse_x':2000.,k+'_corpse_y':245.})
 shot=shoot_guard(s,0,1000)
 assert shot.accepted and story_progress(shot.state)['voyage']['armed']
 p,sleeping=watch_pose(shot.state,'sleeper',1100)
 assert not sleeping and p.segment!='sleep'

def test_space_stance_action_toggles_on_stairs_and_survives_release():
 s=replace(armed_player(),position=Position('lower_stair',.5))
 first=voyage_action(s,'toggle_duck','',1000)
 assert first.accepted and story_progress(first.state)['voyage']['duck']
 second=voyage_action(first.state,'toggle_duck','',1100)
 assert second.accepted and not story_progress(second.state)['voyage']['duck']

def test_ducking_uses_a_smaller_hitbox_instead_of_immunity():
 s=armed_player()
 def scene(height):
  return replace(s,story_state=json.dumps({'voyage':{'armed':True,'duck':True,'last_tick':1000,'shots':[{'x':580,'y':500-height,'dir':1,'born':1000}]}}))
 assert story_progress(crew_tick(scene(64),1200).state)['voyage']['hp']==2
 assert story_progress(crew_tick(scene(20),1200).state)['voyage']['hp']==1


def test_each_living_guard_can_fire_at_the_disguised_prisoner():
 from logic import guard_pose_at,position_xy,_floor_zone
 for kind in (*GUARD_ROUTES,'sleeper'):
  s=replace(armed_player(),story_state=json.dumps({'voyage':{'armed':True,'watch_start':1000}}))
  pose=guard_pose_at(s,kind,0,2000)
  x=pose.x+80*pose.facing
  s=replace(s,position=Position(_floor_zone(pose.y,x),x))
  result=crew_tick(s,2000,0)
  v=story_progress(result.state)['voyage']
  assert kind in v['next_fire'],kind
  assert any(b['x']==pose.x and b['y']==pose.y-64 for b in v['shots']),kind
