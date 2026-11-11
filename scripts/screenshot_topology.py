#!/usr/bin/env python3
"""Capture the EVE-NG topology with the built-in auto-zoom.

Environment:
  EVE_URL   e.g. https://192.168.100.33
  EVE_USER  EVE-NG username
  EVE_PASS  EVE-NG password
  OUT       output png (default topology.png)
"""
import os

from playwright.sync_api import sync_playwright

URL = os.environ.get("EVE_URL", "https://192.168.100.33").rstrip("/")
USER = os.environ.get("EVE_USER", "admin")
PASS = os.environ.get("EVE_PASS", "")
OUT = os.environ.get("OUT", "topology.png")

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(ignore_https_errors=True, viewport={"width": 1920, "height": 1080},
                        device_scale_factor=2)
    pg = ctx.new_page()
    pg.goto(f"{URL}/#/login", wait_until="networkidle", timeout=60000)
    ins = pg.query_selector_all("input")
    ins[0].fill(USER)
    ins[1].fill(PASS)
    pg.get_by_role("button", name="Sign In").click()
    pg.wait_for_timeout(8000)
    # the last-opened lab is displayed; fit all elements
    pg.click(".autozoom-icon")
    pg.wait_for_timeout(2500)
    pg.screenshot(path=OUT)
    print("saved", OUT)
    b.close()
