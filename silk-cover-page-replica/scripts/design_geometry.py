# -*- coding: utf-8 -*-
"""Deterministic polygon engine for the silk cover design pass.

Why this module exists
----------------------
Univer's Slide Facade has no "Merge Shapes" (Boolean) operation, and no exact
curve-boolean is available in the workspace. The design pass therefore computes
the Boolean results analytically here -- same operands, same operation order as
the brief -- and hands finished outlines to the Facade for materialisation.

Everything is expressed in slide points (pt). Rasterisation uses the non-zero
winding rule, which is what DrawingML renderers use for custom geometry.
"""
import math

import numpy as np

EMU_PER_PT = 12700.0


# --------------------------------------------------------------------------- #
# path flattening
# --------------------------------------------------------------------------- #
def bezier_points(p0, p1, p2, p3, n):
    t = np.linspace(0.0, 1.0, n + 1)[:, None]
    mt = 1.0 - t
    p0, p1, p2, p3 = (np.asarray(p, dtype=float) for p in (p0, p1, p2, p3))
    return mt**3 * p0 + 3 * mt**2 * t * p1 + 3 * mt * t**2 * p2 + t**3 * p3


def flatten_path(commands, origin, scale=128):
    """Flatten OOXML path commands to a closed polygon in pt.

    Parameters
    ----------
    commands : list of [op, flat_numbers]  -- frame-local EMU coordinates
    origin   : (x, y) frame origin in pt
    scale    : samples per cubic segment
    """
    ox, oy = origin

    def to_pt(vals):
        return [(ox + vals[i] / EMU_PER_PT, oy + vals[i + 1] / EMU_PER_PT) for i in range(0, len(vals), 2)]

    pts = []
    cur = None
    for op, vals in commands:
        pts_ = to_pt(vals)
        if op == "moveTo":
            if pts and pts[-1] != pts[0]:
                pts.append(pts[0])
            cur = pts_[0]
            pts.append(cur)
        elif op == "lnTo":
            cur = pts_[0]
            pts.append(cur)
        elif op == "cubicBezTo":
            seg = bezier_points(cur, pts_[0], pts_[1], pts_[2], scale)
            pts.extend([(x, y) for x, y in seg[1:]])
            cur = pts_[2]
        elif op in ("close", "Z"):
            if pts and pts[-1] != pts[0]:
                pts.append(pts[0])
    if pts and pts[-1] != pts[0]:
        pts.append(pts[0])
    return pts


# --------------------------------------------------------------------------- #
# rasterisation (non-zero winding)
# --------------------------------------------------------------------------- #
class Grid:
    """Pixel grid over a pt-space rectangle; centre of pixel (r, c) is at (x(c), y(r))."""

    def __init__(self, x0, y0, x1, y1, s):
        self.s = float(s)
        self.x0, self.y0 = float(x0), float(y0)
        self.W = max(1, int(math.ceil((x1 - x0) * s)))
        self.H = max(1, int(math.ceil((y1 - y0) * s)))

    @property
    def xs(self):
        return self.x0 + (np.arange(self.W) + 0.5) / self.s

    @property
    def ys(self):
        return self.y0 + (np.arange(self.H) + 0.5) / self.s

    def to_pt(self, c, r):
        return (self.x0 + (c + 0.5) / self.s, self.y0 + (r + 0.5) / self.s)


def winding_mask(polygons, grid):
    """Non-zero winding fill of one or more closed polygons (pt) on `grid`."""
    edges = []
    for poly in polygons:
        p = np.asarray(poly, dtype=float)
        if len(p) < 3:
            continue
        a, b = p, np.roll(p, -1, axis=0)
        edges.append(np.stack([a[:, 0], a[:, 1], b[:, 0], b[:, 1]], axis=1))
    mask = np.zeros((grid.H, grid.W), dtype=bool)
    if not edges:
        return mask
    E = np.concatenate(edges, axis=0)
    x1, y1, x2, y2 = E[:, 0], E[:, 1], E[:, 2], E[:, 3]
    ymin, ymax = np.minimum(y1, y2), np.maximum(y1, y2)
    dirs = np.where(y2 > y1, 1, -1)
    rows = np.arange(grid.H)
    yc = grid.ys
    for r in rows:
        y = yc[r]
        hit = (ymin <= y) & (y < ymax)
        if not hit.any():
            continue
        xs = x1[hit] + (y - y1[hit]) * (x2[hit] - x1[hit]) / (y2[hit] - y1[hit])
        ds = dirs[hit]
        order = np.argsort(xs, kind="stable")
        xs = xs[order]
        wind = np.cumsum(ds[order])
        # pixel centres between consecutive crossings are inside when wind != 0
        c0 = np.ceil((xs - grid.x0) * grid.s - 0.5).astype(int)
        c0 = np.clip(c0, 0, grid.W)
        c1 = np.r_[c0[1:], grid.W]
        inside = wind != 0
        for k in np.nonzero(inside)[0]:
            if c1[k] > c0[k]:
                mask[r, c0[k]:c1[k]] = True
    return mask


