# -*- coding: utf-8 -*-
"""Phase B — the design pass: merge the line-art page into six texture-filled fragments.

    python build_design.py <skill-base> <workspace> [--images <dir>]

Reads `references/page-spec.json` (the page that phase A reproduces) and
`references/design-spec.json` (the operation ledger), computes the Boolean results,
and writes:

    <workspace>/build/design.json        -- the six finished elements (frames, EMU paths, fills)
    <workspace>/build/design_page.js     -- univer_execute script that materialises them
    <workspace>/build/design-outline.svg -- outline proof sheet for eyeballing
    <workspace>/build/design-preview.png -- flat colour proof sheet

No coordinates are hand-typed anywhere: every number below is derived from the two JSON files
plus the reference images' pixel sizes.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design_geometry as G  # noqa: E402

E = G.EMU_PER_PT
S = 8.0          # rasterisation resolution, px per pt
EPS = 0.12       # contour simplification tolerance, pt


# --------------------------------------------------------------------------- #
# operand geometry
# --------------------------------------------------------------------------- #
def flat_ribbon(el):
    ox, oy = el["frame_pt"][0], el["frame_pt"][1]
    return G.flatten_path(el["path"]["commands"], (ox, oy), scale=192)


def rect_poly(el):
    x, y, w, h = el["frame_pt"]
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def ellipse_poly(el, n=2048):
    x, y, w, h = el["frame_pt"]
    cx, cy, rx, ry = x + w / 2, y + h / 2, w / 2, h / 2
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return [(cx + rx * math.cos(a), cy + ry * math.sin(a)) for a in t]


def bbox(polys, pad=3.0):
    pts = np.vstack([np.asarray(p, dtype=float) for p in polys])
    return (pts[:, 0].min() - pad, pts[:, 1].min() - pad, pts[:, 0].max() + pad, pts[:, 1].max() + pad)


def boolean_masks(a_polys, b_polys, op, crop=None):
    """Return (mask, grid) for A ∩ B or A − B. `crop` limits the window to A's own bbox."""
    window = bbox(a_polys) if (op == "subtract" or crop) else bbox(a_polys + b_polys)
    if crop is not None:
        window = bbox(crop)
    g = G.Grid(*window, S)
    ma = G.winding_mask(a_polys, g)
    if b_polys is None:
        return ma, g
    mb = G.winding_mask(b_polys, g)
    return ((ma & mb) if op == "intersect" else (ma & ~mb)), g


def combine(mask_a, grid_a, other_polys, op):
    """Second-stage Boolean: feed stage-1 result polygons back through the raster."""
    polys = G.mask_to_polygons(mask_a, grid_a, EPS)
    if not polys:
        return np.zeros((1, 1), dtype=bool), G.Grid(0, 0, 1, 1, S), polys
    x0, y0, x1, y1 = bbox([other_polys[0]], 3.0) if op == "intersect" else bbox(polys)
    if op == "intersect":
        x0, y0, x1, y1 = bbox([p for p in polys] + [other_polys[0]], 3.0)
    g = G.Grid(x0, y0, x1, y1, S)
    ma = G.winding_mask(polys, g)
    mb = G.winding_mask(other_polys, g)
    m = (ma & mb) if op == "intersect" else (ma & ~mb)
    return m, g, polys


