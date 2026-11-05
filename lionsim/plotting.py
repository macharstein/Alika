"""Text-free, fixed-scale GPS path images and daily contact sheets."""

from __future__ import annotations

import math
from io import BytesIO
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

# A writable cache avoids worker import warnings on locked-down machines.
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "lionsim-matplotlib"))

import numpy as np
from matplotlib import image as mpl_image
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle

from .config import Config
from .io_utils import atomic_output


def report_filename(report_time: str, day_index: int, report_index: int) -> str:
    timestamp = datetime.fromisoformat(report_time)
    return f"{timestamp:%Y-%m-%d_%H%M}_day{day_index:04d}_report{report_index}.png"


def contact_sheet_filename(date: str, day_index: int) -> str:
    return f"{date}_day{day_index:04d}_contact_sheet.png"


def render_reports(day: Any, reports: list[dict[str, Any]], config: Config,
                   directory: str | Path | None) -> list[Path] | list[bytes]:
    """Draw filled zones, the observed GPS prefix, and a small endpoint dot.

    Every report uses the same map extent and scale. Events, hidden state,
    true coordinates, and future fixes never contribute to its image. Dates
    and report times appear only in filenames; the PNGs contain no text.
    """
    # None selects in-memory reports only (no files or contact sheet).
    if directory is not None:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
    if not reports:
        return []
    opts, geometry = config["images"], config["map"]
    size = opts["size_px"]
    figure = Figure(figsize=(size / opts["dpi"], size / opts["dpi"]),
                    dpi=opts["dpi"], facecolor=opts["background_color"])
    FigureCanvasAgg(figure)
    axis = figure.add_axes([0, 0, 1, 1], facecolor=opts["background_color"])
    axis.set_xlim(0, geometry["width_km"])
    axis.set_ylim(0, geometry["height_km"])
    axis.set_aspect("equal", adjustable="box")
    axis.set_xticks([])
    axis.set_yticks([])
    axis.set_axis_off()
    for name, zone in geometry["zones"].items():
        if name.startswith("_"):
            continue
        style = dict(facecolor=zone["color"], alpha=opts["zone_alpha"],
                     edgecolor="none", zorder=1)
        if zone["shape"] == "circle":
            axis.add_patch(Circle(zone["center"], zone["radius"], **style))
        else:
            x0, x1 = zone["x"]
            y0, y1 = zone["y"]
            axis.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, **style))
    path_line, = axis.plot([], [], color=opts["path_color"],
                          linewidth=opts["path_linewidth"], zorder=2)
    current = axis.scatter([], [], s=opts["current_point_size"],
                           c=opts["path_color"], edgecolors="none", zorder=3)
    x = day.gps["x_km"].to_numpy()
    y = day.gps["y_km"].to_numpy()
    paths: list[Path] = []
    frames: list[bytes] = []
    for report in reports:
        last = report["path_up_to_index"]
        path_line.set_data(x[:last + 1], y[:last + 1])
        current.set_offsets([[x[last], y[last]]])
        if directory is None:
            with BytesIO() as buffer:
                figure.savefig(buffer, format="png", dpi=opts["dpi"],
                               facecolor=opts["background_color"], transparent=False)
                frames.append(buffer.getvalue())
            continue
        destination = directory / report_filename(report["report_time"], day.day_index,
                                                   report["report_index"])
        with atomic_output(destination) as temporary:
            figure.savefig(temporary, dpi=opts["dpi"], facecolor=opts["background_color"], transparent=False)
        paths.append(destination)
    figure.clear()
    if directory is None:
        return frames

    columns = opts["contact_sheet_columns"]
    rows = max(opts["contact_sheet_rows"], math.ceil(len(paths) / columns))
    rgba = np.rint(np.asarray(to_rgba(opts["background_color"])) * 255).astype(np.uint8)
    sheet = np.empty((rows * size, columns * size, 4), dtype=np.uint8)
    sheet[:] = rgba
    for index, path in enumerate(paths):
        decoded = mpl_image.imread(path)
        if decoded.dtype.kind == "f":
            decoded = np.rint(decoded * 255).astype(np.uint8)
        row, column = divmod(index, columns)
        sheet[row * size:(row + 1) * size, column * size:(column + 1) * size] = decoded
    destination = directory / contact_sheet_filename(day.date, day.day_index)
    with atomic_output(destination) as temporary:
        mpl_image.imsave(temporary, sheet)
    paths.append(destination)
    return paths
