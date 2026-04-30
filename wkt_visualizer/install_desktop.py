import argparse
import os
import shutil
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

APP_ID = "com.github.wkt_visualizer"
ICON_REL = [
    ("hicolor/scalable/apps", f"{APP_ID}.svg"),
    ("hicolor/symbolic/apps", f"{APP_ID}-symbolic.svg"),
]


def _xdg_data_home() -> Path:
    env = os.environ.get("XDG_DATA_HOME")
    return Path(env) if env else Path.home() / ".local" / "share"


def _desktop_path() -> Path:
    return _xdg_data_home() / "applications" / f"{APP_ID}.desktop"


def _icon_target(subdir: str, name: str) -> Path:
    return _xdg_data_home() / "icons" / subdir / name


def _render_desktop() -> str:
    tpl = files("wkt_visualizer.templates").joinpath(f"{APP_ID}.desktop").read_text()
    return tpl.format(python=sys.executable)


def _refresh_desktop_db(app_dir: Path) -> None:
    if shutil.which("update-desktop-database"):
        subprocess.run(["update-desktop-database", str(app_dir)], check=False)


def install() -> list[Path]:
    written: list[Path] = []
    desktop = _desktop_path()
    desktop.parent.mkdir(parents=True, exist_ok=True)
    desktop.write_text(_render_desktop())
    written.append(desktop)

    icons_root = files("wkt_visualizer").joinpath("icons")
    for subdir, name in ICON_REL:
        src = icons_root.joinpath(subdir).joinpath(name)
        dst = _icon_target(subdir, name)
        dst.parent.mkdir(parents=True, exist_ok=True)
        with src.open("rb") as r, open(dst, "wb") as w:
            shutil.copyfileobj(r, w)
        written.append(dst)

    _refresh_desktop_db(desktop.parent)
    return written


def uninstall() -> list[Path]:
    removed: list[Path] = []
    targets = [_desktop_path(), *(_icon_target(s, n) for s, n in ICON_REL)]
    for p in targets:
        if p.exists():
            p.unlink()
            removed.append(p)
    _refresh_desktop_db(_desktop_path().parent)
    return removed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="wkt-visualizer-install-desktop",
        description="Install or remove the WKT Visualizer GNOME launcher entry.",
    )
    ap.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove the .desktop file and icons instead of installing.",
    )
    args = ap.parse_args(argv)

    paths = uninstall() if args.uninstall else install()
    verb = "Removed" if args.uninstall else "Installed"

    if not paths:
        print(f"{verb} nothing.")
        return 0

    print(f"{verb}:")
    for p in paths:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
