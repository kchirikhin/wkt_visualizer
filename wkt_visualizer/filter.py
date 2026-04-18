import logging
import re
import sys

import shapely

from .model import WktEntry
from .palette import get_color

log = logging.getLogger(__name__)

_WKT_KEYWORD = re.compile(
    r"((?:MULTI)?(?:POINT|LINESTRING|POLYGON)|GEOMETRYCOLLECTION)\s*\(",
    re.IGNORECASE,
)


def _extract_balanced(text: str, start: int) -> str | None:
    """Extract a balanced-parenthesis substring starting at text[start]=='('."""
    if start >= len(text) or text[start] != "(":
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def extract_wkt_from_line(line: str) -> str | None:
    """Extract a WKT geometry string from a line of text, or return None."""
    m = _WKT_KEYWORD.search(line)
    if not m:
        return None

    keyword = m.group(1).upper()
    paren_start = m.end() - 1  # position of the '('
    balanced = _extract_balanced(line, paren_start)
    if balanced is None:
        return None

    wkt_str = keyword + balanced
    try:
        shapely.from_wkt(wkt_str)
    except Exception:
        log.warning("Invalid WKT: %s", wkt_str[:80])
        return None
    return wkt_str


def read_stdin() -> list[WktEntry]:
    """Read stdin (if piped) and return a list of WktEntry objects."""
    if sys.stdin.isatty():
        return []

    entries = []
    current_group = ""
    group_index = 0
    prev_line = ""

    for line in sys.stdin:
        line = line.rstrip("\n\r")
        stripped = line.lstrip()

        # ## group header (must check before single #)
        if stripped.startswith("##"):
            group_index += 1
            current_group = stripped[2:].lstrip()
            prev_line = stripped
            continue

        # # entity name comment
        if stripped.startswith("#"):
            prev_line = stripped
            continue

        wkt_str = extract_wkt_from_line(line)
        if wkt_str is None:
            prev_line = line
            continue

        # Determine name from previous # comment
        name = ""
        if prev_line.startswith("#") and not prev_line.startswith("##"):
            name = prev_line[1:].lstrip()

        geometry = shapely.from_wkt(wkt_str)
        entry = WktEntry(
            entry_id=len(entries),
            raw_line=line,
            wkt=wkt_str,
            geometry=geometry,
            color=get_color(len(entries)),
            name=name,
            group=current_group,
            group_index=group_index,
        )
        entries.append(entry)
        prev_line = line
    return entries
