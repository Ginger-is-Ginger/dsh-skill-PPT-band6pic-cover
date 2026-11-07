---
name: silk-cover-page-replica
description: Build the complete silk cover page from scratch to within 0.01 pt, in two phases — phase A reproduces the abstract line-art base (10 unfilled 1 pt black outlines on a 960×540 pt page: one closed freeform bezier ribbon, six nested rectangles, three oversized bleeding ellipses), phase B turns it into the finished cover by merging that page into six fragments (duplicate the ribbon, Merge-Shapes intersect/subtract against the rectangles and ellipses), texture-filling each fragment from the seven reference images (tile as texture, cover-fit scale k), and finishing with a 5 pt three-stop white gradient outline — then exports .pptx and proves every number with a verifier. Use when asked to reproduce, clone, rebuild, or design this specific silk cover page, or to redo its Boolean/texture/gradient steps, with no reference deck or screenshot.
---

# Silk cover page — complete design skill

Two phases, one page. Phase A rebuilds the line-art base from numbers. Phase B runs the design pass
that the brief describes — duplicate, merge shapes, renumber, texture fill, gradient outline — and
ends with six filled fragments on a 960 × 540 pt page.

Load `univer` and `univer-slide` first. Everything normative lives in `references/`; nothing here
depends on a reference deck, a screenshot, or the original file.

## Files this skill ships

