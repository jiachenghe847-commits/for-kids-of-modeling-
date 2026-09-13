"""Scalar reference kernel. Hypothetical worlds rank actions, never certify discovery."""
import math
import time


def distance(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])


def rank_distance(value):
    return math.floor(value*1e7+.5)


def clip_polygon(poly, normals, limits):
    for normal, limit in zip(normals, limits):
        if not poly:
            break
        output = []
        previous = poly[-1]
        vp = normal[0]*previous[0]+normal[1]*previous[1]-limit
        for current in poly:
            vc = normal[0]*current[0]+normal[1]*current[1]-limit
            if (vc <= 1e-8) != (vp <= 1e-8) and abs(vp-vc) > 1e-15:
                t = vp/(vp-vc)
                output.append((previous[0]+t*(current[0]-previous[0]), previous[1]+t*(current[1]-previous[1])))
            if vc <= 1e-8:
                output.append(tuple(current))
            previous, vp = current, vc
        poly = []
        for point in output:
            if not poly or distance(point, poly[-1]) > 1e-8:
                poly.append(point)
        if len(poly) > 1 and distance(poly[0], poly[-1]) < 1e-8:
            poly.pop()
    return poly


DISK_NORMALS = [(math.cos(k*math.tau/64), math.sin(k*math.tau/64)) for k in range(64)]


def observe_polygon(poly, point, angle):
    low, high = math.radians(angle-1.005), math.radians(angle+1.005)
    normals = [(math.sin(low), -math.cos(low)), (-math.sin(high), math.cos(high))]
    poly = clip_polygon(poly, normals, [n[0]*point[0]+n[1]*point[1] for n in normals])
    if any(distance(x, point) > 1500 for x in poly):
        poly = clip_polygon(poly, DISK_NORMALS, [1500+n[0]*point[0]+n[1]*point[1] for n in DISK_NORMALS])
    if not poly:
        raise ValueError('Empty hypothetical intersection; historical constraints retained')
    return poly


def circle(poly):
    """Deterministic incremental minimum circle, with outward radius correction."""
    if not poly:
        raise ValueError('Empty feasible region')
    center, radius = poly[0], 0.
    for i, a in enumerate(poly):
        if distance(a, center) <= radius+1e-9:
            continue
        center, radius = a, 0.
        for j in range(i):
            b = poly[j]
            if distance(b, center) <= radius+1e-9:
                continue
            center = ((a[0]+b[0])/2, (a[1]+b[1])/2)
            radius = distance(a, b)/2
            for k in range(j):
                c = poly[k]
                if distance(c, center) <= radius+1e-9:
                    continue
                bx, by, cx, cy = b[0]-a[0], b[1]-a[1], c[0]-a[0], c[1]-a[1]
                det = 2*(bx*cy-by*cx)
                if abs(det) < 1e-12:
                    pairs = [(a,b), (a,c), (b,c)]
                    u,v = max(pairs, key=lambda pair: distance(*pair))
                    center = ((u[0]+v[0])/2, (u[1]+v[1])/2)
                else:
                    bb, cc = bx*bx+by*by, cx*cx+cy*cy
                    center = (a[0]+(cy*bb-by*cc)/det, a[1]+(bx*cc-cx*bb)/det)
                radius = distance(a, center)
    return tuple(center), max(distance(x, center) for x in poly)


def centroid(poly):
    area = sx = sy = 0.
    for a,b in zip(poly, poly[1:]+poly[:1]):
        cross = a[0]*b[1]-a[1]*b[0]
        area += cross
        sx += (a[0]+b[0])*cross
        sy += (a[1]+b[1])*cross
    if abs(area) < 1e-9:
        return tuple(sum(x[k] for x in poly)/len(poly) for k in (0,1))
    return sx/(3*area), sy/(3*area)


def safe_center(poly, center, start, next_point, enabled):
    if not enabled:
        return center
    target = start if next_point is None else ((start[0]+next_point[0])/2, (start[1]+next_point[1])/2)
    lo, hi = 0., 1.
    for _ in range(32):
        t = (lo+hi)/2
        p = (center[0]+t*(target[0]-center[0]), center[1]+t*(target[1]-center[1]))
        if max(distance(p,x) for x in poly) <= 19.8:
            lo = t
        else:
            hi = t
    return center[0]+lo*(target[0]-center[0]), center[1]+lo*(target[1]-center[1])


def optical(poly, bearing, spacing, small_cover=False):
    center, radius = circle(poly)
    if radius <= 19.8:
        return [center]
    if small_cover and radius <= 39.6:
        # Partition the enclosing disk into six convex 60-degree wedges.
        # Each clipped polygon is certified by its actual farthest vertex.
        points = []
        for k in range(6):
            low, high = k*math.pi/3, (k+1)*math.pi/3
            ns = [(math.sin(low),-math.cos(low)),(-math.sin(high),math.cos(high))]
            part = clip_polygon(poly,ns,[n[0]*center[0]+n[1]*center[1] for n in ns])
            if part:
                c,r = circle(part)
                if r > 19.8:
                    break
                points.append(c)
        else:
            return points
    theta = math.radians(bearing)
    co, si = math.cos(theta), math.sin(theta)
    local = [(co*x+si*y, -si*x+co*y) for x,y in poly]
    bounds = [(math.floor(min(p[k] for p in local)/spacing), math.floor(max(p[k] for p in local)/spacing)) for k in (0,1)]
    points = []
    for i in range(bounds[0][0],bounds[0][1]+1):
        for j in range(bounds[1][0],bounds[1][1]+1):
            part = clip_polygon(local,[(1,0),(-1,0),(0,1),(0,-1)],[(i+1)*spacing,-i*spacing,(j+1)*spacing,-j*spacing])
            if part:
                x,y = (i+.5)*spacing,(j+.5)*spacing
                points.append((co*x-si*y,si*x+co*y))
    return points


