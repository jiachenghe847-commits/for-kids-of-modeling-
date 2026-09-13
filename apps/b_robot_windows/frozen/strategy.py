"""Coverage certificate + bounded-error localization + optical-cover fallback."""
from __future__ import annotations
import math
import numpy as np
from geometry import circle_outer,clip,wedge,restrict_disk,enclosing_circle,second_point,optical_cover
from search_coverage import triangular_grid,omnidirectional_ring,compact_directional_grid,DirectionalCertificate

BUILD_VERSION='v9-rollout-review-1'

def discovery_grid(directional=False):
    """All corners of cells intersecting the target disk.

    Omni h=1300: nearest corner <=h/sqrt(2)<1000.
    Directional h=700: every corner <=h*sqrt(2)<1000; at least one is in
    each closed 180-degree sector because the source is in their convex hull.
    """
    h=700 if directional else 1300
    lo=math.floor(-1800/h);hi=math.ceil(1800/h);points=set()
    for i in range(lo,hi):
        for j in range(lo,hi):
            x0,y0=i*h,j*h;x1,y1=x0+h,y0+h
            nearest_x=max(x0,min(0,x1));nearest_y=max(y0,min(0,y1))
            if nearest_x**2+nearest_y**2<=1800**2:
                points.update(((x0,y0),(x0,y1),(x1,y0),(x1,y1)))
    points.add((0,0))
    return [np.array(p,float) for p in sorted(points)]

