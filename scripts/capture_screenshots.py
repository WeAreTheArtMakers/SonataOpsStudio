#!/usr/bin/env python3
from __future__ import annotations

import os
import time
from pathlib import Path

from playwright.sync_api import Error, sync_playwright


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = repo_root / "screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)

    base_url = os.environ.get("SONATA_SCREENSHOT_BASE_URL", "http://localhost:3000").rstrip("/")
    pages: list[tuple[str, str]] = [
        ("home", "/"),
        ("dashboard", "/dashboard"),
        ("anomalies", "/anomalies"),
        ("listen", "/listen"),
        ("copilot", "/copilot"),
        ("briefs", "/briefs"),
        ("admin", "/admin"),
    ]

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1720, "height": 980})
            page = context.new_page()

            for name, path in pages:
                url = f"{base_url}{path}"
                page.goto(url, wait_until="domcontentloaded", timeout=120_000)
                page.wait_for_timeout(1200)
                page.screenshot(path=str(output_dir / f"{name}.png"), full_page=True)
                print(f"captured: {name} -> {url}")

            browser.close()
    except Error as exc:
        print(f"playwright capture failed: {exc}")
        print("Install browsers once with: python3 -m playwright install chromium")
        return 1

    # Touch a tiny delay so CI file systems settle before git add in chained commands.
    time.sleep(0.2)
    print(f"screenshots saved under: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
