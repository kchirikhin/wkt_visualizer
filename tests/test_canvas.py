import math

from wkt_visualizer.canvas import CanvasState, _nice_interval


def test_world_to_screen_identity():
    """With scale=1, offset=0, the transform just flips Y."""
    s = CanvasState()
    sx, sy = s.world_to_screen(5, 3, 100)
    assert sx == 5.0
    assert sy == 97.0  # 100 - 3


def test_screen_to_world_roundtrip():
    s = CanvasState()
    s.scale = 2.5
    s.offset_x = 10
    s.offset_y = 20
    height = 500
    wx, wy = 15.0, 25.0
    sx, sy = s.world_to_screen(wx, wy, height)
    wx2, wy2 = s.screen_to_world(sx, sy, height)
    assert abs(wx2 - wx) < 1e-10
    assert abs(wy2 - wy) < 1e-10


def test_fit_bounds_centering():
    s = CanvasState()
    s.fit_bounds(0, 0, 100, 100, 800, 600)
    # After fitting, the center of the geometry (50, 50) should map to center of screen
    sx, sy = s.world_to_screen(50, 50, 600)
    assert abs(sx - 400) < 1
    assert abs(sy - 300) < 1


def test_fit_bounds_single_point():
    s = CanvasState()
    s.fit_bounds(5, 5, 5, 5, 400, 400)
    # Should not crash, should have reasonable scale
    assert s.scale > 0
    sx, sy = s.world_to_screen(5, 5, 400)
    assert abs(sx - 200) < 1
    assert abs(sy - 200) < 1


def test_nice_interval():
    assert _nice_interval(0.03) == 0.02 or _nice_interval(0.03) == 0.05
    assert _nice_interval(7) == 5 or _nice_interval(7) == 10
    assert _nice_interval(150) == 200
    assert _nice_interval(1) == 1


def test_fit_bounds_aspect_ratio():
    """Wide geometry in tall canvas should scale to width."""
    s = CanvasState()
    s.fit_bounds(0, 0, 200, 10, 800, 600)
    # Scale should be constrained by the wider dimension
    assert s.scale > 0
    # Both corners should be on screen
    sx1, sy1 = s.world_to_screen(0, 0, 600)
    sx2, sy2 = s.world_to_screen(200, 10, 600)
    assert 0 <= sx1 <= 800
    assert 0 <= sx2 <= 800
