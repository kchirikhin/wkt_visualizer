import logging
import os
import sys

# Some snap-confined terminals (e.g. Ghostty) leak GDK_PIXBUF_MODULE_FILE pointing
# at a snap-internal loaders cache that lacks the SVG loader, which silently breaks
# every SVG-only icon (e.g. view-conceal-symbolic). Drop it so gdk-pixbuf falls
# back to the system cache. Must happen before any GTK/Gdk import.
_pixbuf_cache = os.environ.get("GDK_PIXBUF_MODULE_FILE", "")
if "/snap/" in _pixbuf_cache:
    del os.environ["GDK_PIXBUF_MODULE_FILE"]

logging.basicConfig(
    stream=sys.stderr,
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
)


def main():
    from .app import WktVisualizerApp
    from .filter import read_stdin

    entries = read_stdin()
    if not sys.stdin.isatty() and len(entries) == 0:
        logging.warning("No WKT geometries found in piped input")

    app = WktVisualizerApp(entries)
    app.run(None)


if __name__ == "__main__":
    main()
