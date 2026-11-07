# -*- coding: utf-8 -*-
"""Build the page assets for the silk cover page from references/page-spec.json.

Outputs (into <out_dir>, default: ./build):
  page-01.svg      -- author the slide page with univer_compile_svg
  pin_freeform.js  -- run with univer_execute AFTER the compile (see SKILL.md step 4)

Units: the spec stores OOXML EMU. The SVG uses slide user units (pt) = EMU / 12700.
"""
import json
import os
import sys

EMU_PER_PT = 12700.0


def fmt(v):
    """Round a pt value to 6 dp without trailing zeros."""
    s = f"{v:.6f}".rstrip("0").rstrip(".")
    if s in ("-0", ""):
        return "0"
    return s


def build(skill_dir, out_dir):
    spec_path = os.path.join(skill_dir, "references", "page-spec.json")
    spec = json.load(open(spec_path, encoding="utf-8"))
    page = spec["page"]
    style = spec["style"]
    stroke = style["stroke_color"]
    sw = fmt(style["stroke_width_pt"])
    P = page["width_pt"]
    H = page["height_pt"]

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{fmt(P)}" height="{fmt(H)}" '
        f'viewBox="0 0 {fmt(P)} {fmt(H)}">',
        f'  <!-- silk cover page: {len(spec["elements"])} unfilled outlines, stroke {stroke} {sw}pt. '
        f'Document order == bottom-to-top stacking order. -->',
    ]

    for el in spec["elements"]:
        x, y, w, h = el["frame_pt"]
        if el["kind"] == "rect":
            svg.append(
                f'  <rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                f'fill="none" stroke="{stroke}" stroke-width="{sw}"/>'
            )
        elif el["kind"] == "ellipse":
            svg.append(
                f'  <ellipse cx="{fmt(x + w / 2)}" cy="{fmt(y + h / 2)}" rx="{fmt(w / 2)}" ry="{fmt(h / 2)}" '
                f'fill="none" stroke="{stroke}" stroke-width="{sw}"/>'
            )
        elif el["kind"] == "freeform":
            d = []
            space_w, space_h = el["path"]["space_emu"]
            sx, sy = w / (space_w / EMU_PER_PT), h / (space_h / EMU_PER_PT)
            for op, vals in el["path"]["commands"]:
                pts = [(vals[i] / EMU_PER_PT * sx + x, vals[i + 1] / EMU_PER_PT * sy + y) for i in range(0, len(vals), 2)]
                if op == "moveTo":
                    d.append(f"M {fmt(pts[0][0])} {fmt(pts[0][1])}")
                elif op == "lnTo":
                    d.append(f"L {fmt(pts[0][0])} {fmt(pts[0][1])}")
                elif op == "cubicBezTo":
                    d.append("C " + " ".join(f"{fmt(a)} {fmt(b)}" for a, b in pts))
                elif op in ("close", "Z"):
                    d.append("Z")
            svg.append(f'  <path d="{" ".join(d)}" fill="none" stroke="{stroke}" stroke-width="{sw}"/>')
        else:
            raise SystemExit(f"unsupported kind: {el['kind']}")

    svg.append("</svg>")

    os.makedirs(out_dir, exist_ok=True)
    svg_path = os.path.join(out_dir, "page-01.svg")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg) + "\n")

    # ---- Facade calibration script -------------------------------------------
    ff = next(e for e in spec["elements"] if e["kind"] == "freeform")
    space_w, space_h = ff["path"]["space_emu"]
    x, y, w, h = ff["frame_pt"]
    cmds = []
    for op, vals in ff["path"]["commands"]:
        name = {"moveTo": "M", "lnTo": "L", "cubicBezTo": "C"}.get(op, "z")
        pts = ", ".join(str(int(round(v))) for v in vals)
        cmds.append(f'  {{ command: "{name}", points: [{pts}] }},')
    js = f"""// Pin the freeform (element {ff["n"]}, "silk fold") to the exact source geometry.
//
// WHY: univer_compile_svg keeps a <path> as custom geometry whose path window is expressed in
// whole slide units (1 unit ~ 1 pt), so the exported OOXML path is quantised to ~1 pt. Re-stating
// the same curve with an EMU-sized path window ({space_w} x {space_h}) plus the source frame makes the
// export write the source path coordinates verbatim (1 unit = 1 EMU).
//
// Run AFTER the final univer_compile_svg: a recompile rebuilds the page and drops this.
const slide = presentation.getSlideByIndex(0);
const target = slide.getShapes().find((sh) => {{
  const data = sh.getShapeData ? sh.getShapeData() : null;
  return data && data.isCustom;
}});
if (!target) throw new Error("freeform shape not found on page 1");

const dataArray = [
{chr(10).join(cmds)}
];
target.setCustomGeometry({{ pathLst: [{{ w: {space_w}, h: {space_h}, dataArray }}] }});
target.setTransform({{ left: {fmt(x)}, top: {fmt(y)}, width: {fmt(w)}, height: {fmt(h)} }});

const back = target.getCustomGeometry();
return {{
  id: target.getId(),
  frame: target.getTransform(),
  pathSpace: [back.pathLst[0].w, back.pathLst[0].h],
  commandCount: back.pathLst[0].dataArray.length,
}};
"""
    js_path = os.path.join(out_dir, "pin_freeform.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(js)

    return svg_path, js_path


if __name__ == "__main__":
    # usage: build_assets.py <skill-base> <workspace>   -> writes <workspace>/build/*
    skill_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workspace = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
    out_dir = workspace if os.path.basename(os.path.normpath(workspace)) == "build" \
        else os.path.join(workspace, "build")
    s, j = build(skill_dir, out_dir)
    print("wrote", s)
    print("wrote", j)
