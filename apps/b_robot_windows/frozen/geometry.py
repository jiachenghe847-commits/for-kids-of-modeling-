"""Bounded-error bearing geometry. Units: metres, degrees; CCW from east."""
from __future__ import annotations
import itertools
import math
import numpy as np
from scipy.optimize import linprog

def cross(a, b):
    return float(a[0]*b[1]-a[1]*b[0])

def wedge(position, angle, error=1.005):
    """A x <= b for a forward bearing cone; rounding included for simulator data."""
    p=np.asarray(position,float)
    low,high=np.radians([angle-error,angle+error])
    a=np.array([[math.sin(low),-math.cos(low)],[-math.sin(high),math.cos(high)]])
    return a,a@p

def clip(poly, a, b, tol=1e-8):
    """Sutherland-Hodgman half-plane clipping; the input is a convex CCW polygon."""
    poly=np.asarray(poly,float).reshape(-1,2)
    for n,limit in zip(np.asarray(a),np.asarray(b)):
        if not len(poly):break
        output=[];previous=poly[-1];vp=float(n@previous-limit)
        for current in poly:
            vc=float(n@current-limit)
            if (vc<=tol)!=(vp<=tol):
                denom=vp-vc
                if abs(denom)>1e-15:output.append(previous+(current-previous)*(vp/denom))
            if vc<=tol:output.append(current)
            previous=current;vp=vc
        poly=np.array(output,float).reshape(-1,2)
    if len(poly)>1:
        keep=np.r_[True,np.linalg.norm(np.diff(poly,axis=0),axis=1)>1e-8]
        poly=poly[keep]
        if len(poly)>1 and np.linalg.norm(poly[0]-poly[-1])<1e-8:poly=poly[:-1]
    return poly

def circle_outer(center=(0,0),radius=1800,sides=96):
    """Circumscribed polygon: never removes a feasible point in the true disk."""
    angles=(np.arange(sides)+0.5)*2*np.pi/sides
    return np.asarray(center)+radius/math.cos(math.pi/sides)*np.c_[np.cos(angles),np.sin(angles)]

def restrict_disk(poly,center,radius,sides=64):
    angles=np.arange(sides)*2*np.pi/sides;a=np.c_[np.cos(angles),np.sin(angles)]
    return clip(poly,a,radius+a@np.asarray(center))

def bearing_region(observations,error=1.0):
    """Q1: diagnose empty/unbounded intersections before enumerating vertices.

    Each observation is (x,y,bearing). No fictitious bounding box is imposed.
    """
    if not observations:return {'status':'unbounded','vertices':[],'diameter':math.inf}
    constraints=[wedge((x,y),angle,error) for x,y,angle in observations]
    a=np.vstack([v[0] for v in constraints]);b=np.concatenate([v[1] for v in constraints])
    feasible=linprog(np.zeros(2),A_ub=a,b_ub=b,bounds=[(None,None)]*2,method='highs')
    if feasible.status==2:return {'status':'empty','vertices':[],'diameter':None}
    if not feasible.success:raise RuntimeError(feasible.message)
    for direction in [[1,0],[-1,0],[0,1],[0,-1]]:
        result=linprog(direction,A_ub=a,b_ub=b,bounds=[(None,None)]*2,method='highs')
        if result.status==3:return {'status':'unbounded','vertices':[],'diameter':math.inf}
        if not result.success:raise RuntimeError(result.message)
    vertices=[]
    for i,j in itertools.combinations(range(len(a)),2):
        if abs(np.linalg.det(a[[i,j]]))<1e-12:continue
        point=np.linalg.solve(a[[i,j]],b[[i,j]])
        if np.all(a@point<=b+1e-6) and all(np.linalg.norm(point-v)>1e-5 for v in vertices):vertices.append(point)
    if not vertices:vertices=[feasible.x]
    v=np.array(vertices);mid=v.mean(axis=0);v=v[np.argsort(np.arctan2(v[:,1]-mid[1],v[:,0]-mid[0]))]
    d,pair=diameter(v)
    return {'status':'bounded','vertices':v.tolist(),'diameter':d,'diameter_pair':pair}

