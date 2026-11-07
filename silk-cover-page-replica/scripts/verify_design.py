# -*- coding: utf-8 -*-
"""Verify the phase-B design page in an exported .pptx against build/design.json.

    python verify_design.py <design.pptx> <design.json> [--slide N]

`design.json` is what scripts/build_design.py emits; it already carries every expected
number (frames, EMU paths, tile scales, outline stops), so no reference deck or screenshot
is needed.

Checks, per element in z-order:
  * six elements, each custom geometry with a frame matching the spec (0.01 pt)
  * silhouette matches the computed outline (raster IoU >= 0.995)
  * tiled picture fill: alignment ctr, scale == k, and k == max(w/img_w, h/img_h) re-derived
  * outline: 5 pt, gradient, three stops with the spec's positions, colours and alphas

Exit code 0 only when every check passes.
"""
import json
import os
import shutil
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design_geometry as G  # noqa: E402

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
EMU = 12700.0
K_TO_SX = 400000.0 / 3.0     # Facade tile scale k -> OOXML sx (thousandths of a percent)
TOL_PT = 0.01
IOU_MIN = 0.995


def shape_records(slide):
    out = []
    for el in slide.find(f"{P}cSld/{P}spTree"):
        if el.tag.split("}")[1] != "sp":
            continue
        spPr = el.find(f"{P}spPr")
        nv = el.find(f"{P}nvSpPr/{P}cNvPr")
        rec = {"id": nv.get("id"), "name": nv.get("name")}
        xf = spPr.find(f"{A}xfrm")
        off, ext = xf.find(f"{A}off"), xf.find(f"{A}ext")
        rec["frame"] = [int(off.get("x")), int(off.get("y")), int(ext.get("cx")), int(ext.get("cy"))]
        cg = spPr.find(f"{A}custGeom")
        rec["geom"] = None
        if cg is not None:
            path = cg.find(f"{A}pathLst/{A}path")
            rec["geom"] = dict(space=[int(path.get("w")), int(path.get("h"))], paths=[])
            cur, poly = None, None
            for c in path:
                op = c.tag.split("}")[1]
                ps = [(int(p.get("x")), int(p.get("y"))) for p in c.findall(f"{A}pt")]
                if op in ("moveTo", "lnTo"):
                    cur = ps[0]
                    if op == "moveTo" or poly is None:
                        poly = []
                        rec["geom"]["paths"].append(poly)
                    poly.append(cur)
                elif op == "cubicBezTo":
                    p0 = cur
                    for i in range(1, 25):
                        t = i / 24
                        mt = 1 - t
                        x = mt**3 * p0[0] + 3 * mt**2 * t * ps[0][0] + 3 * mt * t**2 * ps[1][0] + t**3 * ps[2][0]
                        y = mt**3 * p0[1] + 3 * mt**2 * t * ps[0][1] + 3 * mt * t**2 * ps[1][1] + t**3 * ps[2][1]
                        poly.append((x, y))
                    cur = ps[2]
        blip = spPr.find(f"{A}blipFill")
        rec["blip"] = None
        if blip is not None:
            b = blip.find(f"{A}blip")
            tile = blip.find(f"{A}tile")
            rec["blip"] = dict(rid=b.get(f"{R}embed") if b is not None else None,
                               tile=dict(tile.attrib) if tile is not None else None)
        ln = spPr.find(f"{A}ln")
        rec["ln"] = None
        if ln is not None:
            grad = ln.find(f"{A}gradFill")
            rec["ln"] = dict(width=int(ln.get("w")) if ln.get("w") else None,
                             kind="gradient" if grad is not None else "other", stops=None)
            if grad is not None:
                stops = []
                for g in grad.find(f"{A}gsLst").findall(f"{A}gs"):
                    clr = g.find(f"{A}srgbClr")
                    alpha = clr.find(f"{A}alpha") if clr is not None else None
                    stops.append(dict(pos=int(g.get("pos")),
                                      color=("#" + clr.get("val").upper()) if clr is not None else None,
                                      alpha=int(alpha.get("val")) if alpha is not None else 100000))
                rec["ln"]["stops"] = stops
        out.append(rec)
    return out


def absolute_loops(rec):
    ox, oy, cx, cy = rec["frame"]
    pw, ph = rec["geom"]["space"]
    sx, sy = cx / pw, cy / ph
    return [[((ox + x * sx) / EMU, (oy + y * sy) / EMU) for x, y in path]
            for path in rec["geom"]["paths"] if len(path) >= 3]


