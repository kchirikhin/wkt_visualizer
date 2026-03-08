# WKT Visualizer — Technical Specification

## Overview

A pipe-friendly CLI + GUI tool for capturing WKT (Well-Known Text) geometry
statements from terminal output and visualizing them interactively. Designed
for rapid prototyping with Boost.Geometry learning examples.

**Typical usage:**

```bash
./build/Release/buffer | wkt-visualizer
./build/Release/difference | wkt-visualizer
echo "POLYGON((0 0,0 5,10 5,10 0,0 0))" | wkt-visualizer
```

## Technology Stack

| Concern             | Choice                                                     |
| ------------------- | ---------------------------------------------------------- |
| Language            | Python 3.12+                                               |
| Dependency manager  | Poetry                                                     |
| GUI toolkit         | GTK 4 via PyGObject (native GNOME look-and-feel)           |
| Geometry parsing    | Shapely 2.x (`shapely.wkt.loads`)                          |
| Canvas rendering    | Cairo (via GTK 4 `Gtk.DrawingArea` + `cairo` context)      |
| WKT filtering       | Python `re` (stdlib)                                       |

### Rationale

- **GTK 4 + PyGObject** — first-class GNOME citizen, supports drag-and-drop
  natively, hardware-accelerated rendering, Adwaita styling out of the box.
- **Shapely** — de-facto standard for parsing and manipulating WKT in Python;
  handles all OGC geometry types; provides bounding-box calculations needed for
  auto-scaling.
- **Cairo** — already bundled with GTK; proven 2D vector graphics with
  sub-pixel precision, ideal for Cartesian coordinate rendering.

## Architecture

```
stdin (pipe)
    │
    ▼
┌──────────────┐
│  WKT Filter  │  — reads stdin line-by-line, extracts valid WKT
└──────┬───────┘
       │ list[WktEntry]
       ▼
┌──────────────────────────────────────────────────┐
│              GTK 4 Application Window            │
│                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐ │
│  │  Hidden     │  │  Displayed │  │  Canvas    │ │
│  │  List       │  │  List      │  │            │ │
│  │  (source)   │  │  (active)  │  │  Cartesian │ │
│  │             │  │            │  │  coords    │ │
│  │  drag ────────► drop       │  │            │ │
│  │  ◄──────────── drag        │  │  auto-fit  │ │
│  │             │  │            │  │  + scroll  │ │
│  │             │  │            │  │  + zoom    │ │
│  └────────────┘  └────────────┘  └────────────┘ │
│                                                  │
│  ┌──────────────────────────────────────────────┐│
│  │ Properties bar (selected item):              ││
│  │   Name: [___]  Color: [■]  Width: [slider]   ││
│  └──────────────────────────────────────────────┘│
└──────────────────────────────────────────────────┘
```

## Component Details

### 1. WKT Filter (stdin reader)

**Responsibility:** Read piped input, extract WKT statements.

**Rules:**
- Read stdin line-by-line until EOF.
- A line is considered WKT if it matches (case-insensitive) one of the OGC
  geometry type prefixes after optional leading whitespace and an optional
  text label prefix (e.g., `"densified: POLYGON(...)"`).
- Supported WKT types:
  `POINT`, `LINESTRING`, `POLYGON`, `MULTIPOINT`, `MULTILINESTRING`,
  `MULTIPOLYGON`, `GEOMETRYCOLLECTION`.
- Extraction regex (applied per line):

  ```
  ((?:MULTI)?(?:POINT|LINESTRING|POLYGON)|GEOMETRYCOLLECTION)\s*\(.*\)
  ```

- Validate each extracted string with `shapely.wkt.loads()`; discard on
  parse error (log warning to stderr).
- Lines that don't match are silently skipped.

**Output:** A list of `WktEntry` objects passed to the GUI.

```python
@dataclass
class WktEntry:
    id: int                          # auto-increment
    raw_line: str                    # original stdin line
    wkt: str                         # extracted WKT substring
    geometry: BaseGeometry           # parsed Shapely object
    name: str                        # editable label, default "Geometry N"
    color: tuple[float, float, float]  # RGB 0..1, assigned from palette
    line_width: float                # default 2.0
    fill_opacity: float              # default 0.3
    visible: bool                    # False initially (hidden list)
```

### 2. GUI — Main Window

**Framework:** `Gtk.Application` + `Gtk.ApplicationWindow` (GTK 4).

**Layout:** Horizontal `Gtk.Paned` with:
- **Left pane:** Vertical `Gtk.Box` containing two list panels.
- **Right pane:** Canvas drawing area.
- **Bottom bar:** Properties panel (conditionally visible when an item is
  selected).

#### 2a. Hidden List & Displayed List

Each list is a `Gtk.ListView` backed by a `Gio.ListStore` of `WktEntry`
model objects.

| Feature              | Details                                          |
| -------------------- | ------------------------------------------------ |
| Item display         | Name + geometry type icon + color swatch         |
| Move to other list   | Drag-and-drop between the two lists              |
| Quick toggle         | Double-click moves item to the other list        |
| Multi-select         | Ctrl+click / Shift+click for bulk operations     |
| Context menu         | Right-click → Rename, Change color, Delete       |
| Keyboard             | Enter to toggle, Delete to remove                |

When an item moves to the **Displayed** list, `visible` is set to `True`;
the canvas is redrawn. Moving back sets `visible = False`.

