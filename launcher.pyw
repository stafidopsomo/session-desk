from sessiondesk.__main__ import main

if __name__ == "__main__":
    try:
        main()
    except Exception:
        import sys
        if "--no-browser" in sys.argv:
            raise
        import ctypes
        ctypes.windll.user32.MessageBoxW(None,
            "Session Desk could not start. Check that your user data folder is writable and try again. Your workspaces were not reset.",
            "Session Desk", 0x10)
