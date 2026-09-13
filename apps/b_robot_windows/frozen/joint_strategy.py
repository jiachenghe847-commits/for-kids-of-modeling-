"""One-action replanning; finite lookahead ranks actions, never certifies cover."""
import math
import numpy as np
from geometry import clip, wedge, enclosing_circle, optical_cover, restrict_disk
from search_coverage import DirectionalCertificate


DEFAULTS = dict(ring_radius=900*math.sqrt(3), survey_bias_s=40.,
                tail_weight=1., max_probes=3, reception_weight=1.)


class JointScheduler:
    def __init__(self, policy):
        self.p = policy
        self.cfg = dict(DEFAULTS, **policy.joint_config)
        if set(self.cfg) != set(DEFAULTS):raise ValueError('Unknown joint configuration')
        if any(not math.isfinite(float(v)) or v < 0 for v in self.cfg.values()):
            raise ValueError('Joint settings must be finite and nonnegative')
        if int(self.cfg['max_probes']) != self.cfg['max_probes']:raise ValueError('Integer probe limit required')
        policy.joint_config = self.cfg
        self.probes = {};self.cache = {};self.cover_cache = {};self.tail_cache = {};self.pruned_at = {}

    def points(self, original):
        if self.p.directional or self.p.grid != 'ring':return original
        r = self.cfg['ring_radius']
        # On each nearest-node angular cell the endpoint squared distances
        # bound the annulus; the central disk covers rho <= 1000.
        worst = max(math.sqrt(t*t+r*r-2*t*r*math.cos(math.pi/6)) for t in (1000,1800))
        if worst >= 1000:raise ValueError('Ring lacks a strict 1000m reception certificate')
        return [np.zeros(2)]+[r*np.array([math.cos(k*math.pi/3),math.sin(k*math.pi/3)]) for k in range(6)]

    def region(self, channel):
        p = self.p;key = (channel,len(p.observations[channel]))
        if key not in self.cache:
            poly=p.tracks[channel]['polygon'];center,radius=enclosing_circle(poly)
            self.cache[key]=(center,radius)
        return self.cache[key]

    def cover(self, channel):
        p=self.p;key=(channel,len(p.observations[channel]))
        if key not in self.cover_cache:
            self.cover_cache[key]=optical_cover(p.tracks[channel]['polygon'],p.tracks[channel]['bearing'])
        failed=p.failed_clear_points.get(channel,[])
        return [x for x in self.cover_cache[key] if not any(np.linalg.norm(x-y)<1e-7 for y in failed)]

    def tail(self, poly):
        # Length and width proxy for a full square-cell optical sweep.
        # This is a ranking estimate only; actual fallback enumerates every cell.
        if not len(poly):return 0.
        extent=np.ptp(poly,axis=0);length=float(np.linalg.norm(extent))
        area=abs(float(np.sum(poly[:,0]*np.roll(poly[:,1],-1)-poly[:,1]*np.roll(poly[:,0],-1))))/2
        cells=max(1.,length/25+area/625)
        return 5.+cells*4.

    def candidates(self, channel, next_point):
        p=self.p;center,radius=self.region(channel);current=np.asarray(p.robot.position)
        angle=math.radians(p.tracks[channel]['bearing']);side=np.array([-math.sin(angle),math.cos(angle)])
        scale=min(180.,max(30.,radius*.45))
        candidates=[center,center+scale*side,center-scale*side,current]
        if next_point is not None:
            edge=next_point-current;den=float(edge@edge)
            candidates.extend([next_point,current+np.clip(float((center-current)@edge)/den,0,1)*edge] if den>1e-8 else [next_point])
        if p.directional:
            for received,_ in p.observations[channel][-2:]:
                toward=center-received;dist=np.linalg.norm(toward)
                candidates.extend([received+.65*toward,received+min(80.,dist*.2)*side,
                                   received-min(80.,dist*.2)*side])
        unique=[]
        for x in candidates:
            if any(np.linalg.norm(x-y)<10 for y in p.probe_positions.get(channel,[])+unique):continue
            unique.append(x)
        return unique

    def probe_tail(self, channel, point):
        p=self.p;poly=p.tracks[channel]['polygon'];center,_=self.region(channel)
        key=(channel,len(p.observations[channel]),tuple(point))
        if key in self.tail_cache:return self.tail_cache[key]
        samples=np.vstack([poly[np.linspace(0,len(poly)-1,min(4,len(poly)),dtype=int)],center])
        prior=self.tail(poly);values=[]
        for source in samples:
            delta=source-point;distance=np.linalg.norm(delta)
            if distance>1000:values.append(prior);continue
            if distance<=5:values.append(5.);continue
            reception=1.
            if p.directional:
                # Enumerate orientations consistent with positive observations.
                phi=np.arange(0,360,15)*math.pi/180
                normals=np.c_[np.cos(phi),np.sin(phi)]
                good=np.ones(len(phi),bool)
                for received,_ in p.observations[channel]:good &= (normals@(received-source)>=-1e-7)
                reception=float(np.mean(normals[good]@(point-source)>=-1e-7)) if good.any() else .5
                reception=reception**self.cfg['reception_weight']
            estimates=[]
            truth=math.degrees(math.atan2(delta[1],delta[0]))
            for error in (-1.,0.,1.):
                cut=clip(poly,*wedge(point,truth+error))
                if len(cut):estimates.append(self.tail(cut)+float(np.linalg.norm(point-cut.mean(axis=0)))/5)
            values.append(reception*(float(np.mean(estimates)) if estimates else prior)+(1-reception)*prior)
        value=float(np.mean(values));self.tail_cache[key]=value
        return value

    def option(self, channel, next_point):
        p=self.p;current=np.asarray(p.robot.position);center,radius=self.region(channel)
        def travel(x):
            distance=np.linalg.norm(x-current)
            if next_point is not None:distance+=np.linalg.norm(x-next_point)-np.linalg.norm(current-next_point)
            return float(max(0,distance))/5
        if radius<=19.8:return (travel(center)+5,channel,center,'certified_clear',0.)
        cover=self.cover(channel)
        if not cover:raise RuntimeError('Exhaustive optical covering failed')
        nearest=min(cover,key=lambda x:np.linalg.norm(x-current))
        tail=self.tail(p.tracks[channel]['polygon'])
        best=(travel(nearest)+3+self.cfg['tail_weight']*tail,channel,nearest,'optical',tail)
        if self.probes.get(channel,0)<self.cfg['max_probes']:
            for point in self.candidates(channel,next_point):
                future=self.probe_tail(channel,point)
                score=travel(point)+5+int(p.robot.channel!=channel)+self.cfg['tail_weight']*future
                if score<best[0]:best=(score,channel,point,'probe',future)
        return best

    def run(self, points):
        p=self.p;points=p._route(points)
        cert=DirectionalCertificate(points) if p.directional else None
        p.pending_nodes={c:set(range(len(points))) for c in range(1,21)}
        locked=None
        while len(p.cleared)<16:
            current=np.asarray(p.robot.position);surveys=[]
            for c,nodes in p.pending_nodes.items():
                if c in p.cleared:continue
                if c in p.tracks:
                    if cert and self.pruned_at.get(c)!=len(p.observations[c]):
                        old=len(nodes);nodes.intersection_update(cert.relevant_nodes(p.tracks[c]['polygon']))
                        p.pruned_nodes+=old-len(nodes)
                        self.pruned_at[c]=len(p.observations[c])
                    continue
                surveys.extend((float(np.linalg.norm(points[i]-current))/5+5+int(c!=p.robot.channel),c,i) for i in nodes)
            survey=min(surveys,default=None)
            reference=survey[2] if survey else None
            for c in p.tracks:
                if c in p.cleared or self.region(c)[1]<=19.8:continue
                for i in sorted(p.pending_nodes[c]):
                    if i!=reference and np.linalg.norm(points[i]-current)>1e-7:continue
                    if any(np.linalg.norm(points[i]-x)<25 for x in p.probe_positions[c]):continue
                    if not len(restrict_disk(p.tracks[c]['polygon'],points[i],1500)):continue
                    surveys.append((float(np.linalg.norm(points[i]-current))/5+5+int(c!=p.robot.channel),c,i))
            survey=min(surveys,default=None)
            next_point=points[survey[2]] if survey else None
            pending=[c for c in p.tracks if c not in p.cleared]
            if locked in p.cleared:locked=None
            if p.scheduler=='time_probe' and pending:
                locked=locked or min(pending,key=lambda c:np.linalg.norm(self.region(c)[0]-current))
                pending=[locked]
            options=[self.option(c,next_point) for c in pending]
            best=min(options,key=lambda x:(x[0],x[1])) if options else None
            if best is None and survey is None:break
            use_survey=survey is not None and (best is None or (p.scheduler=='joint' and best[0]>survey[0]+self.cfg['survey_bias_s']))
            if use_survey:
                _,channel,i=survey;point=points[i]
                p.phase='survey';p.decision=dict(reason='continue_discovery',survey_score_s=survey[0],
                    best_target_score_s=best[0] if best else None,next_node=i)
                if np.linalg.norm(current-point)>1e-7 or not p.action_trace:p.coverage_visits+=1
                if channel in p.tracks:p.supplemental_measures+=1
                p.measure(point,channel);p.pending_nodes[channel].discard(i)
            else:
                score,channel,point,action,tail=best
                p.phase='joint_'+action;p.decision=dict(reason=action,score_s=score,estimated_tail_s=tail,
                    survey_score_s=survey[0] if survey else None,next_point=next_point.tolist() if next_point is not None else None)
                if action=='probe':
                    self.probes[channel]=self.probes.get(channel,0)+1;p.supplemental_measures+=1
                    p.measure(point,channel)
                else:
                    if action=='optical':p.fallbacks+=1
                    success=p.clear(point,channel)
                    if action=='certified_clear' and not success:raise RuntimeError('Certified clear contradicted')
            p.replans+=1
        unresolved=[c for c,nodes in p.pending_nodes.items() if c not in p.cleared and (c in p.tracks or nodes)]
        if len(p.cleared)<16 and unresolved:raise RuntimeError(f'Incomplete channel certificates: {unresolved}')
        return 'known upper bound of 16 sources reached' if len(p.cleared)==16 else 'per-channel discovery certificates and localization complete'
