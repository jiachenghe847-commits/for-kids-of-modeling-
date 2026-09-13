"""Complete-service lookahead using public feedback and independent certificates."""
import importlib
import math
import time
import numpy as np
import rollout_kernel as kernel


DEFAULTS = dict(samples=65, search_rounds=6, optical_trigger=45., spacing=25.,
                safe_shift=False, small_cover=False, unified_route=False,
                negative_grid=False, ring_radius=900*math.sqrt(3), radius_mode='min',
                decision_budget_s=2., planning_budget_s=60., max_worlds=585)


def configuration(values):
    if not isinstance(values,dict) or set(values)-set(DEFAULTS):
        raise ValueError('Unknown rollout configuration')
    cfg = dict(DEFAULTS,**values)
    for name in ('samples','search_rounds','max_worlds'):
        if isinstance(cfg[name],bool) or not isinstance(cfg[name],int):
            raise ValueError(f'{name} must be an integer')
    if cfg['samples'] not in (17,33,65) or not 0 <= cfg['search_rounds'] <= 6 or not 1 <= cfg['max_worlds'] <= 585:
        raise ValueError('Invalid sampling/search limit')
    for name in ('safe_shift','small_cover','unified_route','negative_grid'):
        if not isinstance(cfg[name],bool):
            raise ValueError(f'{name} must be boolean')
    for name in ('optical_trigger','spacing','ring_radius','decision_budget_s','planning_budget_s'):
        if isinstance(cfg[name],bool) or not math.isfinite(cfg[name]) or cfg[name] < 0:
            raise ValueError(f'{name} must be finite and nonnegative')
    if not 0 < cfg['spacing'] < 20*math.sqrt(2) or cfg['optical_trigger'] <= 0:
        raise ValueError('Invalid optical geometry')
    if cfg['radius_mode'] not in ('min','mid','max'):
        raise ValueError('Invalid reception radius mode')
    r = cfg['ring_radius']
    if max(math.sqrt(t*t+r*r-2*t*r*math.cos(math.pi/6)) for t in (1000,1800)) >= 1000:
        raise ValueError('Ring lacks strict 1000m coverage certificate')
    return cfg


def halton(index,base):
    value, fraction = 0.,1.
    while index:
        fraction /= base
        index,digit = divmod(index,base)
        value += digit*fraction
    return value


def area_samples(poly,count):
    center = kernel.centroid(poly)
    triangles = [(center,a,b) for a,b in zip(poly,poly[1:]+poly[:1])]
    weights = [abs((a[0]-center[0])*(b[1]-center[1])-(a[1]-center[1])*(b[0]-center[0])) for _,a,b in triangles]
    total = sum(weights)
    points = [center]
    if total < 1e-9:
        a,b = max(((a,b) for a in poly for b in poly),key=lambda pair:kernel.distance(*pair))
        return points+[(a[0]+halton(i,2)*(b[0]-a[0]),a[1]+halton(i,2)*(b[1]-a[1])) for i in range(1,count)]
    cumulative = np.cumsum(weights)/total
    for i in range(1,count):
        _,a,b = triangles[min(len(triangles)-1,int(np.searchsorted(cumulative,halton(i,2))))]
        u,v = math.sqrt(halton(i,3)),halton(i,5)
        points.append(((1-u)*center[0]+u*(1-v)*a[0]+u*v*b[0],(1-u)*center[1]+u*(1-v)*a[1]+u*v*b[1]))
    return points


