"""Render the README images from docs/readme/*.html with Playwright (installed Chrome, 2x scale).

    python tools/readme_assets.py            # all
    python tools/readme_assets.py hello      # one page

Writes docs/readme/<name>.png, docs/social.png (1280x640) and docs/logo.png (512) + docs/logo-128.png.
Pages load Google Fonts, so this needs network once.
"""
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "readme"
PAGES = {
    "mark": (512, 512), "hello": (1280, 700), "vocab": (1280, None), "trust": (1100, 640),
    "failure": (1100, 590), "people": (1100, 476), "social": (1280, 640),
}
only = [a for a in sys.argv[1:]]


def ready(page):
    page.wait_for_function("document.fonts.status === 'loaded'")
    page.wait_for_timeout(500)


with sync_playwright() as p:
    try:
        browser = p.chromium.launch(channel="chrome")
    except Exception:
        browser = p.chromium.launch()
    for name, (w, h) in PAGES.items():
        if only and name not in only:
            continue
        pg = browser.new_page(viewport={"width": w, "height": h or 800}, device_scale_factor=2)
        pg.goto((SRC / f"{name}.html").as_uri(), wait_until="networkidle")
        ready(pg)
        out = SRC / f"{name}.png"
        pg.screenshot(path=str(out), full_page=h is None)
        pg.close()
        print("wrote", out.relative_to(ROOT))
    browser.close()

if not only or "social" in only:
    Image.open(SRC / "social.png").convert("RGB").save(ROOT / "docs" / "social.png", optimize=True)
if not only or "mark" in only:
    im = Image.open(SRC / "mark.png").convert("RGBA")
    im.save(ROOT / "docs" / "logo.png", optimize=True)
    im.resize((128, 128), Image.LANCZOS).save(ROOT / "docs" / "logo-128.png", optimize=True)
print("done")