# --------------------------------------------------------------------------- #
# build
# --------------------------------------------------------------------------- #
def build(skill_dir, workspace, images_dir=None, image_ext=("png", "jpg", "jpeg")):
    spec = json.load(open(os.path.join(skill_dir, "references", "page-spec.json"), encoding="utf-8"))
    ledger = json.load(open(os.path.join(skill_dir, "references", "design-spec.json"), encoding="utf-8"))
    els = {e["n"]: e for e in spec["elements"]}

    images_dir = images_dir or workspace
    from PIL import Image

    def image_info(name):
        for ext in image_ext:
            p = os.path.join(images_dir, f"{name}.{ext}")
            if os.path.exists(p):
                with Image.open(p) as im:
                    return os.path.abspath(p), im.size
        raise SystemExit(f"reference image not found: {name} ({'/'.join(image_ext)}) in {images_dir}")

    ribbon = flat_ribbon(els[1])
    ribbons = {k: ribbon for k in ledger["ribbon_copies"]}   # identical copies, same position

    # ---- stage 1: 11-x -----------------------------------------------------
    stage1 = {}
    for op in ledger["stage1"]:
        base = rect_poly(els[op["rect"]])
        curve = ribbons[op["ribbon"]]
        m, g = boolean_masks([base], [curve], op["mode"])
        stage1[op["out"]] = (m, g, op)

    # ---- stage 2: 11-x-1 ---------------------------------------------------
    stage2 = {}
    for op in ledger["stage2"]:
        m0, g0, _ = stage1[op["from"]]
        m, g, base_polys = combine(m0, g0, [ellipse_poly(els[op["ellipse"]])], op["mode"])
        stage2[op["out"]] = (m, g)

    # ---- renumber 12-x -----------------------------------------------------
    order = ledger["final_order"]
    shots = []
    for i, label in enumerate(order, 1):
        if label in stage2:
            m, g = stage2[label]
        else:
            m, g, _ = stage1[label]
        polys = G.mask_to_polygons(m, g, EPS)
        if not polys:
            raise SystemExit(f"{label}: Boolean produced an empty result")
        bb = bbox(polys, 0.0)
        shots.append(dict(label=f"12-{i}", origin=label, loops=polys, bbox=bb, grid=g))

    # ---- assign images and k ----------------------------------------------
    final = []
    for shot, fill in zip(shots, ledger["fills"]):
        bb = shot["bbox"]
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        src, (iw, ih) = image_info(fill["image"])
        k = max(w / iw, h / ih)
        final.append(
            dict(
                label=f"13-{fill['index']}", source=shot["label"], origin=shot["origin"],
                frame_pt=[bb[0], bb[1], w, h],
                size_pt=[w, h],
                loops=shot["loops"],
                image=dict(name=fill["image"], path=src, px=[iw, ih]),
                k=round(k, 6),
                tile=dict(scaleX=round(k, 6), scaleY=round(k, 6), alignment="ctr"),
            )
        )

    # ---- encode for the Facade -------------------------------------------
    out_el = []
    for e in final:
        x, y, w, h = e["frame_pt"]
        space = [int(round(w * E)), int(round(h * E))]
        cmds = G.polygons_to_dataarray(e["loops"], (x, y), space[0], space[1])
        out_el.append(
            dict(
                label=e["label"], source=e["source"], origin=e["origin"],
                frame_pt=[round(v, 6) for v in e["frame_pt"]],
                path=dict(space_emu=space, commands=cmds),
                image=dict(name=e["image"]["name"], path=e["image"]["path"],
                           px=e["image"]["px"]),
                k=e["k"], tile=e["tile"],
                fill=dict(mode="tile", alignment="ctr"),
                stroke=ledger["stroke"],
                loop_count=len(e["loops"]), point_count=len(cmds),
            )
        )

    design = dict(
        page=spec["page"],
        note="Phase-B result of the operation ledger in references/design-spec.json",
        stroke=ledger["stroke"],
        elements=out_el,
    )
    os.makedirs(os.path.join(workspace, "build"), exist_ok=True)
    design_path = os.path.join(workspace, "build", "design.json")
    json.dump(design, open(design_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    write_facade_script(out_el, ledger, os.path.join(workspace, "build", "design_page.js"))
    write_proofs(final, os.path.join(workspace, "build"), spec["page"])

    for e in out_el:
        print(f'{e["label"]:6s} <- {e["source"]:8s} <- {e["origin"]:8s} '
              f'frame=({e["frame_pt"][0]:.3f},{e["frame_pt"][1]:.3f},{e["frame_pt"][2]:.3f},{e["frame_pt"][3]:.3f}) '
              f'loops={e["loop_count"]:2d} pts={e["point_count"]:4d} '
              f'img={e["image"]["name"]}({e["image"]["px"][0]}x{e["image"]["px"][1]}) k={e["k"]:.6f}')
    print("wrote", design_path)
    return design


# --------------------------------------------------------------------------- #
# emitters
# --------------------------------------------------------------------------- #
def write_facade_script(elements, ledger, path):
    blocks = []
    for e in elements:
        x, y, w, h = e["frame_pt"]
        cmds = ",\n      ".join(
            '{ command: "%s", points: [%s] }' % (c["command"], ", ".join(str(v) for v in c["points"]))
            for c in e["path"]["commands"]
        )
        blocks.append(
            f"""  {{
    label: "{e['label']}",
    image: "{e['image']['path'].replace(chr(92), '/')}",
    frame: {{ left: {x}, top: {y}, width: {w}, height: {h} }},
    space: {{ w: {e['path']['space_emu'][0]}, h: {e['path']['space_emu'][1]} }},
    tile: {{ scaleX: {e['tile']['scaleX']}, scaleY: {e['tile']['scaleY']}, alignment: "{e['tile']['alignment']}" }},
    dataArray: [
      {cmds}
    ],
  }},"""
        )

    stops = ",\n        ".join(
        '{ position: %s, color: "%s", opacity: %s }' % (s["position"], s["color"], s["opacity"])
        for s in ledger["stroke"]["gradient_stops"]
    )
    js = f"""// Generated by build_design.py -- do not edit by hand.
//
// Phase B of the silk cover: replace the ten line-art elements with the six Boolean
// fragments, each texture-filled and finished with a 5 pt three-stop white gradient outline.
//
// Two things the Facade cannot do, and how they are handled here:
//   * Merge Shapes (Boolean)  -> the outlines were computed by scripts/design_geometry.py and
//     are carried in as custom geometry; the ten operands are deleted first, exactly as a
//     destructive merge would consume them.
//   * (nothing else) -- tiled picture fill and gradient strokes are native Facade features.
const {{ readFile }} = await import("node:fs/promises");

const SHAPES = [
{chr(10).join(blocks)}
];

const STROKE = {{
  lineStrokeType: univerAPI.Enum.ShapeLineTypeEnum.GradientLine,
  width: {ledger['stroke']['width_pt']},
  color: "{ledger['stroke']['gradient_stops'][1]['color']}",
  gradientStops: [
        {stops}
  ],
}};

const slide = presentation.getSlideByIndex(0);

// 1. the merges consume their operands: clear the line-art page
const consumed = slide.getElements().map((el) => el.getId());
for (const el of slide.getElements()) slide.deleteElement(el);

// 2. materialise the six fragments
const created = [];
for (const spec of SHAPES) {{
  const bytes = await readFile(spec.image);
  const ext = spec.image.split(".").pop().toLowerCase();
  const mime = ext === "jpg" || ext === "jpeg" ? "image/jpeg" : "image/png";
  const dataUri = `data:${{mime}};base64,${{Buffer.from(bytes).toString("base64")}}`;
  const shape = slide.insertShape({{
    shapeType: univerAPI.Enum.ShapeTypeEnum.Rect,
    transform: {{ left: spec.frame.left, top: spec.frame.top, width: spec.frame.width, height: spec.frame.height }},
    shapeData: {{
      isCustom: true,
      customGeometry: {{ pathLst: [{{ w: spec.space.w, h: spec.space.h, dataArray: spec.dataArray }}] }},
    }},
  }});
  if (!shape) throw new Error(`insertShape failed for ${{spec.label}}`);
  shape.setImageFill(dataUri, univerAPI.Enum.ShapeImageSourceTypeEnum.BASE64, {{
    imageFillMode: univerAPI.Enum.ShapeImageFillModeEnum.Tile,
    imageTile: spec.tile,
    imageOpacity: 1,
  }});
  shape.setStroke(STROKE);
  created.push({{
    label: spec.label,
    id: shape.getId(),
    frame: shape.getTransform(),
    tile: (shape.getShapeData().fill || {{}}).imageTile,
  }});
}}

return {{
  consumedElementCount: consumed.length,
  created,
  elementsNow: slide.getElements().length,
}};
"""
    open(path, "w", encoding="utf-8").write(js)


def write_proofs(final, outdir, page):
    from PIL import Image, ImageDraw

    SC = 1.5
    W, H = int(page["width_pt"] * SC), int(page["height_pt"] * SC)
    colors = [(46, 92, 138), (138, 84, 52), (86, 122, 62), (110, 66, 132), (44, 122, 116), (140, 116, 52)]
    flat = Image.new("RGB", (W, H), "white")
    outline = Image.new("RGB", (W, H), "white")
    d1, d2 = ImageDraw.Draw(flat), ImageDraw.Draw(outline)
    for i, e in enumerate(final):
        for poly in e["loops"]:
            pts = [(x * SC, y * SC) for x, y in poly]
            d1.polygon(pts, fill=colors[i % len(colors)])
            d2.polygon(pts, outline=(0, 0, 0))
        x, y, w, h = e["frame_pt"]
        d2.rectangle([x * SC, y * SC, (x + w) * SC, (y + h) * SC], outline=(200, 60, 60))
    flat.save(os.path.join(outdir, "design-preview.png"))
    outline.save(os.path.join(outdir, "design-outline.png"))

    path_attr = []
    for e in final:
        for poly in e["loops"]:
            segs = " ".join(f"{'M' if j == 0 else 'L'} {x:.3f} {y:.3f}" for j, (x, y) in enumerate(poly))
            path_attr.append(f'  <path d="{segs} Z" fill="none" stroke="#000000" stroke-width="5"/>')
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{page["width_pt"]}" height="{page["height_pt"]}" '
        f'viewBox="0 0 {page["width_pt"]} {page["height_pt"]}">\n'
        + "\n".join(path_attr)
        + "\n</svg>\n"
    )
    open(os.path.join(outdir, "design-outline.svg"), "w", encoding="utf-8").write(svg)


if __name__ == "__main__":
    skill_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(HERE)
    workspace = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
    images = None
    if "--images" in sys.argv:
        images = sys.argv[sys.argv.index("--images") + 1]
    build(skill_dir, workspace, images)
