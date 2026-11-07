# Silk cover page — normative geometry spec

Source: single-slide deck `handmade.pptx`, page 1 (`ppt/slides/slide1.xml`). All values below are
transcribed from the OOXML and are the only authority for building the page — no reference deck,
screenshot, or image is needed.

## Page

| key | value |
| --- | --- |
| size | 960 × 540 pt = 12192000 × 6858000 EMU (16:9) |
| unit | 1 pt = 12700 EMU; SVG/Univer user unit = pt; origin top-left |
| background | #FFFFFF (inherited, page itself has no background element) |
| element count | 10 shapes, 0 text, 0 images, 0 groups |
| stroke | #000000, width 1 pt (12700 EMU), flat cap, miter join |
| fill | none on every shape |

## Elements (n = z-order, 1 = bottom)

| n | z | shape id | source name | kind | x | y | w | h | right | bottom |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **1** | 1 | 5 | 任意多边形: 形状 4 | freeform | 366.4827 | -2.6976 | 590.7411 | 677.0868 | 957.2238 | 674.3891 |
| **2** | 2 | 8 | 矩形 7 | rect | 519.2000 | 24.0000 | 271.2000 | 117.6000 | 790.4000 | 141.6000 |
| **3** | 3 | 9 | 矩形 8 | rect | 603.0000 | 78.4000 | 187.4000 | 160.7000 | 790.4000 | 239.1000 |
| **4** | 4 | 10 | 矩形 9 | rect | 603.0000 | 141.6000 | 136.2000 | 97.5000 | 739.2000 | 239.1000 |
| **5** | 5 | 11 | 矩形 10 | rect | 505.0500 | 187.2000 | 234.1500 | 149.8268 | 739.2000 | 337.0268 |
| **6** | 6 | 12 | 矩形 11 | rect | 505.0500 | 288.0000 | 452.1738 | 252.0000 | 957.2238 | 540.0000 |
| **7** | 7 | 13 | 矩形 12 | rect | 671.2000 | 391.2000 | 286.0238 | 148.8000 | 957.2238 | 540.0000 |
| **8** | 8 | 15 | 椭圆 14 | ellipse | 78.7035 | 123.7380 | 672.8000 | 168.5732 | 751.5035 | 292.3112 |
| **9** | 9 | 17 | 椭圆 16 | ellipse | 109.7535 | -81.3556 | 790.5929 | 333.3556 | 900.3465 | 252.0000 |
| **10** | 10 | 19 | 椭圆 18 | ellipse | 375.7161 | 177.6000 | 790.5929 | 333.3556 | 1166.3091 | 510.9556 |

## Same data in EMU (integers, byte-level authority)

| n | x (EMU) | y (EMU) | cx (EMU) | cy (EMU) | right | bottom |
| --- | --- | --- | --- | --- | --- | --- |
| **1** | 4654330 | -34260 | 7502412 | 8599002 | 12156742 | 8564742 |
| **2** | 6593840 | 304800 | 3444240 | 1493520 | 10038080 | 1798320 |
| **3** | 7658100 | 995680 | 2379980 | 2040890 | 10038080 | 3036570 |
| **4** | 7658100 | 1798320 | 1729740 | 1238250 | 9387840 | 3036570 |
| **5** | 6414135 | 2377440 | 2973705 | 1902800 | 9387840 | 4280240 |
| **6** | 6414135 | 3657600 | 5742607 | 3200400 | 12156742 | 6858000 |
| **7** | 8524240 | 4968240 | 3632502 | 1889760 | 12156742 | 6858000 |
| **8** | 999535 | 1571472 | 8544560 | 2140880 | 9544095 | 3712352 |
| **9** | 1393870 | -1033216 | 10040530 | 4233616 | 11434400 | 3200400 |
| **10** | 4771595 | 2255520 | 10040530 | 4233616 | 14812125 | 6489136 |

## Percentage of the page

| n | x% | y% | w% | h% |
| --- | --- | --- | --- | --- |
| **1** | 38.175% | -0.500% | 61.536% | 125.386% |
| **2** | 54.083% | 4.444% | 28.250% | 21.778% |
| **3** | 62.812% | 14.519% | 19.521% | 29.759% |
| **4** | 62.812% | 26.222% | 14.187% | 18.056% |
| **5** | 52.609% | 34.667% | 24.391% | 27.746% |
| **6** | 52.609% | 53.333% | 47.101% | 46.667% |
| **7** | 69.917% | 72.444% | 29.794% | 27.556% |
| **8** | 8.198% | 22.914% | 70.083% | 31.217% |
| **9** | 11.433% | -15.066% | 82.353% | 61.733% |
| **10** | 39.137% | 32.889% | 82.353% | 61.733% |

## Shared edges (they are exact, not "about equal")

| shared coordinate (pt) | elements |
| --- | --- |
| left x = 505.0500 | 5, 6 |
| left x = 603.0000 | 3, 4 |
| right x = 739.2000 | 4, 5 |
| right x = 790.4000 | 2, 3 |
| right x = 957.2238 | 1, 6, 7 |
| bottom y = 239.1000 | 3, 4 |
| bottom y = 540.0000 | 6, 7 |

## Element 1 — freeform ("silk fold")

- Closed path, 12 anchors / 11 cubic segments, path window 7502412 × 8599002 EMU == the frame,
  so path coordinates are frame-local at 1:1 scale.
- Draws a ribbon that enters from above the page, crosses it 5 times, and closes below the bottom
  edge (frame bottom 674.3891 pt). Control points leave the page on every side.
- Path commands (EMU, frame-local), in order:

| command | points (EMU, frame-local) |
| --- | --- |
| `moveTo` | 222470, 654020 |
| `cubicBezTo` | 386723, -624447, 931977, 371233, 1461990, 339060 |
| `cubicBezTo` | 1992003, 306887, 2750617, 342447, 3402550, 460980 |
| `cubicBezTo` | 4054483, 579513, 5437937, 826740, 5373590, 1050260 |
| `cubicBezTo` | 5309243, 1273780, 3124843, 1568420, 3016470, 1802100 |
| `cubicBezTo` | 2908097, 2035780, 4924857, 2125527, 4723350, 2452340 |
| `cubicBezTo` | 4521843, 2779153, 1348537, 3353193, 1807430, 3762980 |
| `cubicBezTo` | 2266323, 4172767, 7121110, 4406447, 7476710, 4911060 |
| `cubicBezTo` | 7832310, 5415673, 4388070, 6275887, 3941030, 6790660 |
| `cubicBezTo` | 3493990, 7305433, 5371897, 7796500, 4794470, 7999700 |
| `cubicBezTo` | 4217043, 8202900, 1241857, 9234140, 476470, 8009860 |
| `cubicBezTo` | -288917, 6785580, 58217, 1932487, 222470, 654020 |
| `Z` |  |

## Text

There is no text, no speaker notes, and no enabled placeholder on this page.