def rect_mask(x, y, w, h, grid):
    return winding_mask([[(x, y), (x + w, y), (x + w, y + h), (x, y + h)]], grid)


def ellipse_mask(cx, cy, rx, ry, grid, n=2048):
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return winding_mask([[(cx + rx * math.cos(a), cy + ry * math.sin(a)) for a in t]], grid)


def mask_bounds(mask, grid):
    """pt-space bbox of the filled pixels."""
    rows = np.nonzero(mask.any(axis=1))[0]
    cols = np.nonzero(mask.any(axis=0))[0]
    if len(rows) == 0 or len(cols) == 0:
        return None
    x0, y0 = grid.to_pt(cols[0], rows[0])
    x1, y1 = grid.to_pt(cols[-1], rows[-1])
    return (x0, y0, x1, y1)


# --------------------------------------------------------------------------- #
# contour extraction
# --------------------------------------------------------------------------- #
def _edges_of_mask(mask):
    """Directed boundary segments in pixel-vertex coords, filled side on the right.

    A filled pixel (r, c) covers [c, c+1] x [r, r+1]. A side is a boundary when the
    neighbouring pixel across it is empty; sides are emitted head-to-tail so that
    walking the list traces the ring with the interior consistently on one side.
    """
    P = np.pad(np.asarray(mask, dtype=bool), 1, constant_values=False)
    H, W = mask.shape
    inner = P[1:-1, 1:-1]
    rows, cols = np.nonzero(inner)
    segs = []
    up = ~P[0:-2, 1:-1][rows, cols]
    right = ~P[1:-1, 2:][rows, cols]
    down = ~P[2:, 1:-1][rows, cols]
    left = ~P[1:-1, 0:-2][rows, cols]

    rr, cc = rows[up], cols[up]
    segs.append(np.stack([cc, rr, cc + 1, rr], axis=1))            # top: (c,r) -> (c+1,r)
    rr, cc = rows[right], cols[right]
    segs.append(np.stack([cc + 1, rr, cc + 1, rr + 1], axis=1))    # right: (c+1,r) -> (c+1,r+1)
    rr, cc = rows[down], cols[down]
    segs.append(np.stack([cc + 1, rr + 1, cc, rr + 1], axis=1))    # bottom: (c+1,r+1) -> (c,r+1)
    rr, cc = rows[left], cols[left]
    segs.append(np.stack([cc, rr + 1, cc, rr], axis=1))            # left: (c,r+1) -> (c,r)
    return np.concatenate([s for s in segs if len(s)], axis=0) if segs else np.zeros((0, 4), dtype=int)


def trace_contours(mask):
    """Chain boundary segments into closed pixel-space loops."""
    E = _edges_of_mask(mask)
    if len(E) == 0:
        return []
    start = {}
    for k in range(len(E)):
        start.setdefault((int(E[k, 0]), int(E[k, 1])), []).append(k)
    used = np.zeros(len(E), dtype=bool)
    loops = []
    for k0 in range(len(E)):
        if used[k0]:
            continue
        loop = []
        k = k0
        guard = 0
        while not used[k] and guard < len(E) + 2:
            used[k] = True
            loop.append((int(E[k, 0]), int(E[k, 1])))
            end = (int(E[k, 2]), int(E[k, 3]))
            cand = [j for j in start.get(end, []) if not used[j]]
            if not cand:
                loop.append(end)
                break
            # deterministic: prefer the tightest left turn so pinch vertices stay separated
            if len(cand) == 1:
                k = cand[0]
            else:
                def turn(j):
                    nx, ny = int(E[j, 2]) - int(E[j, 0]), int(E[j, 3]) - int(E[j, 1])
                    px, py = int(E[k, 2]) - int(E[k, 0]), int(E[k, 3]) - int(E[k, 1])
                    cross = px * ny - py * nx
                    dot = px * nx + py * ny
                    return (math.atan2(cross, dot))
                k = max(cand, key=turn)
            guard += 1
        if len(loop) >= 4:
            loops.append(loop)
    return loops