def fixed_action(poly, start, bearing, received, used, failed, rounds, next_point, cfg):
    center, radius = circle(poly)
    if radius <= 19.8:
        return 'certified_clear', safe_center(poly,center,start,next_point,cfg['safe_shift'])
    if radius <= cfg['optical_trigger'] or rounds >= 12:
        points = [p for p in optical(poly,bearing,cfg['spacing'],cfg['small_cover'])
                  if all(distance(p,f) > 1e-7 for f in failed)]
        if not points:
            raise ValueError('Exhaustive optical covering failed')
        return 'optical', min(points,key=lambda p: rank_distance(distance(p,start)))
    angle = math.radians(bearing)
    direction, side = (math.cos(angle),math.sin(angle)),(-math.sin(angle),math.cos(angle))
    advance = max(0., (center[0]-received[0])*direction[0]+(center[1]-received[1])*direction[1])
    base = (received[0]+advance*direction[0],received[1]+advance*direction[1])
    choices = [(base[0]+s*20*side[0],base[1]+s*20*side[1]) for s in (-1,1)]
    fresh = [p for p in choices if all(distance(p,u)>1 for u in used)]
    if not fresh:
        step = 20*(1+rounds)
        fresh = [(base[0]+step*side[0],base[1]+step*side[1]),(base[0]-step*side[0],base[1]-step*side[1])]
    # A deterministic local comparison; there is no recursive candidate search.
    return 'probe', min(fresh,key=lambda p: rank_distance(distance(start,p)+distance(p,center)))


def key(point):
    return f'{point[0]:.8f}|{point[1]:.8f}'


def evaluate(poly, start, tuned_channel, channel, bearing, received, history,
             failed, rounds, worlds, action, point, next_point, cfg, deadline):
    """Mean complete service cost plus onward travel, or None on interruption.

    World: (x, y, reception radius, normal x, normal y, fixed future error).
    A zero normal represents an omnidirectional source.
    """
    totals = []
    components = [0.]*5  # movement, detection, switching, failed, successful
    for world in worlds:
        if time.monotonic() >= deadline:
            return None
        source = world[:2]
        region = list(poly)
        current, last_received, last_bearing = start, received, bearing
        memory = {key(h[:2]):(h[2],h[3]) for h in history}
        used = [h[:2] for h in history]
        misses, probes = list(failed), rounds
        kind, destination = action, point
        cost = [0.]*5
        tuned = tuned_channel
        optical_points = None
        while True:
            if time.monotonic() >= deadline:
                return None
            cost[0] += distance(current,destination)/5
            current = destination
            if kind != 'probe':
                if distance(current,source) <= 20+1e-9:
                    cost[4] += 5
                    break
                if kind == 'certified_clear':
                    raise ValueError('Hypothesis outside certified clear')
                cost[3] += 3
                misses.append(current)
                if circle(region)[1] <= cfg['optical_trigger'] or probes >= 12:
                    if optical_points is None:
                        optical_points = [p for p in optical(region,last_bearing,cfg['spacing'],cfg['small_cover'])
                                          if all(distance(p,f)>1e-7 for f in misses)]
                    else:
                        optical_points = [p for p in optical_points if distance(p,current)>1e-7]
                    if not optical_points:
                        raise ValueError('Exhaustive optical covering failed')
                    kind,destination = 'optical',min(optical_points,key=lambda p:rank_distance(distance(p,current)))
                    continue
            else:
                cost[1] += 5
                cost[2] += int(tuned != channel)
                tuned = channel
                probes += 1
                used.append(current)
                position_key = key(current)
                if position_key in memory:
                    response, angle = memory[position_key]
                else:
                    visible = ((current[0]-source[0])*world[3]+(current[1]-source[1])*world[4] >= -1e-9
                               and distance(current,source) <= world[2]+1e-9)
                    response = 'near' if visible and distance(current,source) <= 5 else ('direction' if visible else 'no_signal')
                    angle = (math.degrees(math.atan2(source[1]-current[1],source[0]-current[0]))+world[5])%360
                    memory[position_key] = response,angle
                if response == 'near':
                    cost[4] += 5
                    break
                if response == 'direction':
                    region = observe_polygon(region,current,angle)
                    last_received, last_bearing = current,angle
                    optical_points = None
            kind,destination = fixed_action(region,current,last_bearing,last_received,used,misses,probes,next_point,cfg)
        if next_point is not None:
            cost[0] += distance(current,next_point)/5
        totals.append(sum(cost))
        components = [a+b for a,b in zip(components,cost)]
    if not totals:
        raise ValueError('No compatible sampled worlds')
    return dict(mean_s=sum(totals)/len(totals), max_s=max(totals), worlds=len(totals),
                components_s=[v/len(totals) for v in components])
