"""Full-page screenshots of the local site. Usage: .venv/bin/python tools/screenshots.py [base_url]"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
OUT = Path(__file__).resolve().parent.parent / "screenshots"; OUT.mkdir(exist_ok=True)
SHOTS = [("home.png", "/index.html", 1440, None), ("newsletter.png", "/newsletter.html", 1440, None),
         ("home-newsletter-section.png", "/index.html", 1440, "#newsletter"),
         ("daily-2026-10-27.png", "/news/2026-10-27/index.html", 1440, None),
         ("about.png", "/about.html", 1440, None), ("archive.png", "/news/index.html", 1440, None),
         ("home-mobile.png", "/index.html", 390, None)]
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    for name, path, w, sel in SHOTS:
        pg = b.new_page(viewport={"width": w, "height": 900}, device_scale_factor=1)
        pg.goto(BASE + path, wait_until="networkidle"); pg.wait_for_timeout(400)
        if sel: pg.locator(sel).screenshot(path=str(OUT / name))
        else: pg.screenshot(path=str(OUT / name), full_page=True)
        print(OUT / name); pg.close()
    b.close()
