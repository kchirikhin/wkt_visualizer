import logging
import sys

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
