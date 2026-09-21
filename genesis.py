from __future__ import annotations

import traceback


def main() -> int:
    print("⚡ ULTRON GENESIS starting...")
    try:
        from ui.orb import run_genesis
        return run_genesis()
    except Exception as exc:
        print("\n❌ ULTRON failed to start:")
        print(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
        print("\nPress Enter to close...")
        input()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
