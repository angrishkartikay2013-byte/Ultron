from __future__ import annotations

TOOL = {
    "name": "browser",
    "description": "Use Playwright for deterministic browser navigation, page text extraction, screenshots, and basic interaction.",
}

_browser = None

def _get_browser():
    global _browser
    if _browser is not None:
        return _browser
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is not installed. Run scripts\\setup_ecosystem.ps1 -WithEnvironments.") from exc
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=False)
    _browser = (pw, browser, browser.new_page())
    return _browser

def run(action: str, url: str = "", selector: str = "", text: str = "") -> str:
    """Navigate and interact with the active Chromium page."""
    _, _, page = _get_browser()
    if action == "open":
        if not url:
            raise ValueError("url is required for open")
        page.goto(url, wait_until="domcontentloaded")
        return f"Opened {page.url}\nTitle: {page.title()}"
    if action == "read":
        return page.locator("body").inner_text(timeout=5000)[:12000]
    if action == "click":
        page.locator(selector).click(timeout=5000)
        return f"Clicked {selector!r}."
    if action == "type":
        page.locator(selector).fill(text, timeout=5000)
        return f"Filled {selector!r}."
    if action == "screenshot":
        path = "memory/browser_screenshot.png"
        page.screenshot(path=path, full_page=False)
        return f"Saved browser screenshot to {path}."
    if action == "close":
        global _browser
        _browser[1].close()
        _browser[0].stop()
        _browser = None
        return "Closed the browser."
    raise ValueError("action must be one of: open, read, click, type, screenshot, close")
