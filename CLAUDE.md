# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WKT Visualizer is a pipe-friendly CLI + GUI tool for capturing WKT (Well-Known Text) geometry from terminal output and visualizing it interactively. It's designed for rapid prototyping with Boost.Geometry learning examples.

**Tech Stack:** Python 3.10+, GTK 4 via PyGObject, Cairo rendering, Shapely for WKT parsing, Poetry for dependencies.

## Development Commands

```bash
# Setup
poetry install

# Run the application (pipe mode)
echo "POLYGON((0 0,0 5,10 5,10 0,0 0))" | poetry run wkt-visualizer
./build/Release/buffer | poetry run wkt-visualizer

# Run tests
poetry run pytest
poetry run pytest tests/test_filter.py -v  # Single test file
poetry run pytest tests/test_filter.py::test_hash_comment_sets_name -v  # Single test

# Install as CLI tool
poetry install  # Creates wkt-visualizer command
```

## Architecture

### Data Flow
```
stdin → filter.py (WKT extraction) → WktEntry objects → GTK 4 App
                                                           ↓
                    ←─────────────────────────────────────────
                    │
         ┌──────────┴───────────┬─────────────────┐
         │                      │                 │
    panels.py              canvas.py         properties.py
 (Hidden/Displayed        (Cairo renderer)  (Property editor)
     lists)
```

### Core Components

**filter.py** (`read_stdin`, `extract_wkt_from_line`)
- Reads stdin line-by-line, extracts WKT using regex + balanced parenthesis matching
- Validates with Shapely, discards invalid WKT
- Supports grouping via `# Group Name` headers
- Supports naming via `## Comment` prefix (immediately before WKT)
- Returns list of `WktEntry` objects

**model.py** (`WktEntry`)
- GObject-based model for GTK bindings with GObject.Property decorators
- Properties: name, color (RGB as separate color_r/g/b floats), line_width, fill_opacity
- Holds: entry_id, raw_line, wkt string, Shapely geometry, group, group_index
- Property changes trigger canvas redraw via notify signals

**app.py** (`WktVisualizerApp`, `WktVisualizerWindow`)
- Main GTK Application and Window setup
- Manages two `Gio.ListStore` instances (hidden/displayed)
- Coordinates panels, canvas, and properties bar
- Handles property change notifications and triggers canvas redraws

**panels.py** (`GeometryPanels`)
- Dual ListBox UI: Hidden and Displayed geometry lists
- Transfer controls: Show/Hide buttons, Show All/Hide All buttons
- Group headers with per-group Show All/Hide All when groups are present
- Maintains ordered insertion by (group_index, entry_id)

**canvas.py** (`WktCanvas`, `CanvasState`)
- GTK DrawingArea with Cairo rendering
- Cartesian coordinate system (Y-axis points up)
- Pan (middle-click drag), zoom (scroll wheel, cursor-centered)
- Auto-fit bounds with 10% padding
- Renders grid, axes, geometries, cursor coordinates
- Drawing order: follows Displayed list order (top = bottom layer)

**properties.py** (`PropertiesBar`)
- Bottom bar for editing selected entry properties
- Binds to selected WktEntry: name, color picker, line width slider, fill opacity slider
- Changes apply immediately and trigger canvas redraw

**palette.py**
- 12 visually distinct colors cycled through as geometries load

### Coordinate System

Canvas uses world-to-screen transforms maintained in `CanvasState`:
```python
screen_x = (world_x - offset_x) * scale
screen_y = height - (world_y - offset_y) * scale
```

Navigation: scroll to zoom (cursor-centered), middle-drag to pan, double-click or Home key to auto-fit.

## Testing

Tests use pytest. Testing approach:
- **filter.py**: Unit tests for WKT extraction, balanced parenthesis matching, naming/grouping logic
- Mock stdin with `io.StringIO` for testing `read_stdin()`
- **canvas.py**: Coordinate transform math tests (exists in spec, may need implementation)

When writing tests, maintain the pattern of focused unit tests. Use the `_read_stdin_from_string` helper pattern for stdin-based tests.

## Input Format

Standard WKT on stdin:
```
POINT(1 2)
POLYGON((0 0,0 5,10 5,10 0,0 0))
```

With naming (## comment immediately before WKT):
```
## My Point
POINT(1 2)
## Buffer result
POLYGON((0 0,0 5,10 5,10 0,0 0))
```

With grouping (# headers, mirroring Markdown levels):
```
# Inputs
## First polygon
POLYGON((0 0,0 5,10 5,10 0,0 0))

# Outputs
## Buffer result
POLYGON((1 1,1 4,9 4,9 1,1 1))
```

Supports all OGC types: POINT, LINESTRING, POLYGON, MULTIPOINT, MULTILINESTRING, MULTIPOLYGON, GEOMETRYCOLLECTION.

## Common Patterns

**GTK/GObject Integration:**
- All model classes that need property binding must inherit from `GObject.Object`
- Use `GObject.Property(type=...)` for bindable properties
- Use `entry.connect("notify::property-name", callback)` for change notifications
- Disconnect handlers when rebinding to avoid leaks (see `_on_selection_changed` in app.py)

**List Management:**
- Use `Gio.ListStore` for GTK list models
- Maintain ordering with `_insert_ordered` when moving between stores
- Call `invalidate_headers()` after list changes when using header functions

**Canvas Rendering:**
- Always use Cartesian coordinates (Y-up) in world space
- Use `state.world_to_screen()` for rendering
- Call `queue_draw()` to trigger redraw
- Set `draw_func` callback instead of overriding draw method

## System Dependencies

GTK 4 and GObject Introspection libraries required (typically pre-installed on GNOME desktops):
- libgtk-4-dev
- libgirepository-2.0-dev
- gir1.2-gtk-4.0