#### 2b. Properties Bar

Appears at the bottom when an item in either list is selected.

| Control         | Widget                | Bound property        |
| --------------- | --------------------- | --------------------- |
| Name            | `Gtk.Entry`           | `WktEntry.name`       |
| Color           | `Gtk.ColorButton`     | `WktEntry.color`      |
| Line width      | `Gtk.Scale` (1–10)    | `WktEntry.line_width` |
| Fill opacity    | `Gtk.Scale` (0–1)     | `WktEntry.fill_opacity` |
| WKT text        | `Gtk.Label` (selectable, monospace, truncated) | read-only |

Changes are applied immediately and the canvas redraws.

### 3. Canvas (Cartesian Renderer)

**Widget:** `Gtk.DrawingArea` with a `draw` callback receiving a
`cairo.Context`.

#### Coordinate System

The canvas uses a Cartesian coordinate system (Y-axis points up). A
world-to-screen affine transform is maintained:

```
screen_x = (world_x - offset_x) * scale
screen_y = height - (world_y - offset_y) * scale
```

#### Auto-Scaling

When the set of visible geometries changes:
1. Compute the union bounding box of all visible geometries
   (`shapely.ops.unary_union` → `.bounds`).
2. Add 10% padding on each side.
3. Compute scale and offset to fit the bounding box in the drawable area.

#### Manual Navigation

| Action             | Input                     |
| ------------------ | ------------------------- |
| Zoom in/out        | Scroll wheel              |
| Pan                | Middle-click drag         |
| Reset to auto-fit  | Double-click on canvas or Home key |

Zoom is centered on the mouse cursor position.

#### Rendering

Draw order follows the Displayed list order (top of list drawn first =
bottom layer). For each visible `WktEntry`:

- **Point / MultiPoint:** Filled circle (radius = `line_width * 2` px).
- **LineString / MultiLineString:** Stroked path.
- **Polygon / MultiPolygon:** Filled + stroked (fill uses `color` at
  `fill_opacity`; stroke uses `color` at full opacity).
- **GeometryCollection:** Recurse into components.

#### Grid & Axes

- Light gray grid lines at "nice" intervals determined by current scale.
- X and Y axes drawn as thin dark lines when the origin (0,0) is in view.
- Coordinate labels on grid lines.
- Mouse cursor position displayed in world coordinates (bottom-right
  corner).

### 4. Color Palette

A predefined palette of 12 visually distinct colors is cycled through as
geometries are loaded. The user can override via the color picker.

```python
PALETTE = [
    (0.122, 0.467, 0.706),   # blue
    (1.000, 0.498, 0.055),   # orange
    (0.173, 0.627, 0.173),   # green
    (0.839, 0.153, 0.157),   # red
    (0.580, 0.404, 0.741),   # purple
    (0.549, 0.337, 0.294),   # brown
    (0.890, 0.467, 0.761),   # pink
    (0.498, 0.498, 0.498),   # gray
    (0.737, 0.741, 0.133),   # olive
    (0.090, 0.745, 0.812),   # cyan
    (0.682, 0.780, 0.910),   # light blue
    (0.988, 0.553, 0.384),   # salmon
]
```

## Project Structure

```
wkt_visualizer/
├── pyproject.toml
├── README.md
├── SPEC.md                        # this file
├── wkt_visualizer/
│   ├── __init__.py
│   ├── __main__.py                # entry point (python -m wkt_visualizer)
│   ├── app.py                     # Gtk.Application setup
│   ├── filter.py                  # stdin WKT filtering
│   ├── model.py                   # WktEntry dataclass + ListStore models
│   ├── canvas.py                  # DrawingArea + Cairo rendering
│   ├── panels.py                  # Hidden/Displayed list panels
│   ├── properties.py              # Properties bar widget
│   └── palette.py                 # Color palette constants
└── tests/
    ├── test_filter.py
    └── test_canvas.py             # coordinate transform math tests
```

## Entry Point & CLI

The package installs a console script `wkt-visualizer`:

```toml
[tool.poetry.scripts]
wkt-visualizer = "wkt_visualizer.__main__:main"
```

**Behavior:**

1. If stdin is a pipe (not a TTY), read all lines from stdin, filter WKT,
   build the entry list.
2. If stdin is a TTY (no pipe), start with an empty entry list (the user
   can later paste WKT or use a file-open dialog — stretch goal).
3. Launch the GTK application window.

## Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.12"
PyGObject = "^3.50"
Shapely = "^2.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
```

**System packages required** (Ubuntu/Fedora):
- `libgtk-4-dev`, `libgirepository-2.0-dev`, `gir1.2-gtk-4.0` (or
  equivalents).
- These are typically pre-installed on GNOME desktops.

## Non-Functional Requirements

| Requirement         | Target                                         |
| ------------------- | ---------------------------------------------- |
| Startup latency     | < 1 s for up to 100 geometries                 |
| Rendering           | 60 fps for up to 50 visible geometries         |
| Memory              | < 100 MB for typical workloads                 |
| Accessibility       | Keyboard navigation for all list operations    |

## Out of Scope (possible future enhancements)

- Live/streaming stdin (watch mode).
- Export canvas to SVG/PNG.
- Load WKT from file via file-open dialog.
- Edit WKT text inline and re-parse.
- Coordinate reference system (CRS) support.
- 3D geometry support.
