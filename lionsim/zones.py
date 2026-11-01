"""Map geometry and confirmed zone-entry tracking, independent of GPS noise."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping


ZONE_NAMES: tuple[str, ...] = (
    "Den", "Shade", "Kopje", "Waterhole", "Plain", "Hunting ground",
    "Feeding spot", "Road",
)


def _number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path} must be a finite number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{path} must be a finite number")
    return value


def _pair(value: Any, path: str) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{path} must contain exactly two numbers")
    return _number(value[0], f"{path}[0]"), _number(value[1], f"{path}[1]")


class ZoneMap:
    """Validate the configured map and perform exact circle/rectangle lookups.

    All zone boundaries are inclusive. Touching zones are rejected because a
    boundary point would otherwise belong to both. Distances are to the nearest
    point in a zone (zero inside), not to its centre.
    """

    def __init__(self, config: Any) -> None:
        data = config.data if hasattr(config, "data") else config
        if not isinstance(data, Mapping):
            raise ValueError("ZoneMap expects Config or a configuration mapping")
        map_data = data.get("map", data)
        self.width = _number(map_data["width_km"], "map.width_km")
        self.height = _number(map_data["height_km"], "map.height_km")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Map width and height must be positive")
        self.zones: dict[str, dict[str, Any]] = map_data["zones"]
        actual = {key for key in self.zones if not key.startswith("_")}
        if actual != set(ZONE_NAMES):
            raise ValueError(
                "map.zones must contain exactly the eight token-bearing zones; "
                f"missing={sorted(set(ZONE_NAMES) - actual)}, "
                f"unknown={sorted(actual - set(ZONE_NAMES))}"
            )
        self.names = tuple(name for name in self.zones if not name.startswith("_"))
        self._validate()

    def _validate(self) -> None:
        for name in self.names:
            zone = self.zones[name]
            path = f"map.zones.{name}"
            if not isinstance(zone, Mapping):
                raise ValueError(f"{path} must be an object")
            shape = zone.get("shape")
            if shape == "circle":
                x, y = _pair(zone.get("center"), f"{path}.center")
                radius = _number(zone.get("radius"), f"{path}.radius")
                if radius <= 0:
                    raise ValueError(f"{path}.radius must be positive")
                limits = (x - radius, x + radius, y - radius, y + radius)
            elif shape == "rectangle":
                xmin, xmax = _pair(zone.get("x"), f"{path}.x")
                ymin, ymax = _pair(zone.get("y"), f"{path}.y")
                if xmin >= xmax or ymin >= ymax:
                    raise ValueError(f"{path} rectangle limits must increase strictly")
                limits = (xmin, xmax, ymin, ymax)
            else:
                raise ValueError(f"{path}.shape must be 'circle' or 'rectangle'")
            if (limits[0] < 0 or limits[1] > self.width or limits[2] < 0
                    or limits[3] > self.height):
                raise ValueError(f"{path} extends outside the configured map")
        for index, left in enumerate(self.names):
            for right in self.names[index + 1:]:
                if self._overlaps(self.zones[left], self.zones[right]):
                    raise ValueError(
                        f"Map zones overlap or touch: {left!r} and {right!r}"
                    )

    @staticmethod
    def _overlaps(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
        if a["shape"] == "circle" and b["shape"] == "circle":
            return math.dist(a["center"], b["center"]) <= a["radius"] + b["radius"]
        if a["shape"] == "rectangle" and b["shape"] == "rectangle":
            return (max(a["x"][0], b["x"][0]) <= min(a["x"][1], b["x"][1])
                    and max(a["y"][0], b["y"][0]) <= min(a["y"][1], b["y"][1]))
        circle, rect = (a, b) if a["shape"] == "circle" else (b, a)
        cx, cy = circle["center"]
        nearest_x = max(rect["x"][0], min(cx, rect["x"][1]))
        nearest_y = max(rect["y"][0], min(cy, rect["y"][1]))
        return math.hypot(cx - nearest_x, cy - nearest_y) <= circle["radius"]

    def center(self, name: str) -> tuple[float, float]:
        """Return a circle centre or rectangle midpoint."""
        zone = self.zones[name]
        if zone["shape"] == "circle":
            return float(zone["center"][0]), float(zone["center"][1])
        return (sum(zone["x"]) / 2.0, sum(zone["y"]) / 2.0)

    def contains(self, name: str, x: float, y: float) -> bool:
        """Check whether a finite true position is inside a named zone."""
        if not math.isfinite(x) or not math.isfinite(y):
            return False
        zone = self.zones[name]
        if zone["shape"] == "circle":
            cx, cy = zone["center"]
            return math.hypot(x - cx, y - cy) <= zone["radius"]
        return zone["x"][0] <= x <= zone["x"][1] and zone["y"][0] <= y <= zone["y"][1]

    def lookup(self, x: float, y: float) -> str | None:
        """Return the containing zone, or None for unzoned/outside space."""
        for name in self.names:
            if self.contains(name, x, y):
                return name
        return None

    def distance_to(self, name: str, x: float, y: float) -> float:
        """Shortest distance in km from a position to a zone's boundary/interior."""
        zone = self.zones[name]
        if zone["shape"] == "circle":
            return max(0.0, math.dist((x, y), zone["center"]) - zone["radius"])
        dx = max(zone["x"][0] - x, 0.0, x - zone["x"][1])
        dy = max(zone["y"][0] - y, 0.0, y - zone["y"][1])
        return math.hypot(dx, dy)


@dataclass
class HysteresisTracker:
    """Emit a new named entry after consecutive one-minute samples.

    The last confirmed named zone persists across unzoned gaps. Re-entering that
    same zone therefore emits nothing until another named zone was confirmed.
    This convention prevents identical consecutive ENTER tokens.
    """

    required_minutes: int = 2
    initial_zone: str | None = "Den"

    def __post_init__(self) -> None:
        if (isinstance(self.required_minutes, bool)
                or not isinstance(self.required_minutes, int)
                or self.required_minutes < 1):
            raise ValueError("required_minutes must be a positive integer")
        self.considered_zone = self.initial_zone
        self.candidate_zone: str | None = None
        self.candidate_minutes = 0

    @property
    def current_zone(self) -> str | None:
        """Last confirmed named zone (possibly different from raw lookup)."""
        return self.considered_zone

    def update(self, zone: str | None) -> str | None:
        """Consume one minute's zone and return only a newly confirmed entry."""
        if zone is None or zone == self.considered_zone:
            self.candidate_zone = None
            self.candidate_minutes = 0
            return None
        if zone == self.candidate_zone:
            self.candidate_minutes += 1
        else:
            self.candidate_zone, self.candidate_minutes = zone, 1
        if self.candidate_minutes < self.required_minutes:
            return None
        self.considered_zone = zone
        self.candidate_zone, self.candidate_minutes = None, 0
        return zone
