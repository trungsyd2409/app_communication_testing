"""Start SpeakDaily.  Run:  python main.py"""
import sys
import traceback


def main():
    try:
        from speakdaily.ui.app import App
        App().mainloop()
    except Exception:
        # Show the error instead of closing silently (important for the .exe).
        details = traceback.format_exc()
        try:
            from speakdaily import paths
            (paths.data_dir() / "error_log.txt").write_text(details, encoding="utf-8")
        except Exception:
            pass
        try:
            from tkinter import Tk, messagebox
            root = Tk()
            root.withdraw()
            messagebox.showerror("SpeakDaily stopped", details[-1500:])
        except Exception:
            print(details, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
