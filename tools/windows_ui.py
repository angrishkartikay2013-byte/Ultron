from __future__ import annotations

TOOL = {
    "name": "windows_ui",
    "description": "Control Windows applications through pywinauto UI Automation when installed. Use for windows, dialogs, controls, buttons, and text fields that are not reliably reachable with mouse coordinates.",
}

def run(action: str, title: str = "", control: str = "", text: str = "") -> str:
    """Perform a Windows UI Automation action using pywinauto."""
    try:
        from pywinauto import Desktop
    except ImportError as exc:
        raise RuntimeError("pywinauto is not installed. Run scripts\\setup_ecosystem.ps1 -WithEnvironments.") from exc

    desktop = Desktop(backend="uia")
    if not title:
        windows = [w.window_text() for w in desktop.windows() if w.window_text()]
        return "Available windows: " + ", ".join(windows[:40])

    window = desktop.window(title_re=title)
    window.wait("exists ready", timeout=5)

    if action == "focus":
        window.set_focus()
        return f"Focused window matching {title!r}."
    if action == "inspect":
        return window.print_control_identifiers(depth=3) or f"Inspected window matching {title!r}."
    if action == "click":
        target = window.child_window(title=control, best_match=True)
        target.click_input()
        return f"Clicked control {control!r}."
    if action == "type":
        target = window.child_window(title=control, best_match=True)
        target.set_focus()
        target.type_keys(text, with_spaces=True)
        return f"Typed text into {control!r}."

    raise ValueError("action must be one of: focus, inspect, click, type")