| Path (relative to this skill's base directory) | Purpose |
| --- | --- |
| `references/page-spec.md` / `.json` | Phase A geometry: 10 frames in pt / EMU / %, shared edges, the full freeform path |
| `references/design-spec.md` / `.json` | Phase B: the operation ledger (which rectangle merges with which ribbon copy), fill rule, outline spec, Facade capability map |
| `scripts/build_assets.py` | Phase A: emits `build/page-01.svg` + `build/pin_freeform.js` |
| `scripts/build_design.py` | Phase B: executes the Boolean ledger and emits `build/design.json`, `build/design_page.js`, `build/design-outline.{png,svg}`, `build/design-preview.png` |
| `scripts/design_geometry.py` | Polygon engine (non-zero winding raster, contour trace, Douglas-Peucker) used by phase B |
| `scripts/verify_slide.py` | Phase A acceptance: `.pptx` vs `page-spec.json` |
| `scripts/verify_design.py` | Phase B acceptance: `.pptx` vs `build/design.json` |

Never hand-type a coordinate. If a number must change, change it in the JSON, rebuild, re-verify.

---

## Phase A — reproduce the line-art base

Target: page 1 with **exactly 10 shapes, 0 text**, every shape unfilled, stroke `#000000`, **1 pt**,
in the fixed z-order.

### A1. Build the authoring assets

```bash
python <skill-base>/scripts/build_assets.py <skill-base> <workspace>
```

Writes `<workspace>/build/page-01.svg` (960 × 540, user unit = pt, document order = bottom-to-top)
and `<workspace>/build/pin_freeform.js`. The argument is a **workspace**; the script appends `/build`
(passing `<workspace>/build` also works — it is used as-is).

### A2. Create file, worktree, Slide Unit

`univer_new` → `univer_worktree` (`create`) → `univer_unit` (`kind: "slide"`). The new unit already
has one empty page; never append a page for page 1.

### A3. Compile the page

`univer_compile_svg` with `source` = `build/page-01.svg`, `page: 1`, default `mode: "replace"`.
`warnings` and `lints` must both be empty — the page has no text, so any lint finding means something
extra got in.

### A4. Calibrate the freeform (skippable only if you go straight to phase B)

`univer_execute` with `codeFile` = `build/pin_freeform.js`, same `file` / `worktreeId` / `unitId`.
Skipping it costs a measured **99.18 pt** frame error and 0.6557 pt on the curve — but it is irrelevant
if phase B follows immediately, because phase B deletes this shape. Pin when phase A's own export
must be exact.

Why: `univer_compile_svg` keeps a `<path>` as custom geometry whose path window is whole slide units
(1 unit ≈ 1 pt) and re-derives the frame from the ink box, so a plain compile exports the bezier at
≤ 0.66 pt error with a wrong frame. Re-stating the curve with an EMU-sized path window
(`7502412 × 8599002`) and the source frame makes the exporter write the source coordinates verbatim.

**Order matters:** a later compile replaces the page and drops the calibration — compile first, pin
last, re-pin after any recompile. Expected return:
`frame {left: 366.482677, top: -2.697638, width: 590.741102, height: 677.086772}`,
`pathSpace [7502412, 8599002]`, `commandCount 13`.

### A5. Verify the model, then look at it

- `univer_inspect`: `size {960, 540}`, `elementCounts {total: 10, text: 0, shapes: 10, images: 0}`.
- `univer_lint` `pages: [1]`: `findings: []`.- `univer_screenshot` `pages: [1]`, `scale: 1.5`: ribbon + 6 nested rectangles + 3 huge ellipses, all
  bleeding off the page edges.

The dashed “Click to add a title / text” boxes are the default layout's editor placeholders — not
page elements (`text: 0` proves it) and not in the export. Judge only the black outlines.

### A6. Prove it numerically — before phase B

`univer_export` **with the worktree's `worktreeId`** → `<workspace>/cold-lineart.pptx`, then
`python <skill-base>/scripts/verify_slide.py <pptx> <skill-base>`. Every row `OK`, verdict
`REPLICA MATCHES SPEC (tolerance 0.01pt)`.

Export and verify **now**: phase B replaces page 1, after which `verify_slide.py` can no longer pass
(it expects the ten line-art shapes). Keep that pptx as phase A's evidence.

Scope note: the Unit lives in the worktree, and a fresh file's trunk has no Units, so an export
without `worktreeId` fails with `Error [UNIT_NOT_FOUND]` — that error means “add the worktreeId”,
not “the page is missing”.

Do not report phase A success from a screenshot alone.

---

## Phase B — the design pass

Target: the same page ends with **exactly 6 shapes**, each a fragment of the ribbon, texture-filled
and finished with a gradient outline. The ten phase-A operands are consumed by the merges.

### B1. Check the reference images

The seven reference images live in the workspace as `a.*` … `g.*` (the brief says `a.jpg` … `g.jpg`;
PNG works identically — the builder accepts `png/jpg/jpeg` and only cares about pixel sizes).
`a … f` are consumed by elements `12-1 … 12-6`; `g` is unused.

### B2. Build the design assets

```bash
python <skill-base>/scripts/build_design.py <skill-base> <workspace> --images <workspace>
```

Takes ~3 s. Writes:

- `build/design.json` — the six finished elements (frames, EMU paths, tile scales, outline spec)
- `build/design_page.js` — the `univer_execute` script that materialises them
- `build/design-outline.png`, `build/design-preview.png` — proof sheets for eyeballing

It prints one line per element: label, source chain, frame, loop/point counts, image, `k`. If any
Boolean comes out empty it stops with that label — check the ledger's operand numbers. `--images`
is optional (it defaults to `<workspace>`); point it elsewhere only if the images live in another
directory. Accepted extensions: `png`, `jpg`, `jpeg`.

### B3. Run the design pass on the page

`univer_execute` with `codeFile` = `build/design_page.js`, same `file` / `worktreeId` / `unitId`.
On the phase-A page it consumes the ten line-art elements and inserts six; on an empty page it simply
inserts six. Expect `consumedElementCount: 10` (or 0), `elementsNow: 6`, and per element
`tile {scaleX, scaleY, alignment: "ctr"}`.

The script does three things the brief describes, in order: delete the operands, insert each
fragment as custom geometry, then `setImageFill` (tile) and `setStroke` (gradient) on it.

### B4. Verify the model, then look at it

- `univer_inspect`: `elementCounts {total: 6, text: 0, shapes: 6}`. **`images: 0` is correct** — the
  fragments use picture *fills*, not picture *elements*. Do not read that field as "the texture step
  failed"; the fill evidence is B3's return value and the exported `a:blipFill`.
- `univer_lint` `pages: [1]`: `findings: []` (still no text).
- `univer_screenshot` `pages: [1]`, `scale: 1.5`. What to judge:
  - six fragments that together read as one continuous silk sheet cut into bands;
  - **coverage, not pattern**: each fragment shows exactly **one** instance of its image's landmark —
    for `a` that is one circle centred in the band. Do **not** judge by "bands" or "stripes": the
    reference images are themselves vertically banded, so a correctly covered fragment still looks
    striped, and eyeballing it is how people wrongly conclude "k is too small". The authoritative
    check is numeric — `design.json`'s tile size must be ≥ its frame, and `k` must equal
    `max(w/img_w, h/img_h)`;
  - the joins between fragments are white lines about 7 px wide at scale 1.5 (5 pt × 1.5);
  - no fragment is empty, black, or clipped by its own frame.

Known canvas limitations: the canvas draws a gradient **outline** as a flat colour, so the three-stop
fade is not visible in the screenshot; and the exported ramp is horizontal (`a:lin ang="0"`), so even
in the `.pptx` the fade reads along each fragment's width, not uniformly on every join. The stops are
stored in the model and written to the export correctly — `verify_design.py` proves them. Do not
"fix" a flat-looking outline.

### B5. Export and prove it numerically

`univer_export` with the **worktree's `worktreeId`** → `<workspace>/design.pptx`, then

```bash
python <skill-base>/scripts/verify_design.py <workspace>/design.pptx <workspace>/build/design.json
```

It re-checks frames, silhouette IoU against the computed outlines, tile alignment and scale (and
re-derives `k` from the frame and the image's pixel size), and the outline's width, stop positions,
colours and **alphas**. Expected: six `OK` rows and `DESIGN MATCHES SPEC`.

Two honest limits of this gate, so you do not overclaim:

- It is **self-referential** by design: it proves the page materialised `design.json` faithfully. That
  `design.json` matches the brief is established by `references/design-spec.md` §1 (the ledger) and
  §4 (the expected numbers) — quote those when reporting, and note the silhouette IoU band.
- Same scope rule as A6: no `worktreeId` → `Error [UNIT_NOT_FOUND]`.

`design_page.js` is generated per workspace (it embeds absolute image paths) and clears page 1 before
inserting, so never run it on a page you want to keep.

### B6. Hand off

`univer_worktree` `ready`. Report the `.univer`, the `.pptx`, the verifier output, the screenshot,
and the `k` table. Do not merge unless asked.

---

## The base page, in one table

Frames are `x, y, w, h` in pt (page = 960 × 540). n = z-order, 1 = bottom.

| n | kind | x | y | w | h |
| --- | --- | --- | --- | --- | --- |
| 1 | freeform (closed bezier ribbon, 12 anchors) | 366.4827 | -2.6976 | 590.7411 | 677.0868 |
| 2 | rect | 519.2000 | 24.0000 | 271.2000 | 117.6000 |
| 3 | rect | 603.0000 | 78.4000 | 187.4000 | 160.7000 |
| 4 | rect | 603.0000 | 141.6000 | 136.2000 | 97.5000 |
| 5 | rect | 505.0500 | 187.2000 | 234.1500 | 149.8268 |
| 6 | rect | 505.0500 | 288.0000 | 452.1738 | 252.0000 |
| 7 | rect | 671.2000 | 391.2000 | 286.0238 | 148.8000 |
| 8 | ellipse | 78.7035 | 123.7380 | 672.8000 | 168.5732 |
| 9 | ellipse | 109.7535 | -81.3556 | 790.5929 | 333.3556 |
| 10 | ellipse | 375.7161 | 177.6000 | 790.5929 | 333.3556 |

Self-checkable facts: 1/6/7 share the right edge **957.2238**; 2/3 share **790.4**; 4/5 share
**739.2**; 3/4 share bottom **239.1**; 5/6 share left **505.05**; 6/7 sit on the page bottom **540**.
9 and 10 are the *same* 790.5929 × 333.3556 ellipse translated twice. Five shapes bleed off the page
(1 above and below, 9 above, 10 to the right) — never clamp them.

## Design pass contract

- **Merge Shapes**: `2∩1`, `4∩1-3`, `6∩1-5` → `11-1`, `11-3`, `11-5`;
  `3−1-2`, `5−1-4`, `7−1-6` → `11-2`, `11-4`, `11-6` (rectangle is the base of a subtract);
  then `11-1−8` → `11-1-1`, `11-2∩9` → `11-2-1`, `11-5∩10` → `11-5-1`;
  renumber `[11-1-1, 11-2-1, 11-3, 11-4, 11-5-1, 11-6]` → `12-1 … 12-6`; fill with `a … f` → `13-1 … 13-6`.
- **k** = `max(w_el / img_px_w, h_el / img_px_h)`; `scaleX = scaleY = k`; alignment `ctr`. One tile
  then covers the element exactly. (OOXML export: `sx = sy = k × 133333.33`.)
- **Outline**: gradient, 5 pt, three stops `[0.20 white transparency 100 %]`,
  `[0.50 white transparency 0 %]`, `[0.80 white transparency 100 %]` — i.e. opacity `0 / 1 / 0`,
  because the Facade stores opacity while the brief speaks of transparency.

## Failure modes

| Symptom | Cause | Fix |
| --- | --- | --- |
| phase A: freeform curve dev ≈ 0.3–0.7 pt / frame off | `pin_freeform.js` not run, or run before a recompile | rerun A4, re-export |
| phase A: element count ≠ 10 | background rect, group, or leftover from a previous attempt | recompile page 1 with `mode: "replace"` (never `add`), re-pin |
| phase B: builder stops with “reference image not found: x” | images not in `--images` dir, or an extension outside png/jpg/jpeg | point `--images` at the workspace holding `a…g` |
| phase B: builder stops with “Boolean produced an empty result” | operand pair does not overlap (wrong ledger numbers) | check `design-spec.json` stage rows against the brief |
| verifier: “fill is not a tiled picture” | solid fill used, or `imageFillMode` omitted | `setImageFill` + `ShapeImageFillModeEnum.Tile` + `imageTile` |
| verifier: “tile scale … != k” | `k` computed with 96-dpi points instead of pixels, or averaged instead of `max` | recompute from `design.json`; do not hand-tune |
| verifier: “outline is not a gradient line” | `SolidLine` used | `lineStrokeType: GradientLine` + `gradientStops` |
| verifier: “stop alpha …” | transparency fed into `opacity` (inverted alphas) | `opacity = 1 − transparency` → `0 / 1 / 0` |
| verifier: silhouette IoU < 0.995 | `design.json` and the page came from different builds | rerun B2 then B3 against the same workspace |
| canvas outline looks flat white, no fade | the canvas does not render gradient-outline alphas (renderer limit) | expected — check the export instead (`verify_design.py` proves the three stops) |
| `Error [UNIT_NOT_FOUND]` on export | `worktreeId` omitted; the Unit lives only in the worktree | pass the worktree's `worktreeId` |
| phase B `univer_inspect` shows `images: 0` | picture *fills* are not picture *elements* | expected — check `design_page.js`'s return and the exported `a:blipFill` |
| phase A rows off by ≤ 0.004 pt if you tighten the tolerance | 1/12700 EMU export rounding on the nine primitive shapes (only the pinned freeform is exact) | keep 0.01 pt; that is the export grid, not a modelling error |
| screenshot: fragments show a grid of many tiles | `k` too small — tile smaller than the element | recompute `k` (it must reach cover) |
| screenshot: dashed title/text boxes | default-layout editor placeholders | expected; ignore (step B4 proves `text: 0`) |

## Do not

- Do not add a background rectangle, title, caption, or watermark: phase A is 10 shapes, phase B is 6.
- Do not group, merge-by-hand, or replace the ribbon with straight segments; the phase-B outlines are
  polyline approximations *produced by* the Boolean engine at ≤ 0.12 pt, not by redrawing.
- Do not rescale or “fit” anything to the page: the design deliberately bleeds.
- Do not hand-edit `build/design.json` or `build/design_page.js`; regenerate from the JSON specs.
- Do not claim phase B success without `VERDICT: DESIGN MATCHES SPEC`.

## 说明（中文）

这个技能现在覆盖完整的封面页设计：**阶段 A** 复刻纯线稿底页（960×540 pt 上 10 个「无填充 + 1 pt
黑线」形状：1 条闭合贝塞尔丝带 + 6 个嵌套矩形 + 3 条出血椭圆，误差 < 0.01 pt）；**阶段 B** 才是设计：
把丝带复制成 6 份，与矩形/椭圆做「相交/剪除」合并，重编号为 12-1…12-6，再用参考图 a…f
作「图片或纹理填充 + 平铺 + 刻度 k」（k 取长宽比的最大值，正好铺满一个图块），最后把线条设成
5 磅三光圈白色渐变线。

两个关键点：**Univer 没有「合并形状」布尔运算**，所以相交/剪除由 `scripts/design_geometry.py`
按同样的操作数、同样的顺序精确算出（0.12 pt 折线逼近，验收用轮廓 IoU 卡 0.995）；**透明度要转成
不透明度**（100 % 透明 = 0 不透明），否则渐变线会反相。验收闸门是
`verify_design.py` 必须打印 `DESIGN MATCHES SPEC`。