def signed_area(poly):
    p = np.asarray(poly, dtype=float)
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def point_in_polygon(pt, poly):
    x, y = pt
    p = np.asarray(poly, dtype=float)
    xs, ys = p[:, 0], p[:, 1]
    xn, yn = np.roll(xs, -1), np.roll(ys, -1)
    cond = ((ys > y) != (yn > y))
    with np.errstate(divide="ignore", invalid="ignore"):
        xint = xs + (y - ys) * (xn - xs) / (yn - ys)
    return bool(np.count_nonzero(cond & (x < xint)) % 2)


def simplify(poly, eps):
    """Douglas-Peucker on a closed polygon (keeps it closed)."""
    p = [tuple(map(float, q)) for q in poly]
    if len(p) < 4:
        return p

    def dp(points):
        if len(points) < 3:
            return points
        a, b = np.array(points[0]), np.array(points[-1])
        ab = b - a
        n = float(np.hypot(*ab))
        if n == 0:
            d = np.hypot(*(np.array(points) - a).T)
        else:
            rel = np.array(points) - a
            # scalar 2-D cross product (np.cross on 2-vectors is deprecated in NumPy 2)
            d = np.abs(ab[0] * rel[:, 1] - ab[1] * rel[:, 0]) / n
        i = int(np.argmax(d))
        if d[i] > eps:
            return dp(points[: i + 1])[:-1] + dp(points[i:])
        return [points[0], points[-1]]

    # split the ring at the two extreme vertices to avoid a degenerate baseline
    k = int(np.argmax(np.hypot(*(np.array(p) - np.array(p[0])).T)))
    head = dp(p[: k + 1])
    tail = dp(p[k:] + [p[0]])
    out = head[:-1] + tail[:-1]
    return out if len(out) >= 3 else p


def mask_to_polygons(mask, grid, eps=0.12):
    """Closed pt-space loops with outer rings CCW and holes CW (non-zero fill)."""
    loops = []
    for loop in trace_contours(mask):
        pts = [grid.to_pt(c, r) for c, r in loop]
        if len(pts) > 3 and pts[0] == pts[-1]:
            pts = pts[:-1]
        pts = simplify(pts, eps)
        if len(pts) >= 3:
            loops.append(pts)
    if not loops:
        return []
    loops.sort(key=lambda p: -abs(signed_area(p)))
    out = []
    for i, poly in enumerate(loops):
        depth = 0
        probe = poly[0]
        for j, other in enumerate(loops):
            if i != j and abs(signed_area(other)) > abs(signed_area(poly)) and point_in_polygon(probe, other):
                depth += 1
        ccw = signed_area(poly) > 0
        want_ccw = depth % 2 == 0
        out.append(poly if ccw == want_ccw else poly[::-1])
    return out


def polygons_to_dataarray(polygons, origin, path_w_emu, path_h_emu):
    """Encode loops as frame-local integer EMU commands for <a:path>/dataArray."""
    ox, oy = origin
    cmds = []
    for poly in polygons:
        for i, (x, y) in enumerate(poly):
            px = int(round((x - ox) * EMU_PER_PT))
            py = int(round((y - oy) * EMU_PER_PT))
            if i == 0:
                cmds.append({"command": "M", "points": [px, py]})
            else:
                cmds.append({"command": "L", "points": [px, py]})
        cmds.append({"command": "z", "points": []})
    return cmds


def rasterise_polygons(polygons, x0, y0, x1, y1, s):
    g = Grid(x0, y0, x1, y1, s)
    return winding_mask(polygons, g), g