def worlds_for(poly,history,failed,directional,cfg):
    """Filter actual disk, bearing, clear, near, radius and emitting-half-plane feedback."""
    strata = []
    normals = [(0.,0.)]+[(math.cos(k*math.tau/24),math.sin(k*math.tau/24)) for k in range(24)] if directional else [(0.,0.)]
    for source in area_samples(poly,cfg['samples']):
        if math.hypot(*source) > 1800+1e-8 or any(kernel.distance(source,p) <= 20+1e-9 for p in failed):
            continue
        alternatives = []
        for normal in normals:
            lower,upper = 1000.,1500.
            compatible = True
            for x,y,kind,angle in history:
                d = kernel.distance(source,(x,y))
                visible = (x-source[0])*normal[0]+(y-source[1])*normal[1] >= -1e-9
                if kind in ('direction','near'):
                    delta = abs((math.degrees(math.atan2(source[1]-y,source[0]-x))-angle+180)%360-180)
                    if not visible or (kind=='direction' and (d<=5 or delta>1.005+1e-8)) or (kind=='near' and d>5+1e-9):
                        compatible = False
                        break
                    lower = max(lower,d-1e-9)
                elif visible:
                    upper = min(upper,d-2e-9)
            if not compatible or lower > upper:
                continue
            radius = {'min':lower,'mid':(lower+upper)/2,'max':upper}[cfg['radius_mode']]
            for error in (-1.,0.,1.):
                alternatives.append((*source,radius,*normal,error))
        if alternatives:
            strata.append(alternatives)
    # Round robin across positions, with deterministic orientation/error strata.
    result = []
    for level in range(max(map(len,strata),default=0)):
        for i,values in enumerate(strata):
            if level < len(values):
                result.append(values[(level+i*3)%len(values)])
                if len(result) == cfg['max_worlds']:
                    return result
    return result


def open_route(start,points,improve=True):
    if not points:
        return []
    p = np.asarray(points,float)
    distances = np.linalg.norm(p[:,None,:]-p[None,:,:],axis=2)
    initial = np.linalg.norm(p-np.asarray(start),axis=1)
    def length(order):
        return float(initial[order[0]]+sum(distances[a,b] for a,b in zip(order,order[1:])))
    orders = []
    starts = sorted(range(len(p)),key=lambda i:(initial[i],i))[:min(4,len(p))] if improve else [int(initial.argmin())]
    for first in starts:
        order, left = [first],set(range(len(p)))-{first}
        while left:
            i = min(left,key=lambda i:(distances[order[-1],i],i))
            order.append(i)
            left.remove(i)
        orders.append(order)
    if improve:
        angle = sorted(range(len(p)),key=lambda i:math.atan2(p[i,1]-start[1],p[i,0]-start[0]))
        orders.extend([angle,angle[::-1]])
    route = min(orders,key=length)
    for _ in range(5 if improve else 0):
        best, value = route,length(route)
        for i in range(len(route)):
            for j in range(i+1,len(route)):
                candidate = route[:i]+route[i:j+1][::-1]+route[j+1:]
                score = length(candidate)
                if score < value-1e-7:
                    best,value = candidate,score
        for i in range(len(route)):
            rest = route[:i]+route[i+1:]
            for j in range(len(route)):
                candidate = rest[:j]+[route[i]]+rest[j:]
                score = length(candidate)
                if score < value-1e-7:
                    best,value = candidate,score
        if best == route:
            break
        route = best
    return route


class NegativeGrid:
    """20m cells intersecting the actual source disk; delete only whole cells."""
    def __init__(self):
        cells = []
        for i in range(-90,90):
            for j in range(-90,90):
                x,y = max(i*20,min(0,(i+1)*20)),max(j*20,min(0,(j+1)*20))
                if x*x+y*y <= 1800**2:
                    cells.append((i*20+10,j*20+10))
        self.centers = np.asarray(cells,float)
        self.remaining = {}

    def observe(self,channel,point):
        cells = self.remaining.setdefault(channel,np.ones(len(self.centers),dtype=bool))
        far = np.abs(self.centers-np.asarray(point))+10
        cells[np.sum(far*far,axis=1) < (1000-1e-7)**2] = False

    def empty(self,channel):
        return channel in self.remaining and not self.remaining[channel].any()


