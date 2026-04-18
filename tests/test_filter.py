import io
import sys

from wkt_visualizer.filter import extract_wkt_from_line, read_stdin


def test_plain_point():
    assert extract_wkt_from_line("POINT(1 2)") == "POINT(1 2)"


def test_plain_polygon():
    result = extract_wkt_from_line("POLYGON((0 0,0 5,10 5,10 0,0 0))")
    assert result == "POLYGON((0 0,0 5,10 5,10 0,0 0))"


def test_labeled_line():
    result = extract_wkt_from_line("densified: POLYGON((0 0,0 5,10 5,10 0,0 0))")
    assert result == "POLYGON((0 0,0 5,10 5,10 0,0 0))"


def test_linestring():
    result = extract_wkt_from_line("LINESTRING(0 0, 1 1, 2 0)")
    assert result == "LINESTRING(0 0, 1 1, 2 0)"


def test_multipolygon_nested_parens():
    wkt = "MULTIPOLYGON(((0 0,0 1,1 1,1 0,0 0)),((2 2,2 3,3 3,3 2,2 2)))"
    result = extract_wkt_from_line(wkt)
    assert result == wkt


def test_case_insensitive():
    result = extract_wkt_from_line("polygon((0 0,0 1,1 1,1 0,0 0))")
    assert result == "POLYGON((0 0,0 1,1 1,1 0,0 0))"


def test_spaces_after_keyword():
    result = extract_wkt_from_line("POINT  (3 4)")
    assert result == "POINT(3 4)"


def test_no_wkt():
    assert extract_wkt_from_line("just some random text") is None


def test_dsv_not_matched():
    assert extract_wkt_from_line("1,2,3") is None


def test_invalid_wkt_returns_none():
    # Unbalanced parens
    assert extract_wkt_from_line("POLYGON((0 0,0 1,1 1") is None


def test_geometrycollection():
    wkt = "GEOMETRYCOLLECTION(POINT(1 2),LINESTRING(0 0,1 1))"
    result = extract_wkt_from_line(wkt)
    assert result == wkt


def test_trailing_text_ignored():
    line = "result: POINT(5 6) some trailing text"
    result = extract_wkt_from_line(line)
    assert result == "POINT(5 6)"


def test_multipoint():
    wkt = "MULTIPOINT((0 0),(1 1),(2 2))"
    result = extract_wkt_from_line(wkt)
    assert result == wkt


def _read_stdin_from_string(text):
    """Helper: feed a string to read_stdin() as if it were piped stdin."""
    old_stdin = sys.stdin
    sys.stdin = io.StringIO(text)
    try:
        return read_stdin()
    finally:
        sys.stdin = old_stdin


def test_hash_comment_sets_name():
    entries = _read_stdin_from_string("# My Point\nPOINT(1 2)\n")
    assert len(entries) == 1
    assert entries[0].name == "My Point"


def test_no_comment_uses_default_name():
    entries = _read_stdin_from_string("POINT(1 2)\n")
    assert len(entries) == 1
    assert entries[0].name == "Point 1"


def test_double_hash_sets_group():
    text = "## Inputs\nPOINT(1 2)\n"
    entries = _read_stdin_from_string(text)
    assert len(entries) == 1
    assert entries[0].group == "Inputs"
    assert entries[0].group_index == 1


def test_entries_before_any_group():
    text = "POINT(1 2)\n## Group A\nPOINT(3 4)\n"
    entries = _read_stdin_from_string(text)
    assert entries[0].group == ""
    assert entries[0].group_index == 0
    assert entries[1].group == "Group A"
    assert entries[1].group_index == 1


def test_full_example():
    text = (
        "## Inputs\n"
        "# First polygon\n"
        "POLYGON((0 0,0 5,10 5,10 0,0 0))\n"
        "# A point\n"
        "POINT(1 2)\n"
        "## Outputs\n"
        "# Result polygon\n"
        "POLYGON((1 1,1 4,9 4,9 1,1 1))\n"
    )
    entries = _read_stdin_from_string(text)
    assert len(entries) == 3

    assert entries[0].name == "First polygon"
    assert entries[0].group == "Inputs"
    assert entries[0].group_index == 1

    assert entries[1].name == "A point"
    assert entries[1].group == "Inputs"
    assert entries[1].group_index == 1

    assert entries[2].name == "Result polygon"
    assert entries[2].group == "Outputs"
    assert entries[2].group_index == 2


def test_comment_not_adjacent_to_wkt():
    """A # comment with a blank line before WKT should NOT name the entry."""
    text = "# A name\n\nPOINT(1 2)\n"
    entries = _read_stdin_from_string(text)
    assert len(entries) == 1
    assert entries[0].name == "Point 1"


def test_double_hash_not_used_as_name():
    """## lines define groups, not entity names."""
    text = "## Group Name\nPOINT(1 2)\n"
    entries = _read_stdin_from_string(text)
    assert entries[0].name == "Point 1"
    assert entries[0].group == "Group Name"
