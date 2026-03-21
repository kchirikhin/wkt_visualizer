from wkt_visualizer.filter import extract_wkt_from_line


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