class RolloutScheduler:
    def __init__(self,policy):
        self.p = policy
        self.cfg = configuration(policy.rollout_config)
        policy.rollout_config = self.cfg
        self.backend = kernel
        if policy.rollout_backend == 'cpp':
            self.backend = importlib.import_module('_rollout_cpp')
        elif policy.rollout_backend == 'auto':
            from rollout_runtime import native_backend
            self.backend = native_backend() or kernel
        policy.rollout_actual_backend = 'cpp' if self.backend is not kernel else 'python'
        self.rounds = {}
        self.planning = 0.
        self.negative = NegativeGrid() if self.cfg['negative_grid'] and not policy.directional else None

    def history(self,channel):
        return [(a['point'][0],a['point'][1],a['response']['measure_result'],a['response'].get('svd_deg',0.))
                for a in self.p.action_trace if a['channel']==channel and a['action']=='measure']

    def candidate_points(self,poly,received,bearing,used):
        center,radius = kernel.circle(poly)
        angle = math.radians(bearing)
        along,side = (math.cos(angle),math.sin(angle)),(-math.sin(angle),math.cos(angle))
        step = max(0.,sum((center[k]-received[k])*along[k] for k in (0,1)))
        forward = tuple(received[k]+step*along[k] for k in (0,1))
        scale = min(180.,max(20.,radius*.45))
        delta = np.asarray(poly)-np.asarray(center)
        _,vectors = np.linalg.eigh(delta.T@delta)
        lateral = vectors[:,0]
        points = [forward,tuple(forward[k]+20*side[k] for k in (0,1)),tuple(forward[k]-20*side[k] for k in (0,1)),
                  kernel.centroid(poly),area_samples(poly,17)[1],area_samples(poly,17)[8],
                  tuple(center[k]+scale*lateral[k] for k in (0,1)),tuple(center[k]-scale*lateral[k] for k in (0,1))]
        unique = []
        for point in points:
            if all(kernel.distance(point,p)>1 for p in used+unique):
                unique.append(point)
        return unique[:8]

    def decide(self,channel,next_point):
        p,cfg = self.p,self.cfg
        started = time.monotonic()
        allowance = min(cfg['decision_budget_s'], max(0.,cfg['planning_budget_s']-self.planning))
        session_deadline = getattr(p.robot,'deadline',None)
        if session_deadline is not None:
            allowance = min(allowance,max(0.,session_deadline-started-30))
        deadline = started+allowance
        track = p.tracks[channel]
        poly = [tuple(x) for x in track['polygon']]
        history = self.history(channel)
        received, bearing = p.observations[channel][-1]
        received = tuple(received)
        used = [h[:2] for h in history]
        failed = [tuple(x) for x in p.failed_clear_points.get(channel,[])]
        rounds = self.rounds.get(channel,0)
        start = tuple(p.robot.position)
        action,point = kernel.fixed_action(poly,start,bearing,received,used,failed,rounds,next_point,cfg)
        scores,worlds = [],[]
        reason = 'fixed_budget_fallback'
        if allowance > 0 and action != 'certified_clear':
            worlds = worlds_for(poly,history,failed,p.directional,cfg)
            if not worlds:
                reason = 'fixed_no_compatible_sampled_worlds'
            else:
                cache = set()
                def score(kind,position):
                    k = kind,kernel.key(position)
                    if k in cache or time.monotonic()>=deadline:
                        return False
                    cache.add(k)
                    result = self.backend.evaluate(poly,start,p.robot.channel,channel,bearing,received,history,
                        failed,rounds,worlds,kind,position,next_point,cfg,deadline)
                    if result is None:
                        return False
                    scores.append(dict(action=kind,point=list(position),**result))
                    return True
                completed = score(action,point)
                if completed and action=='probe':
                    covering = kernel.optical(poly,bearing,cfg['spacing'],cfg['small_cover'])
                    remaining = [x for x in covering if all(kernel.distance(x,f)>1e-7 for f in failed)]
                    if remaining:
                        score('optical',min(remaining,key=lambda x:kernel.rank_distance(kernel.distance(x,start))))
                if completed and rounds < 12:
                    for candidate in self.candidate_points(poly,received,bearing,used):
                        if not score('probe',candidate):
                            break
                    step = min(80.,max(20.,kernel.circle(poly)[1]/4))
                    for _ in range(cfg['search_rounds']):
                        probes = [r for r in scores if r['action']=='probe']
                        if not probes or time.monotonic()>=deadline:
                            break
                        best = min(probes,key=lambda r:r['mean_s'])['point']
                        for dx,dy in ((step,0),(-step,0),(0,step),(0,-step)):
                            if not score('probe',(best[0]+dx,best[1]+dy)):
                                break
                        step /= 2
                if scores:
                    best = min(scores,key=lambda r:r['mean_s'])
                    action,point = best['action'],tuple(best['point'])
                    reason = 'complete_rollout_minimum' if time.monotonic()<deadline else 'complete_candidate_budget_fallback'
        elif action=='certified_clear':
            reason = 'certified_clear'
        elapsed = time.monotonic()-started
        self.planning += elapsed
        decision = dict(reason=reason,action=action,point=list(point),channel=channel,
                        next_point=list(next_point) if next_point is not None else None,
                        decision_wall_s=elapsed,world_count=len(worlds),candidate_scores=scores,
                        planning_wall_s=self.planning,backend=p.rollout_actual_backend)
        p.rollout_decisions.append(decision)
        return action,point,decision

    def run(self,points):
        p = self.p
        if not p.directional and p.grid=='ring':
            r = self.cfg['ring_radius']
            points = [np.zeros(2)]+[r*np.array([math.cos(k*math.pi/3),math.sin(k*math.pi/3)]) for k in range(6)]
        p.pending_nodes = {c:set(range(len(points))) for c in range(1,21)}
        while len(p.cleared)<16:
            nodes = []
            for i,point in enumerate(points):
                channels = [c for c in range(1,21) if c not in p.cleared and c not in p.tracks and i in p.pending_nodes[c]]
                if channels:
                    channel = min(channels,key=lambda c:(c!=p.robot.channel,c))
                    nodes.append(('survey',i,tuple(point),channel))
            for c in sorted(p.tracks):
                if c not in p.cleared:
                    nodes.append(('target',c,kernel.centroid([tuple(x) for x in p.tracks[c]['polygon']]),c))
            if not nodes:
                break
            if self.cfg['unified_route']:
                order = open_route(p.robot.position,[n[2] for n in nodes])
            else:
                # Local service first; the original seven/25-point certificate remains.
                targets = [i for i,n in enumerate(nodes) if n[0]=='target']
                first = min(targets or list(range(len(nodes))),key=lambda i:kernel.distance(nodes[i][2],p.robot.position))
                rest = [i for i in range(len(nodes)) if i!=first]
                order = [first]+sorted(rest,key=lambda i:kernel.distance(nodes[first][2],nodes[i][2]))
            kind,index,point,channel = nodes[order[0]]
            next_point = nodes[order[1]][2] if len(order)>1 else None
            if kind=='survey':
                p.phase = 'rollout_survey'
                p.decision = dict(reason='discovery_certificate',next_point=next_point,node=index)
                if kernel.distance(p.robot.position,point)>1e-7 or not p.action_trace:
                    p.coverage_visits += 1
                response = p.measure(point,channel)
                p.pending_nodes[channel].discard(index)
                if self.negative and response['measure_result']=='no_signal':
                    self.negative.observe(channel,point)
                    if self.negative.empty(channel):
                        p.pending_nodes[channel].clear()
            else:
                action,point,p.decision = self.decide(channel,next_point)
                p.phase = 'rollout_'+action
                if action=='probe':
                    self.rounds[channel] = self.rounds.get(channel,0)+1
                    p.supplemental_measures += 1
                    response = p.measure(point,channel)
                    if self.negative and response['measure_result']=='no_signal':
                        self.negative.observe(channel,point)
                else:
                    if action=='optical':
                        p.fallbacks += 1
                    success = p.clear(point,channel)
                    if action=='certified_clear' and not success:
                        raise RuntimeError('Certified clear contradicted')
            p.replans += 1
        unresolved = [c for c,nodes in p.pending_nodes.items() if c not in p.cleared and (c in p.tracks or nodes)]
        if len(p.cleared)<16 and unresolved:
            raise RuntimeError(f'Incomplete channel certificates: {unresolved}')
        return 'known upper bound of 16 sources reached' if len(p.cleared)==16 else 'per-channel discovery certificates and localization complete'
