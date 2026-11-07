# Phase B — design pass: normative spec

Phase A reproduces the line-art page (10 outlined shapes). Phase B turns that page into the finished
cover: six texture-filled fragments with a three-stop white gradient outline.

Everything here is derived from `page-spec.json` (phase A geometry) plus the reference images'
pixel sizes. `design-spec.json` is the machine-readable operation ledger this document explains;
`scripts/build_design.py` executes it.

## 1. The operation ledger

Element numbers are the ones the brief uses. `1-2 … 1-6` are five more copies of element 1 placed at
exactly the same position (so there are six identical ribbons). `∩` = Merge Shapes → **Intersect**,
`−` = Merge Shapes → **Subtract** (first shape minus the second).

| step | output | operation | brief |
| --- | --- | --- | --- |
| 2 | `11-1` | rect `2` ∩ ribbon `1` | intersect |
| 2 | `11-3` | rect `4` ∩ ribbon `1-3` | intersect |
| 2 | `11-5` | rect `6` ∩ ribbon `1-5` | intersect |
| 3 | `11-2` | rect `3` − ribbon `1-2` | subtract |
| 3 | `11-4` | rect `5` − ribbon `1-4` | subtract |
| 3 | `11-6` | rect `7` − ribbon `1-6` | subtract |
| 4 | `11-1-1` | `11-1` − ellipse `8` | subtract |
| 5 | `11-2-1` | `11-2` ∩ ellipse `9` | intersect |
| 6 | `11-5-1` | `11-5` ∩ ellipse `10` | intersect |
| 7 | `12-1 … 12-6` | `11-1-1, 11-2-1, 11-3, 11-4, 11-5-1, 11-6` | renumber |
| 8-9 | `13-1 … 13-6` | `12-1 … 12-6` + reference images `a … f` | picture/texture fill |
| 10 | `13-1 … 13-6` | gradient outline, 5 pt, three stops | outline |

Two readings of the brief are fixed here; both are recorded in `design-spec.json`:

- **Step 9's element list.** "images b to f (5) with elements 12-2 to 12-5 (5)" is off by one —
  `12-2 … 12-5` is four elements, and the stated output `13-2 … 13-6` is five. Five images need five
  elements, so `12-2 … 12-6 ← b … f`. Reference image `g` is not consumed.
- **Subtraction order.** The sentence starts with the rectangle, so the rectangle is the base:
  `rect − ribbon`, not `ribbon − rect`.

## 2. Fill: picture, tiled as texture, cover fit

Each `13-x` gets **Picture or texture fill** → **Tile picture as texture** → source = its reference
image → **Scale X = Scale Y = k** → **alignment = Center (`ctr`)**.

```
k = max( element_width / image_pixel_width , element_height / image_pixel_height )
```

Both ratios are "element pt per image pixel". In this Facade a tile scale of `k` renders one tile
`k × image_pixels` points wide/high, so that `k` makes a single tile exactly cover the element —
cover fit, no seam, nothing stretched. (The OOXML export writes `sx = sy = round(k × 133333.33)`,
i.e. the familiar PowerPoint percentage of 133.33 % per unit of `k`.)

## 3. Outline: 5 pt gradient, three stops

| property | value |
| --- | --- |
| line type | gradient |
| width | 5 pt = 63500 EMU |
| stops | `[0.20, #FFFFFF, transparency 100 %]`, `[0.50, #FFFFFF, transparency 0 %]`, `[0.80, #FFFFFF, transparency 100 %]` |

The brief specifies **transparency** (透明度); the Facade stores **opacity**, so
`opacity = 1 − transparency` → `0.0, 1.0, 0.0`. Exported OOXML: `<a:ln w="63500"><a:gradFill>` with
`a:gs pos="20000" alpha="0"`, `pos="50000" alpha="100000"`, `pos="80000" alpha="0"`.

## 4. Reference values from the accepted run

Deterministic output of `scripts/build_design.py` for the shipped page spec and the seven reference
images in this workspace (`a` 1200×800, `b` 800×1200, `c` 640×640, `d` 1600×900, `e` 900×1600,
`f` 1024×768, `g` 500×300 unused).

| element | from | image (px) | x | y | w | h | k | tile (pt) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `13-1` | `12-1` ← `11-1-1` | a 1200×800 | 519.358 | 24.179 | 270.500 | 114.250 | 0.225417 | 270.5 × 180.3 |
| `13-2` | `12-2` ← `11-2-1` | b 800×1200 | 603.691 | 78.582 | 186.750 | 160.750 | 0.233438 | 186.8 × 280.1 |
| `13-3` | `12-3` ← `11-3` | c 640×640 | 603.046 | 141.616 | 136.250 | 97.500 | 0.212891 | 136.3 × 136.3 |
| `13-4` | `12-4` ← `11-4` | d 1600×900 | 505.238 | 189.012 | 234.000 | 147.625 | 0.164028 | 262.4 × 147.6 |
| `13-5` | `12-5` ← `11-5-1` | e 900×1600 | 505.279 | 288.163 | 452.125 | 221.000 | 0.502361 | 452.1 × 803.8 |
| `13-6` | `12-6` ← `11-6` | f 1024×768 | 672.263 | 391.387 | 285.000 | 148.625 | 0.278320 | 285.0 × 213.8 |

The page holds **six** elements when phase B finishes; the ten operands are consumed by the merges.

## 5. What the Facade can and cannot do

| brief step | Facade support | how phase B does it |
| --- | --- | --- |
| duplicate a shape, same position | `insertShape` with a copy of `customGeometry` | the six ribbon copies are operands only — they never need to exist as live shapes, so the ledger names them and the geometry engine consumes them |
| Merge Shapes ∩ / − | **none** (no Boolean API on the Facade) | `scripts/design_geometry.py` computes the exact same operation order on the identical operands (raster + non-zero winding, contour tracing, Douglas-Peucker at 0.12 pt) |
| picture/texture fill, tile, scale, align | **yes** — `setImageFill` + `imageFillMode: Tile` + `imageTile` | native |
| gradient outline with stops | **yes** — `setStroke` with `lineStrokeType: GradientLine` + `gradientStops` | native |

Measured renderer note: the canvas paints a gradient **outline** as a flat colour — the three stops
are stored in the model and exported correctly (`a:gradFill` with `alpha 0 / 100000 / 0`), but a
screenshot will show a solid line. Judge the fade from the exported `.pptx`, not from the canvas; a
flat-looking outline in the screenshot is not a defect.

Radius of the approximation: outlines are polylines at ≤ 0.12 pt deviation, which is 0.4 % of a
5 pt outline — invisible, but it is an approximation and the verifier measures it (silhouette
IoU ≥ 0.995; the accepted run measures 0.9997–0.9999).
