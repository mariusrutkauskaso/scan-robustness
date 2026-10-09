# Scan robustness: where QR decoding actually breaks

A small measurement harness for document-automation pipelines that read a code
off a scanned page.

Pipelines like this are usually built and demonstrated against a clean,
generated PDF. They then meet a real scanner, and the useful question turns out
not to be *does it work* but **at what point does it stop working, and does it
fail loudly or quietly**.

This answers that with measurements rather than opinion. It generates a
synthetic form, degrades it the way a cheap scanner or a phone camera would,
and reports where decoding breaks.

No third-party documents are included. The test page is generated, so every
number below can be reproduced by running the file.

## Running it

```
pip install -r requirements.txt
python scan_robustness.py
```

## Results

Reference page rendered at 400 dpi, then scaled down to simulate lower scan
settings. The printed code is 24 mm square with error correction level M.

### Scan resolution

| Scan setting | Code size | Result |
|---|---|---|
| 75 dpi | 71 px | **not decoded** |
| 100 dpi | 94 px | `DEMO-PO:10001` |
| 150 dpi | 142 px | `DEMO-PO:10001` |
| 200 dpi | 189 px | `DEMO-PO:10001` |
| 300 dpi | 283 px | `DEMO-PO:10001` |

### Adverse conditions

| Condition | Detail | Result |
|---|---|---|
| Cheap scanner | 150 dpi, JPEG quality 40 | `DEMO-PO:10001` |
| Cheap scanner | 200 dpi, JPEG quality 40 | `DEMO-PO:10001` |
| Page fed askew | 200 dpi, rotated 7 degrees | `DEMO-PO:10001` |
| Page fed upside-down | 200 dpi, rotated 180 degrees | `DEMO-PO:10001` |
| Out of focus | 150 dpi, heavy blur | **not decoded** |

### Parts of the code obscured

Tested at 300 dpi, so that resolution is not the limiting factor.

| Area covered | Share of the code | Result |
|---|---|---|
| Data area (centre) | 5% | `DEMO-PO:10001` |
| Data area (centre) | 10% | **not decoded** |
| Data area (centre) | 15% | **not decoded** |
| Data area (centre) | 25% | **not decoded** |
| Corner: top-left | 5% — finder pattern | **not decoded** |
| Corner: bottom-left | 5% — finder pattern | **not decoded** |
| Corner: bottom-right | 5% — no finder pattern here | `DEMO-PO:10001` |

## What this implies

**Resolution is rarely the problem.** Anything from 100 dpi upward decoded
cleanly, and that is below what any office scanner produces by default. JPEG
compression, a skewed page and a page fed in upside-down were all survivable.
Focus turned out to matter more than resolution: a heavily blurred 150 dpi scan
failed where a sharp 100 dpi scan succeeded.

**Error correction helps less than people assume.** Covering a tenth of the
data area was already enough to lose the code. "QR codes are self-healing" is
true only for small, scattered damage, not for a pen stroke or a stamp.

**The three corner squares tolerate nothing at all.** Five percent over any
finder pattern made the code undetectable, while the same patch over the
bottom-right corner — which has no finder pattern — changed nothing. Guidance
printed on a form should therefore protect the corners specifically, rather
than say "do not write on the code" and leave people to guess what matters.

**Design consequence.** Because failures here are silent by nature — an
unreadable code simply yields nothing — a production pipeline should treat
"not decoded" as a distinct state requiring attention, never as an empty
result. Where the same identifier is also printed as text, decoding the code
and reading the text independently, then comparing them, costs very little and
makes a wrong identifier close to impossible.

## Method and limits

The degradation model is deliberately simple: bilinear downscaling, Gaussian
blur, uniform pixel noise, optional JPEG compression and rotation. It
approximates a scanner rather than modelling one. Real scanners also introduce
banding, uneven illumination and dust.

Numbers are specific to a 24 mm code at error correction level M. A larger
code, or level Q or H, will move the thresholds — which is the point: these
should be measured per document, not assumed.

Decoding uses [zxing-cpp](https://github.com/zxing-cpp/zxing-cpp). Other
decoders will differ at the margins.

## Licence

MIT.
