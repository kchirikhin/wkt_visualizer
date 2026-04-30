# WKT Visualizer

A pipe-friendly GTK 4 viewer for [Well-Known Text (WKT)](https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry)
geometry. Drop WKT statements into stdin and get an interactive Cartesian
canvas — useful for prototyping with Boost.Geometry, Shapely, PostGIS, or
anything else that emits WKT.

```bash
echo "POLYGON((0 0,0 5,10 5,10 0,0 0))" | wkt-visualizer
./build/Release/buffer | wkt-visualizer
psql -At -c "SELECT ST_AsText(geom) FROM features" | wkt-visualizer
```

## Features

- Reads WKT from stdin (any line containing a valid WKT statement is picked up).
- Hidden / Displayed lists with drag-and-drop, double-click toggle, multi-select.
- Per-geometry properties: name, color, line width, fill opacity.
- Auto-fit to bounds, cursor-centered scroll-zoom, middle- or right-click pan.
- Native GNOME look-and-feel; integrates with the GNOME launcher.
- Supports all OGC types: `POINT`, `LINESTRING`, `POLYGON`, `MULTIPOINT`,
  `MULTILINESTRING`, `MULTIPOLYGON`, `GEOMETRYCOLLECTION`.

## Installation

### Requirements

- Linux with GTK 4 system libraries (typically pre-installed on GNOME).
  Debian/Ubuntu: `sudo apt install libgtk-4-1 gir1.2-gtk-4.0`.
  Fedora: `sudo dnf install gtk4 gobject-introspection`.
- Python 3.10 or newer.

### Install with pipx (recommended)

```bash
pipx install wkt-visualizer
```

Or from a local clone:

```bash
pipx install .
```

This puts `wkt-visualizer` and `wkt-visualizer-install-desktop` on your
`PATH` (typically `~/.local/bin/`).

### Register the GNOME launcher entry

To make WKT Visualizer appear in the Activities grid / dock with its icon,
run once after installing:

```bash
wkt-visualizer-install-desktop
```

This writes a `.desktop` file to `~/.local/share/applications/` and copies
the app icons to `~/.local/share/icons/hicolor/`. Launching from Activities
will start the app with no piped input — useful when you want to paste WKT
later or just see the empty canvas.

To remove it:

```bash
wkt-visualizer-install-desktop --uninstall
```

## Usage

### Naming geometries

Prefix a geometry with `##` on the line immediately above it to set its
display name:

```
## My buffer
POLYGON((0 0,0 5,10 5,10 0,0 0))
```

### Grouping

Group geometries under a header using `#`:

```
# Inputs
## First polygon
POLYGON((0 0,0 5,10 5,10 0,0 0))

# Outputs
## Buffer result
POLYGON((-1 -1,-1 6,11 6,11 -1,-1 -1))
```

Groups appear as collapsible sections in the Hidden / Displayed panels with
per-group Show All / Hide All buttons.

### Mouse and keyboard controls

| Action                    | Input                                |
| ------------------------- | ------------------------------------ |
| Zoom (cursor-centered)    | Scroll wheel                         |
| Pan                       | Middle-click drag *or* right-click drag |
| Auto-fit to visible       | Double-click on canvas, or `Home` key |
| Quit                      | `Ctrl+Q`                             |

In the side panels, double-click an entry to move it between Hidden and
Displayed; drag-and-drop also works.

## Development

The project uses Poetry. The repo's dev venv uses `--system-site-packages`
to pick up the system PyGObject; if you don't have it installed, recent
PyGObject (≥ 3.50) ships Linux wheels and `poetry install` will pull them.

```bash
poetry install
poetry run wkt-visualizer < sample.wkt
poetry run pytest
```

To build a wheel:

```bash
poetry build
ls dist/
```

See [SPEC.md](SPEC.md) for the technical specification.
