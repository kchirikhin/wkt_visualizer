from gi.repository import GObject
from shapely.geometry.base import BaseGeometry


class WktEntry(GObject.Object):
    __gtype_name__ = "WktEntry"

    name = GObject.Property(type=str, default="")
    color_r = GObject.Property(type=float, default=0.0)
    color_g = GObject.Property(type=float, default=0.0)
    color_b = GObject.Property(type=float, default=0.0)
    line_width = GObject.Property(type=float, default=2.0)
    fill_opacity = GObject.Property(type=float, default=0.3)

    def __init__(
        self,
        entry_id: int,
        raw_line: str,
        wkt: str,
        geometry: BaseGeometry,
        color: tuple[float, float, float],
        name: str = "",
        group: str = "",
        group_index: int = 0,
    ):
        super().__init__()
        self.entry_id = entry_id
        self.raw_line = raw_line
        self.wkt = wkt
        self.geometry = geometry
        self.color_r = color[0]
        self.color_g = color[1]
        self.color_b = color[2]
        self.name = name if name else f"{geometry.geom_type} {entry_id + 1}"
        self.group = group
        self.group_index = group_index

    @property
    def color(self) -> tuple[float, float, float]:
        return (self.color_r, self.color_g, self.color_b)

    @color.setter
    def color(self, value: tuple[float, float, float]):
        self.color_r, self.color_g, self.color_b = value
