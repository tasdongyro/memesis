"""Render the animated README images from docs/readme/anim_*.html and mark.html into GIFs.

    python tools/readme_anim.py            # all
    python tools/readme_anim.py run        # one

Each page defines window.frame(t) (t in seconds) and window.LOOP. Frames are stepped, not recorded,
so every GIF is deterministic and loops cleanly. One shared palette per GIF, identical frames merged.
"""
import io
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "readme"
#        name     page               css size     scale  fps
ANIMS = {
    "mark":  ("mark.html",       (512, 512),  0.6,  20),
    "run":   ("anim_run.html",   (1000, 520), 0.9,  12),
    "trust": ("anim_trust.html", (1100, 560), 0.82, 12),
}
only = sys.argv[1:]


def render(browser, page_name, size, scale, fps):
    w, h = size
    pg = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=scale)
    pg.goto((SRC / page_name).as_uri(), wait_until="networkidle")
    pg.wait_for_function("document.fonts.status === 'loaded'")
    pg.wait_for_timeout(400)
    loop = pg.evaluate("window.LOOP")
    n = int(round(loop * fps))
    frames = []
    for i in range(n):
        pg.evaluate(f"window.frame({i / fps})")
        frames.append(Image.open(io.BytesIO(pg.screenshot())).convert("RGB"))
    pg.close()
    return frames


def to_gif(frames, fps, out):
    # merge identical neighbours into longer frames
    merged, durs = [], []
    for f in frames:
        if merged and f.tobytes() == merged[-1].tobytes():
            durs[-1] += 1000 / fps
        else:
            merged.append(f); durs.append(1000 / fps)
    # one palette for the whole loop, built from a strip of sampled frames
    step = max(1, len(merged) // 12)
    sample = merged[::step]
    strip = Image.new("RGB", (merged[0].width, merged[0].height * len(sample)))
    for k, f in enumerate(sample):
        strip.paste(f, (0, k * f.height))
    pal = strip.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in merged]
    q[0].save(out, save_all=True, append_images=q[1:], duration=[int(d) for d in durs], loop=0, optimize=False, disposal=1)
    return len(merged), out.stat().st_size


with sync_playwright() as p:
    try:
        browser = p.chromium.launch(channel="chrome")
    except Exception:
        browser = p.chromium.launch()
    for name, (page_name, size, scale, fps) in ANIMS.items():
        if only and name not in only:
            continue
        frames = render(browser, page_name, size, scale, fps)
        out = SRC / f"{name}.gif"
        k, b = to_gif(frames, fps, out)
        print(f"wrote {out.relative_to(ROOT)}  {frames[0].width}x{frames[0].height}  {k} frames  {b / 1e6:.2f} MB")
    browser.close()