class Strategy:
    route_detour_m=1000.
    def __init__(self,robot,directional=False,baseline=False,grid='triangle',early_clears=3,localize_batch=3,scheduler='adaptive',joint_config=None,rollout_config=None,rollout_backend='auto'):
        if scheduler not in ('adaptive', 'legacy', 'joint', 'time_probe', 'rollout'):
            raise ValueError('Unknown scheduler')
        if localize_batch < 0 or early_clears < 0:
            raise ValueError('Batch and early clear limits must be nonnegative')
        self.robot=robot;self.directional=directional;self.baseline=baseline
        self.cleared=set();self.tracks={};self.measures=0;self.clear_attempts=0;self.fallbacks=0
        self.probe_positions={};self.coverage_visits=0
        self.grid=grid;self.early_clears=early_clears;self.localize_batch=localize_batch;self.failed_clear_points={}
        self.scheduler='legacy' if baseline else scheduler
        self.observations={};self.phase='localization';self.pending_nodes={}
        self.costs={'movement_s':0.,'measurement_s':0.,'switching_s':0.,'successful_clear_s':0.,'failed_clear_s':0.}
        self.phase_costs={};self.no_signals=0
        self.pruned_nodes=0;self.replans=0;self.supplemental_measures=0
        self.joint_config=joint_config or {};self.action_trace=[];self.decision=None
        if rollout_backend not in ('python','cpp','auto'):raise ValueError('Unknown rollout backend')
        self.rollout_config=rollout_config or {};self.rollout_backend=rollout_backend
        self.rollout_actual_backend=None;self.rollout_decisions=[]
    def _trace(self,point,channel,action,response):
        self.action_trace.append(dict(index=len(self.action_trace),point=np.asarray(point).tolist(),
            channel=channel,action=action,response=dict(response),decision=self.decision or {'reason':self.phase},
            virtual_time_s=self.robot.virtual_time))
    def _record_cost(self,point,action,channel,success=False):
        movement=float(np.linalg.norm(np.asarray(point)-self.robot.position))/5
        costs={'movement_s':movement}
        if action=='measure':costs.update(measurement_s=5.,switching_s=float(channel!=self.robot.channel))
        else:costs['successful_clear_s' if success else 'failed_clear_s']=5. if success else 3.
        return costs
    def _add_cost(self,costs):
        for key,value in costs.items():self.costs[key]+=value
        self.phase_costs[self.phase]=self.phase_costs.get(self.phase,0.)+sum(costs.values())
    def measure(self,point,channel):
        costs=self._record_cost(point,'measure',channel)
        response=self.robot.measure(tuple(point),channel);self.measures+=1
        self._trace(point,channel,'measure',response)
        self._add_cost(costs)
        self.probe_positions.setdefault(channel,[]).append(np.asarray(point).copy())
        kind=response['measure_result']
        if kind=='near':
            if not self.clear(point,channel):raise RuntimeError('Near response contradicted by optical clear')
        elif kind=='direction':
            angle=float(response['svd_deg'])
            self.observations.setdefault(channel,[]).append((np.asarray(point,float).copy(),angle))
            old=self.tracks.get(channel)
            polygon=old['polygon'] if old else circle_outer()
            a,b=wedge(point,angle);polygon=restrict_disk(clip(polygon,a,b),point,1500)
            if len(polygon)==0:raise RuntimeError(f'Inconsistent bearing constraints for channel {channel}')
            self.tracks[channel]={'polygon':polygon,'first':old['first'] if old else np.asarray(point),
                                  'bearing':old['bearing'] if old else angle}
        elif kind=='no_signal':self.no_signals+=1
        else:raise RuntimeError(f'Unknown measure result {kind}')
        return response
    def clear(self,point,channel):
        costs=self._record_cost(point,'clear',channel)
        response=self.robot.clear(tuple(point),channel);self.clear_attempts+=1
        self._trace(point,channel,'clear',response)
        if response['clear_result']=='success':
            costs.pop('failed_clear_s');costs['successful_clear_s']=5.
        self._add_cost(costs)
        if response['clear_result']=='success':self.cleared.add(channel);return True
        if response['clear_result']!='no_target_in_range':raise RuntimeError('Unknown clear result')
        self.failed_clear_points.setdefault(channel,[]).append(np.asarray(point).copy())
        return False
    def try_optical(self,channel,limit=None):
        track=self.tracks[channel];failed=self.failed_clear_points.get(channel,[])
        candidates=[p for p in optical_cover(track['polygon'],track['bearing'])
                    if not any(np.linalg.norm(p-old)<1e-7 for old in failed)]
        attempts=0
        while candidates and (limit is None or attempts<limit):
            current=np.asarray(self.robot.position)
            i=min(range(len(candidates)),key=lambda k:np.linalg.norm(candidates[k]-current))
            attempts+=1
            if self.clear(candidates.pop(i),channel):return True
        return False
    def localize(self,channel):
        if self.scheduler=='adaptive':
            center,radius=enclosing_circle(self.tracks[channel]['polygon'])
            if radius<=19.8:
                if not self.clear(center,channel):raise RuntimeError('Certified optical cover contradicted by simulator')
                return
        # A few near-end optical checks can avoid driving behind a directional source.
        # Every failed check is included in cost; this is not an optimality claim.
        if self.directional and not self.baseline and self.early_clears:
            if self.try_optical(channel,self.early_clears):return
        probes=0 if self.baseline else 3
        for _ in range(probes):
            if channel in self.cleared:return
            track=self.tracks[channel];polygon=track['polygon'];center,radius=enclosing_circle(polygon)
            if radius<=19.8:
                if not self.clear(center,channel):raise RuntimeError('Certified optical cover contradicted by simulator')
                return
            candidate,_=second_point(polygon,np.asarray(self.robot.position),track['bearing'])
            used=self.probe_positions.get(channel,[])
            if any(np.linalg.norm(candidate-p)<1 for p in used):
                # A different location, not repeated measurements of the fixed local error.
                angle=math.radians(track['bearing']);v=np.array([-math.sin(angle),math.cos(angle)])
                candidate=center+((-1)**len(used))*min(120,max(radius/2,25))*v
            self.measure(candidate,channel)
        if channel in self.cleared:return
        self.fallbacks+=1
        if self.try_optical(channel):return
        raise RuntimeError('Exhaustive optical covering failed: bounds/protocol require investigation')
    def _route(self,points):
        """Nearest-neighbour coverage route followed by deterministic 2-opt."""
        points=[np.asarray(p,float) for p in points];start=np.asarray(self.robot.position,float);left=list(range(len(points)));route=[];current=start
        while left:
            i=min(left,key=lambda k:np.linalg.norm(points[k]-current));route.append(i);current=points[i];left.remove(i)
        def length(order):
            return float(np.linalg.norm(points[order[0]]-start)+sum(np.linalg.norm(points[b]-points[a]) for a,b in zip(order,order[1:]))) if order else 0.
        improved=True
        while improved:
            improved=False;best=length(route)
            for i in range(1,len(route)-1):
                for j in range(i+1,len(route)):
                    candidate=route[:i]+route[i:j+1][::-1]+route[j+1:];value=length(candidate)
                    if value<best-1e-7:route,best,improved=candidate,value,True
        return [points[i] for i in route]
    def _localize_pending(self,limit=None):
        pending=[c for c in self.tracks if c not in self.cleared];done=0
        while pending and (limit is None or done<limit):
            current=np.asarray(self.robot.position)
            channel=min(pending,key=lambda c:np.linalg.norm(self.tracks[c]['polygon'].mean(axis=0)-current))
            self.localize(channel);pending.remove(channel);done+=1
    def _grid_points(self):
        if self.grid=='compact':points=compact_directional_grid(self.directional)
        elif self.grid=='ring':
            if self.directional:raise ValueError('Omnidirectional ring is not a directional coverage certificate')
            points=omnidirectional_ring()
        else:points=triangular_grid(self.directional) if self.grid=='triangle' else discovery_grid(self.directional)
        return points
    def _run_legacy(self,points):
        points=self._route(points)
        while points and len(self.cleared)<16:
            current=np.asarray(self.robot.position);i=min(range(len(points)),key=lambda k:np.linalg.norm(points[k]-current))
            point=points.pop(i);self.coverage_visits+=1
            channels=[c for c in range(1,21) if c not in self.cleared]
            if self.robot.channel in channels:
                channels.remove(self.robot.channel);channels.insert(0,self.robot.channel)
            for channel in channels:self.measure(point,channel)
            self._localize_pending(self.localize_batch)
        self._localize_pending(None)
        return 'all coverage nodes visited' if not points else 'known upper bound of 16 sources reached'

    def _service_on_route(self,next_point):
        attempted={}
        while True:
            current=np.asarray(self.robot.position)
            options=[]
            for channel,track in self.tracks.items():
                if channel in self.cleared:continue
                center,radius=enclosing_circle(track['polygon'])
                detour=np.linalg.norm(center-current)
                if next_point is not None:
                    detour+=np.linalg.norm(center-next_point)-np.linalg.norm(current-next_point)
                if radius<=19.8 and (next_point is None or detour<=400):
                    options.append((float(detour)/5+5,channel,center,'clear'))
                elif detour<=self.route_detour_m:
                    options.append((float(detour+2*radius)/5+20,channel,center,'localize'))
                elif self.directional and attempted.get(channel,0)<self.early_clears:
                    failed=self.failed_clear_points.get(channel,[])
                    for point in optical_cover(track['polygon'],track['bearing']):
                        if any(np.linalg.norm(point-old)<1e-7 for old in failed):continue
                        extra=np.linalg.norm(point-current)
                        if next_point is not None:extra+=np.linalg.norm(point-next_point)-np.linalg.norm(current-next_point)
                        if extra<=150:
                            options.append((float(extra)/5+3,channel,point,'optical'))
            if not options:return
            _,channel,center,action=min(options,key=lambda row:(row[0],row[1]))
            self.phase='on_route_clear'
            if action=='localize':self.localize(channel)
            elif action=='optical':
                self.clear(center,channel);attempted[channel]=attempted.get(channel,0)+1
            elif not self.clear(center,channel):raise RuntimeError('Certified optical cover contradicted by simulator')

    def _run_adaptive(self,points):
        points=self._route(points)
        certificate=DirectionalCertificate(points) if self.directional else None
        self.pending_nodes={c:set(range(len(points))) for c in range(1,21)}
        remaining=list(range(len(points)))
        while remaining:
            if len(self.cleared)==16:break
            if self.directional:
                nearest=min(remaining,key=lambda j:np.linalg.norm(points[j]-self.robot.position))
                remaining.remove(nearest);i=nearest
            else:i=remaining.pop(0)
            point=points[i]
            channels=[]
            for channel in range(1,21):
                if channel in self.cleared:continue
                if channel not in self.tracks:
                    if i in self.pending_nodes[channel]:channels.append(channel)
                    continue
                poly=self.tracks[channel]['polygon']
                if certificate is not None:
                    before=len(self.pending_nodes[channel])
                    self.pending_nodes[channel].intersection_update(certificate.relevant_nodes(poly))
                    self.pruned_nodes+=before-len(self.pending_nodes[channel])
                if i not in self.pending_nodes[channel]:continue
                if enclosing_circle(poly)[1]<=19.8:continue
                if not len(restrict_disk(poly,point,1500)):continue
                if any(np.linalg.norm(point-used)<25 for used in self.probe_positions[channel]):continue
                channels.append(channel)
            if self.robot.channel in channels:
                channels.remove(self.robot.channel);channels.insert(0,self.robot.channel)
            if channels:self.coverage_visits+=1
            self.phase='survey'
            for channel in channels:
                if channel in self.tracks:self.supplemental_measures+=1
                self.measure(point,channel)
                self.pending_nodes[channel].discard(i)
            if self.directional and np.linalg.norm(point)>1800:
                self.phase='boundary_localization'
                self._localize_pending(self.localize_batch)
            else:self._service_on_route(points[remaining[0]] if remaining else None)
            if remaining and np.linalg.norm(np.asarray(self.robot.position)-point)>250:
                self.replans+=1
                routed=self._route([points[j] for j in remaining])
                remaining=[min(remaining,key=lambda j:np.linalg.norm(points[j]-p)) for p in routed]
        self.phase='localization'
        self._localize_pending(None)
        unresolved=[c for c,nodes in self.pending_nodes.items() if c not in self.cleared and (c in self.tracks or nodes)]
        if len(self.cleared)<16 and unresolved:raise RuntimeError(f'Incomplete channel certificates: {unresolved}')
        return 'known upper bound of 16 sources reached' if len(self.cleared)==16 else 'per-channel discovery certificates and localization complete'

    def run(self):
        points=self._grid_points()
        if self.scheduler=='rollout':
            from rollout_strategy import RolloutScheduler
            basis=RolloutScheduler(self).run(points)
        elif self.scheduler in ('joint','time_probe'):
            from joint_strategy import JointScheduler
            joint=JointScheduler(self)
            points=joint.points(points)
            basis=joint.run(points)
        else:basis=self._run_adaptive(points) if self.scheduler=='adaptive' else self._run_legacy(points)
        return {'cleared_count':len(self.cleared),'cleared_channels':sorted(self.cleared),
                'virtual_time_s':self.robot.virtual_time,'average_time_s':self.robot.virtual_time/len(self.cleared) if self.cleared else None,
                'measurements':self.measures,'clear_attempts':self.clear_attempts,'fallbacks':self.fallbacks,
                'coverage_visits':self.coverage_visits,'grid':self.grid,'early_clears':self.early_clears,
                'localize_batch':self.localize_batch,'scheduler':self.scheduler,
                'build_version':BUILD_VERSION,
                'joint_config':self.joint_config,'action_trace':self.action_trace,
                'rollout_config':self.rollout_config,'rollout_backend':self.rollout_actual_backend,
                'rollout_requested_backend':self.rollout_backend,'rollout_decisions':self.rollout_decisions,
                'full_survey_reference':{'nodes':len(points),'channels':20,
                    'measurements':len(points)*20,'measurement_and_switching_s':len(points)*119,
                    'scope':'Reference for scanning all 20 channels at every node with the current channel first; not an adaptive lower bound'},
                'cost_breakdown_s':self.costs,'phase_costs_s':self.phase_costs,'no_signal_measurements':self.no_signals,
                'pruned_known_channel_nodes':self.pruned_nodes,'route_replans':self.replans,
                'supplemental_survey_measurements':self.supplemental_measures,
                'scheduler_settings':{'localization_detour_m':self.route_detour_m,
                    'certified_clear_detour_m':400.,'optical_detour_m':150.,'replan_displacement_m':250.},
                'channel_remaining_nodes':{str(c):sorted(nodes) for c,nodes in self.pending_nodes.items() if c not in self.cleared},
                'completion_basis':basis}
