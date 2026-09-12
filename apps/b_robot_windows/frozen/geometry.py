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
    """Diameter of a convex polygon using rotating calipers.

    Degenerate inputs are handled explicitly.  The fallback for a malformed
    polygon keeps the diagnostic routine total rather than imposing a hidden
    bounding box.
    """
    p=np.asarray(poly,float).reshape(-1,2)
    if not len(p):return None,None
    if len(p)==1:return 0.,[p[0].tolist(),p[0].tolist()]
    if len(p)==2:
        return float(np.linalg.norm(p[1]-p[0])),[p[0].tolist(),p[1].tolist()]
    area2=float(np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1)))
    if area2<0:p=p[::-1]
    best2=-1.;best=None;j=1;n=len(p)
    def cross_edge(i,k):
        return abs(cross(p[(i+1)%n]-p[i],p[k]-p[i]))
    for i in range(n):
        ni=(i+1)%n
        while cross_edge(i,(j+1)%n)>cross_edge(i,j)+1e-10:
            j=(j+1)%n
        for k in (i,j,ni):
            d2=float(np.dot(p[i]-p[k],p[i]-p[k]))
            if d2>best2:
                best2=d2;best=(p[i],p[k])
    # A convexity/order error should not silently corrupt a safety result.
    exact=np.sum((p[:,None,:]-p[None,:,:])**2,axis=2)
    ei,ej=np.unravel_index(np.argmax(exact),exact.shape)
    if float(exact[ei,ej])>best2+1e-7:
        best2=float(exact[ei,ej]);best=(p[ei],p[ej])
    return float(np.sqrt(max(0.,best2))),[best[0].tolist(),best[1].tolist()]

def polygon_area(poly):
    """Area of an ordered polygon; zero for a point or line segment."""
    p=np.asarray(poly,float).reshape(-1,2)
    if len(p)<3:return 0.
    return abs(float(np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1)))/2)

def fisher_information(poly, first, second, bearing, sigma_deg=1.005):
    """Sampled bearing Fisher information for a candidate second detector."""
    p=np.asarray(poly,float).reshape(-1,2);first=np.asarray(first,float);second=np.asarray(second,float)
    samples=np.vstack([p,(p+np.roll(p,1,axis=0))/2,p.mean(axis=0)])
    info=np.zeros((2,2));used=0
    sigma=math.radians(float(sigma_deg))
    for source in samples:
        terms=[]
        for detector in (first,second):
            delta=source-detector;rho=float(np.linalg.norm(delta))
            if rho<5.:continue
            n=np.array([-delta[1],delta[0]])/rho
            terms.append(np.outer(n,n)/(rho*rho*sigma*sigma))
        if terms:info+=sum(terms);used+=1
    if used:info/=used
    sign,logdet=np.linalg.slogdet(info)
    return info,float(logdet if sign>0 else -math.inf)

def pareto_front(records, keys=('mean_area_m2','mean_diameter_m','distance_from_first_m')):
    """Return nondominated candidate records for minimization metrics."""
    front=[]
    for i,a in enumerate(records):
        dominated=False
        for j,b in enumerate(records):
            if i==j:continue
            av=[float(a[k]) for k in keys];bv=[float(b[k]) for k in keys]
            if all(x<=y+1e-10 for x,y in zip(bv,av)) and any(x<y-1e-10 for x,y in zip(bv,av)):
                dominated=True;break
        if not dominated:front.append(a)
    return front

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
    """Choose a reception-safe second detector by information and area.

    A coarse deterministic grid is screened by Fisher information, evaluated
    with exact polygon clipping, then reduced to a Pareto front.  This is a
    finite active-sensing design, not a continuous global optimum claim.
    """
    poly=np.asarray(poly,float).reshape(-1,2);first=np.asarray(first,float)
    center,_=enclosing_circle(poly);lo=poly.min(axis=0);hi=poly.max(axis=0)
    gx=np.arange(math.floor(lo[0]/200)*200,math.ceil(hi[0]/200)*200+1,200)
    gy=np.arange(math.floor(lo[1]/200)*200,math.ceil(hi[1]/200)*200+1,200)
    candidates=[center]
    candidates.extend(np.array([x,y],float) for x in gx for y in gy)
    candidates.extend([center+np.array([dx,dy]) for dx in (-100,0,100) for dy in (-100,0,100)])
    unique=[]
    for x in candidates:
        if np.max(np.linalg.norm(poly-x,axis=1))<=995 and not any(np.linalg.norm(x-y)<1e-7 for y in unique):unique.append(x)
    if not unique:unique=[center]
    records=[]
    samples=np.vstack([poly,(poly+np.roll(poly,1,axis=0))/2,center[None,:]])
    for x in unique:
        info,logdet=fisher_information(poly,first,x,bearing)
        areas=[];diameters=[]
        for source in samples:
            delta=source-x
            if np.linalg.norm(delta)<5:continue
            true=math.degrees(math.atan2(delta[1],delta[0]))
            for error in (-1.005,0.,1.005):
                a,b=wedge(x,true+error);cut=clip(poly,a,b)
                if len(cut):areas.append(polygon_area(cut));diameters.append(diameter(cut)[0])
        records.append({'position':x.tolist(),'distance_from_first_m':float(np.linalg.norm(x-first)),
            'max_distance_to_outer_polygon_m':float(np.max(np.linalg.norm(poly-x,axis=1))),
            'mean_area_m2':float(np.mean(areas) if areas else 0.),'max_area_m2':float(max(areas) if areas else 0.),
            'mean_diameter_m':float(np.mean(diameters) if diameters else 0.),'max_sampled_diameter_m':float(max(diameters) if diameters else 0.),
            'logdet_fisher':logdet,'fisher_trace':float(np.trace(info)),'source_error_pairs':len(areas)})
    # Information is an analytic pre-screen; retain the strongest half before
    # exact area Pareto filtering to keep online calls inexpensive.
    records=sorted(records,key=lambda r:r['logdet_fisher'],reverse=True)[:max(8,min(32,len(records)))]
    front=pareto_front(records)
    min_area=min(r['mean_area_m2'] for r in front)
    near=[r for r in front if r['mean_area_m2']<=min_area*1.01+1e-9]
    selected=min(near,key=lambda r:(r['distance_from_first_m'],-r['logdet_fisher']))
    return np.asarray(selected['position']),{'candidate_count':len(unique),'evaluated_count':len(records),
        'pareto_count':len(front),'selected_mean_area_m2':selected['mean_area_m2'],
        'selected_max_area_m2':selected['max_area_m2'],'selected_mean_diameter_m':selected['mean_diameter_m'],
        'selected_max_diameter_m':selected['max_sampled_diameter_m'],'selected_logdet_fisher':selected['logdet_fisher'],
        'selected_fisher_trace':selected['fisher_trace'],'pareto':front,
        'scope':'Fisher-information screening plus sampled polygon-area Pareto design; finite design, not global optimum'}
