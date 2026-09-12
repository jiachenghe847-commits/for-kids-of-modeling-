"""Coverage certificate + bounded-error localization + optical-cover fallback."""
from __future__ import annotations
import math
import time
import numpy as np
from geometry import circle_outer,clip,wedge,restrict_disk,enclosing_circle,second_point,optical_cover
from search_coverage import triangular_grid,omnidirectional_ring,compact_directional_grid

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
    def __init__(self,robot,directional=False,baseline=False,grid='triangle',early_clears=3):
        self.robot=robot;self.directional=directional;self.baseline=baseline
        self.cleared=set();self.tracks={};self.measures=0;self.clear_attempts=0;self.fallbacks=0
        self.probe_positions={};self.coverage_visits=0
        self.grid=grid;self.early_clears=early_clears;self.failed_clear_points={}
    def measure(self,point,channel):
        response=self.robot.measure(tuple(point),channel);self.measures+=1
        self.probe_positions.setdefault(channel,[]).append(np.asarray(point).copy())
        kind=response['measure_result']
        if kind=='near':
            if not self.clear(point,channel):raise RuntimeError('Near response contradicted by optical clear')
        elif kind=='direction':
            angle=float(response['svd_deg'])
            old=self.tracks.get(channel)
            polygon=old['polygon'] if old else circle_outer()
            a,b=wedge(point,angle);polygon=restrict_disk(clip(polygon,a,b),point,1500)
            if len(polygon)==0:raise RuntimeError(f'Inconsistent bearing constraints for channel {channel}')
            self.tracks[channel]={'polygon':polygon,'first':old['first'] if old else np.asarray(point),
                                  'bearing':old['bearing'] if old else angle}
        elif kind!='no_signal':raise RuntimeError(f'Unknown measure result {kind}')
        return response
    def clear(self,point,channel):
        response=self.robot.clear(tuple(point),channel);self.clear_attempts+=1
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
    def run(self):
        if self.grid=='compact':points=compact_directional_grid(self.directional)
        elif self.grid=='ring':
            if self.directional:raise ValueError('Omnidirectional ring is not a directional coverage certificate')
            points=omnidirectional_ring()
        else:points=triangular_grid(self.directional) if self.grid=='triangle' else discovery_grid(self.directional)
        while points and len(self.cleared)<16:
            current=np.asarray(self.robot.position);i=min(range(len(points)),key=lambda k:np.linalg.norm(points[k]-current))
            point=points.pop(i);self.coverage_visits+=1
            channels=[c for c in range(1,21) if c not in self.cleared]
            if self.robot.channel in channels:
                channels.remove(self.robot.channel);channels.insert(0,self.robot.channel)
            for channel in channels:self.measure(point,channel)
            pending=[c for c in self.tracks if c not in self.cleared]
            while pending:
                current=np.asarray(self.robot.position)
                channel=min(pending,key=lambda c:np.linalg.norm(self.tracks[c]['polygon'].mean(axis=0)-current))
                self.localize(channel);pending.remove(channel)
        return {'cleared_count':len(self.cleared),'cleared_channels':sorted(self.cleared),
                'virtual_time_s':self.robot.virtual_time,'average_time_s':self.robot.virtual_time/len(self.cleared) if self.cleared else None,
                'measurements':self.measures,'clear_attempts':self.clear_attempts,'fallbacks':self.fallbacks,
                'coverage_visits':self.coverage_visits,'grid':self.grid,'early_clears':self.early_clears,
                'completion_basis':'all coverage nodes visited' if not points else 'known upper bound of 16 sources reached'}
