# -*- coding: utf-8 -*-
"""Verify a produced .pptx against references/page-spec.json (no reference deck needed).

    python verify_slide.py <produced.pptx> [skill_dir] [slide_index]

Checks, per element in z-order: shape kind, frame (x/y/w/h), stroke width, fill, and -- for the
freeform -- the flattened bezier curve. Prints one line per element and a final VERDICT.

Tolerance default 0.01 pt (127 EMU). Exit code 0 only when every check passes.
"""
import json
import os
import sys
import tempfile
import shutil
import zipfile
import xml.etree.ElementTree as ET

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
EMU_PER_PT = 12700.0
TOL_EMU = 127.0  # 0.01 pt


def read_slide(pptx, idx):
    tmp = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(pptx) as z:
            for n in z.namelist():
                if n.startswith("ppt/") or n == "[Content_Types].xml":
                    z.extract(n, tmp)
        pres = ET.parse(os.path.join(tmp, "ppt", "presentation.xml")).getroot()
        sld = ET.parse(os.path.join(tmp, "ppt", "slides", f"slide{idx}.xml")).getroot()
        sz = pres.find(f"{P}sldSz")
        sw, sh = int(sz.get("cx")), int(sz.get("cy"))
        shapes = []
        for el in sld.find(f"{P}cSld/{P}spTree"):
            if el.tag.split("}")[1] not in ("sp", "cxnSp", "pic", "graphicFrame"):
                continue
            nv = el.find(f".//{P}cNvPr")
            spPr = el.find(f"{P}spPr")
            rec = {"id": nv.get("id") if nv is not None else None,
                   "name": nv.get("name") if nv is not None else None}
            if spPr is None:
                rec.update(kind="other")
                shapes.append(rec)
                continue
            prst = spPr.find(f"{A}prstGeom")
            cg = spPr.find(f"{A}custGeom")
            if cg is not None:
                rec["kind"] = "freeform"
            elif prst is not None:
                rec["kind"] = prst.get("prst")
            else:
                rec["kind"] = "other"
            xf = spPr.find(f"{A}xfrm")
            off = xf.find(f"{A}off") if xf is not None else None
            ext = xf.find(f"{A}ext") if xf is not None else None
            rec["frame"] = [int(off.get("x")), int(off.get("y")), int(ext.get("cx")), int(ext.get("cy"))] \
                if off is not None and ext is not None else None
            ln = spPr.find(f"{A}ln")
            rec["line_w"] = int(ln.get("w")) if (ln is not None and ln.get("w")) else 12700
            rec["fill"] = "none" if spPr.find(f"{A}noFill") is not None else (
                "solid" if spPr.find(f"{A}solidFill") is not None else "other")
            if cg is not None:
                path = cg.find(f"{A}pathLst/{A}path")
                rec["path_w"] = int(path.get("w"))
                rec["path_h"] = int(path.get("h"))
                rec["path"] = [(c.tag.split("}")[1],
                                [(int(p.get("x")), int(p.get("y"))) for p in c.findall(f"{A}pt")])
                               for c in path]
            shapes.append(rec)
        return sw, sh, shapes
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def flatten(rec, n=64):
    """Absolute EMU polyline of a shape's path, scaled so the path window maps onto the frame."""
    ox, oy, cx, cy = rec["frame"]
    pw, ph = rec.get("path_w") or cx, rec.get("path_h") or cy
    sx, sy = cx / pw, cy / ph
    out, cur = [], None
    for op, ps in rec.get("path", []):
        ps = [(p[0] * sx, p[1] * sy) for p in ps]
        if op in ("moveTo", "lnTo"):
            cur = ps[0]
            out.append((ox + cur[0], oy + cur[1]))
        elif op == "cubicBezTo":
            p0, p1, p2, p3 = cur, ps[0], ps[1], ps[2]
            for i in range(1, n + 1):
                t = i / n
                mt = 1 - t
                x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
                y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
                out.append((ox + x, oy + y))
            cur = p3
    return out


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    pptx = sys.argv[1]
    skill_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    idx = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    spec = json.load(open(os.path.join(skill_dir, "references", "page-spec.json"), encoding="utf-8"))

    sw, sh, shapes = read_slide(pptx, idx)
    want_w = spec["page"]["width_emu"]
    want_h = spec["page"]["height_emu"]
    ok = True
    print(f"page: {sw} x {sh} EMU (expected {want_w} x {want_h})   shapes: {len(shapes)} (expected {len(spec['elements'])})")
    if (sw, sh) != (want_w, want_h):
        print("  FAIL slide size")
        ok = False
    if len(shapes) != len(spec["elements"]):
        print("  FAIL element count")
        ok = False

    for want, got in zip(spec["elements"], shapes):
        fails = []
        if want["kind"] != got.get("kind"):
            fails.append(f'kind {got.get("kind")} != {want["kind"]}')
        gf = got.get("frame")
        if gf is None:
            fails.append("missing frame")
        else:
            dev_rel = [abs(gf[i] - want["frame_emu"][i]) for i in range(4)]
            if max(dev_rel) > TOL_EMU:
                fails.append("frame off by " + ", ".join(f"{d/EMU_PER_PT:.4f}pt" for d in dev_rel))
        if got.get("line_w") != want["stroke"]["width_emu"]:
            fails.append(f'stroke {got.get("line_w")} != {want["stroke"]["width_emu"]} EMU')
        if got.get("fill") != "none":
            fails.append(f'fill {got.get("fill")} != none')
        curve = ""
        if want["kind"] == "freeform" and got.get("path") is not None:
            src = {"frame": want["frame_emu"], "path_w": want["path"]["space_emu"][0],
                   "path_h": want["path"]["space_emu"][1],
                   "path": [(c[0], [(c[1][i], c[1][i + 1]) for i in range(0, len(c[1]), 2)])
                            for c in want["path"]["commands"]]}
            a, b = flatten(src), flatten(got)
            if len(a) != len(b):
                fails.append(f"curve point count {len(b)} != {len(a)}")
            else:
                d = max(max(abs(p[0] - q[0]), abs(p[1] - q[1])) for p, q in zip(a, b))
                curve = f"   curve max dev {d/EMU_PER_PT:.4f} pt"
                if d > TOL_EMU:
                    fails.append(f"curve dev {d/EMU_PER_PT:.4f}pt > 0.01pt")
        status = "OK" if not fails else "FAIL: " + "; ".join(fails)
        print(f'[{want["n"]:2d}] {want["kind"]:8s} frame=({gf[0] if gf else "?"},{gf[1] if gf else "?"},'
              f'{gf[2] if gf else "?"},{gf[3] if gf else "?"})  {status}{curve}')
        if fails:
            ok = False

    print("\nVERDICT:", "REPLICA MATCHES SPEC (tolerance 0.01pt)" if ok else "REPLICA DIFFERS FROM SPEC")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
