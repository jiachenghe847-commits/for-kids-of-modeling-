"""Conservative triangular-lattice discovery with an explicit coverage argument."""
import math
import numpy as np
from scipy.spatial import ConvexHull, Delaunay
from geometry import clip


class DirectionalCertificate:
    """Short-edge triangulation; pruning never relies on sampled orientations."""

    def __init__(self, points):
        self.points = np.asarray(points, float)
        self.triangles = Delaunay(self.points).simplices
        vertices = self.points[self.triangles]
        edges = vertices - np.roll(vertices, 1, axis=1)
        self.valid = bool(np.max(np.linalg.norm(edges, axis=2)) < 1000 - 1e-7)
        self.hull = ConvexHull(self.points).equations

    def relevant_nodes(self, polygon):
        polygon = np.asarray(polygon, float)
        all_nodes = set(range(len(self.points)))
        if not self.valid or not len(polygon):
            return all_nodes
        if np.max(polygon @ self.hull[:, :2].T + self.hull[:, 2]) > 1e-7:
            return all_nodes
        nodes = set()
        for indices in self.triangles:
            triangle = self.points[indices]
            edge = np.roll(triangle, -1, axis=0) - triangle
            normals = np.c_[edge[:, 1], -edge[:, 0]]
            if len(clip(polygon, normals, np.sum(normals * triangle, axis=1))):
                nodes.update(map(int, indices))
        return nodes or all_nodes


def omnidirectional_ring():
    """Seven 900m reception disks cover the entire radius-1800m target disk.

    The centre covers rho<=900. For rho in [900,1800], the nearest of six
    ring points at radius 900*sqrt(3) differs in angle by at most 30 degrees.
    Squared distance is convex in rho; at either endpoint it is <=900**2.
    This certificate uses no source positions or distribution assumptions.
    """
    r = 900 * math.sqrt(3)
    return [np.zeros(2)] + [r * np.array([math.cos(k * math.pi / 3), math.sin(k * math.pi / 3)]) for k in range(6)]


def compact_directional_grid(directional=True):
    """25-point directional certificate with boundary caps instead of far vertices.

    A side-1980 regular hexagon is tiled by side-990 equilateral triangles,
    using its 19 triangular-lattice vertices. Add one radial cap at distance
    1850 in each side-midpoint direction (30+60k degrees). Each cap creates
    two triangles with longest edge sqrt(990^2+(1850-990*sqrt(3))^2)<1000.
    The resulting convex dodecagon has edge distance from origin >1832m,
    hence contains the radius-1800 disk. All its covering triangles have
    every edge <1000, providing the same half-plane visibility certificate.
    """
    if not directional:
        return omnidirectional_ring()
    core = [p for p in triangular_grid(True) if np.linalg.norm(p) <= 1980 + 1e-8]
    if len(core) != 19:
        raise RuntimeError('Unexpected core lattice vertex count')
    caps = [1850*np.array([math.cos(math.pi/6+k*math.pi/3), math.sin(math.pi/6+k*math.pi/3)]) for k in range(6)]
    return core + caps


def triangle_intersects_disk(triangle, radius=1800.0):
    triangle = np.asarray(triangle, float)
    signs = []
    distances = []
    for a, b in zip(triangle, np.roll(triangle, -1, axis=0)):
        u = b - a
        signs.append(u[0] * (-a[1]) - u[1] * (-a[0]))
        nearest = a + np.clip(-np.dot(a, u) / np.dot(u, u), 0, 1) * u
        distances.append(np.linalg.norm(nearest))
    origin_inside = min(signs) >= -1e-8 or max(signs) <= 1e-8
    return origin_inside or min(distances) <= radius + 1e-8


def triangular_grid(directional=False):
    """Keep vertices of every equilateral triangle intersecting the source disk.

    Omni: side 1700, nearest triangle vertex <=1700/sqrt(3)<1000.
    Directional: side 990, all vertices <=990 from each point of the triangle.
    Their convex hull contains the source, so a closed emitting half-plane
    contains at least one vertex. Grid vertices outside the source disk are legal.
    Integer lattice keys avoid duplicate points caused by floating-point addition.
    """
    side = 990.0 if directional else 1700.0
    height = math.sqrt(3) * side / 2

    def position(key):
        i, j = key
        return np.array([side * (i + j / 2), height * j])

    keys = set()
    limit = math.ceil(1800 / height) + 2
    for j in range(-limit, limit):
        for i in range(-2 * limit, 2 * limit):
            triangles = [((i, j), (i + 1, j), (i, j + 1)),
                         ((i + 1, j + 1), (i, j + 1), (i + 1, j))]
            for vertices in triangles:
                if triangle_intersects_disk([position(k) for k in vertices]):
                    keys.update(vertices)
    keys.add((0, 0))
    return [position(k) for k in sorted(keys)]