def diameter(poly):
    p=np.asarray(poly,float)
    if not len(p):return None,None
    distances=np.sum((p[:,None,:]-p[None,:,:])**2,axis=2)
    i,j=np.unravel_index(np.argmax(distances),distances.shape)
    return float(np.sqrt(distances[i,j])),[p[i].tolist(),p[j].tolist()]

def enclosing_circle(poly):
    """Exact finite candidates: optimum supported by at most three vertices."""
    p=np.asarray(poly,float).reshape(-1,2)
    if not len(p):raise ValueError('Empty feasible region')
    best_center=p.mean(axis=0);best_radius=float(np.max(np.linalg.norm(p-best_center,axis=1)))
    candidates=[(x,0.) for x in p]
    for x,y in itertools.combinations(p,2):candidates.append(((x+y)/2,float(np.linalg.norm(x-y)/2)))
    for x,y,z in itertools.combinations(p,3):
        matrix=2*np.array([y-x,z-x]);rhs=np.array([np.dot(y-x,y-x),np.dot(z-x,z-x)])
        if abs(np.linalg.det(matrix))<1e-10:continue
        center=x+np.linalg.solve(matrix,rhs);radius=float(np.linalg.norm(center-x))
        if radius<best_radius+1e-8:candidates.append((center,radius))
    for center,radius in candidates:
        if radius<best_radius and np.all(np.linalg.norm(p-center,axis=1)<=radius+1e-7):best_center,best_radius=center,radius
    # Outward correction prevents tolerance from claiming an unsafe clear.
    return best_center,float(np.max(np.linalg.norm(p-best_center,axis=1)))

def optical_cover(poly,angle,spacing=25.):
    """Centers of every intersecting square cover P within spacing/sqrt(2)<20."""
    if not 0<spacing<=20*math.sqrt(2)-1e-6:raise ValueError('Spacing cannot guarantee a 20m cover')
    theta=math.radians(angle);rotation=np.array([[math.cos(theta),-math.sin(theta)],[math.sin(theta),math.cos(theta)]])
    local=np.asarray(poly)@rotation;lo=np.floor(local.min(axis=0)/spacing).astype(int);hi=np.floor(local.max(axis=0)/spacing).astype(int)
    points=[]
    for i in range(lo[0],hi[0]+1):
        for j in range(lo[1],hi[1]+1):
            lower=np.array([i,j])*spacing;upper=lower+spacing
            part=clip(local,[[1,0],[-1,0],[0,1],[0,-1]],[upper[0],-lower[0],upper[1],-lower[1]])
            if len(part):points.append(((lower+upper)/2)@rotation.T)
    return np.asarray(points)

def second_point(poly,first,bearing):
    """Reception-safe candidates for omni sources; sampled minimax geometry score.

    Every retained candidate is <=995m from ALL vertices, hence <=1000m from P.
    Scores are heuristic comparisons, not a global optimum certificate.
    """
    poly=np.asarray(poly);center,radius=enclosing_circle(poly)
    theta=math.radians(bearing);u=np.array([math.cos(theta),math.sin(theta)]);v=np.array([-u[1],u[0]])
    candidates=[]
    for along in [-200,0,200]:
        for side in [-600,-400,-200,200,400,600]:
            x=center+along*u+side*v
            if np.max(np.linalg.norm(poly-x,axis=1))<=995:candidates.append(x)
    if not candidates:candidates=[center]
    samples=np.vstack([poly,(poly+np.roll(poly,1,axis=0))/2,center[None,:]])
    scores=[]
    for x in candidates:
        worst=0.
        for source in samples:
            delta=source-x
            if np.linalg.norm(delta)<5:continue
            true=math.degrees(math.atan2(delta[1],delta[0]))
            for error in [-1.005,0,1.005]:
                a,b=wedge(x,true+error);cut=clip(poly,a,b)
                if len(cut):worst=max(worst,diameter(cut)[0])
        scores.append(worst+0.04*np.linalg.norm(x-np.asarray(first)))
    return np.asarray(candidates[int(np.argmin(scores))]),{'candidate_count':len(candidates),'score':min(scores),'scope':'sampled geometry; safe reception certified only when candidate max distance <=1000'}