def spec_loops(el):
    ox, oy = el["frame_pt"][0], el["frame_pt"][1]
    loops, cur = [], None
    for c in el["path"]["commands"]:
        if c["command"] == "M":
            cur = [(ox + c["points"][0] / EMU, oy + c["points"][1] / EMU)]
            loops.append(cur)
        elif c["command"] == "L":
            cur.append((ox + c["points"][0] / EMU, oy + c["points"][1] / EMU))
    return loops


def iou(pa, pb, s=5.0, pad=2.0):
    pts = np.vstack([np.asarray(p) for p in pa + pb])
    g = G.Grid(pts[:, 0].min() - pad, pts[:, 1].min() - pad, pts[:, 0].max() + pad, pts[:, 1].max() + pad, s)
    ma = G.winding_mask(pa, g)
    mb = G.winding_mask(pb, g)
    u = np.count_nonzero(ma | mb)
    return np.count_nonzero(ma & mb) / u if u else 0.0


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    pptx, design_path = sys.argv[1], sys.argv[2]
    idx = int(sys.argv[sys.argv.index("--slide") + 1]) if "--slide" in sys.argv else 1
    design = json.load(open(design_path, encoding="utf-8"))
    els = design["elements"]
    stroke = design["stroke"]

    tmp = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(pptx) as z:
            z.extractall(tmp)
        slide = ET.parse(os.path.join(tmp, "ppt", "slides", f"slide{idx}.xml")).getroot()
        shapes = shape_records(slide)
        ok = True
        print(f"shapes: {len(shapes)} (expected {len(els)})")
        if len(shapes) != len(els):
            ok = False
        for i, (rec, el) in enumerate(zip(shapes, els), 1):
            fails = []
            frame = rec["frame"]
            w_pt, h_pt = frame[2] / EMU, frame[3] / EMU
            exp = el["frame_pt"]
            if max(abs(frame[k] / EMU - exp[k]) for k in range(4)) > TOL_PT:
                fails.append("frame differs from spec by > 0.01pt")
            if rec["geom"] is None:
                fails.append("no custom geometry")
            else:
                if rec["geom"]["space"] != list(el["path"]["space_emu"]):
                    fails.append(f'path space {rec["geom"]["space"]} != {el["path"]["space_emu"]}')
            # fill
            blip = rec["blip"]
            if not blip or not blip.get("tile"):
                fails.append("fill is not a tiled picture")
            else:
                tile = blip["tile"]
                if tile.get("algn") != "ctr":
                    fails.append(f'tile alignment {tile.get("algn")} != ctr')
                iw, ih = el["image"]["px"]
                k = max(w_pt / iw, h_pt / ih)
                if abs(k - el["k"]) > 1e-4:
                    fails.append(f'k re-derived {k:.6f} != ledger {el["k"]:.6f}')
                sx = float(tile.get("sx", 0)) / K_TO_SX
                sy = float(tile.get("sy", 0)) / K_TO_SX
                if abs(sx - k) > 2e-3 or abs(sy - k) > 2e-3:
                    fails.append(f"tile scale ({sx:.6f},{sy:.6f}) != k {k:.6f}")
            # outline
            ln = rec["ln"]
            if not ln or ln["kind"] != "gradient":
                fails.append("outline is not a gradient line")
            else:
                if ln["width"] != int(stroke["width_emu"]):
                    fails.append(f'width {ln["width"]} != {stroke["width_emu"]}')
                stops = ln["stops"] or []
                if len(stops) != len(stroke["gradient_stops"]):
                    fails.append(f"{len(stops)} stops != {len(stroke['gradient_stops'])}")
                else:
                    for got, want in zip(stops, stroke["gradient_stops"]):
                        if abs(got["pos"] - round(want["position"] * 100000)) > 1:
                            fails.append(f'stop position {got["pos"]}')
                        if got["color"] != want["color"].upper():
                            fails.append(f'stop colour {got["color"]}')
                        if abs(got["alpha"] - round(want["opacity"] * 100000)) > 1:
                            fails.append(f'stop alpha {got["alpha"]}')
            # silhouette
            iou_v = None
            if rec["geom"] is not None:
                iou_v = iou(absolute_loops(rec), spec_loops(el))
                if iou_v < IOU_MIN:
                    fails.append(f"silhouette IoU {iou_v:.4f}")
            status = "OK" if not fails else "FAIL: " + "; ".join(fails)
            extra = f"  iou={iou_v:.4f}" if iou_v is not None else ""
            print(f'[{el["label"]:5s}] frame=({exp[0]:.3f},{exp[1]:.3f},{w_pt:.3f},{h_pt:.3f}) '
                  f'k={el["k"]:.6f} img={el["image"]["name"]}  {status}{extra}')
            if fails:
                ok = False
        print("\nVERDICT:", "DESIGN MATCHES SPEC" if ok else "DESIGN DIFFERS FROM SPEC")
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
