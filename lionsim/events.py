"""The collar's public event vocabulary and small JSON-safe log helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Iterable


ZONE_TOKENS: dict[str, str] = {
    "Den": "ENTER_DEN",
    "Shade": "ENTER_SHADE",
    "Kopje": "ENTER_KOPJE",
    "Waterhole": "ENTER_WATER",
    "Hunting ground": "ENTER_HUNT",
    "Feeding spot": "ENTER_FEED",
    "Plain": "ENTER_PLAIN",
    "Road": "ENTER_ROAD",
}

TOKENS: tuple[str, ...] = (
    "ENTER_DEN", "ENTER_SHADE", "ENTER_KOPJE", "ENTER_WATER",
    "ENTER_HUNT", "ENTER_FEED", "ENTER_PLAIN", "ENTER_ROAD",
    "WOKE_UP", "FELL_ASLEEP", "GROOM", "DRINK", "CHASE_START", "CATCH",
    "FAIL", "EAT_START", "EAT_END",
)


_DESCRIPTIONS: dict[str, str] = {
    "ENTER_DEN": "The lion entered the den.",
    "ENTER_SHADE": "The lion entered the shaded area.",
    "ENTER_KOPJE": "The lion entered the kopje (rocky outcrop).",
    "ENTER_WATER": "The lion reached the waterhole.",
    "ENTER_HUNT": "The lion entered the hunting ground.",
    "ENTER_FEED": "The lion entered the feeding spot.",
    "ENTER_PLAIN": "The lion entered the open plain.",
    "ENTER_ROAD": "The lion entered the road corridor.",
    "WOKE_UP": "The lion woke up.",
    "FELL_ASLEEP": "The lion fell asleep.",
    "GROOM": "The lion started grooming.",
    "DRINK": "The lion started drinking water.",
    "CHASE_START": "The lion started chasing prey.",
    "CATCH": "The lion caught its prey.",
    "FAIL": "The chase ended without a catch.",
    "EAT_START": "The lion started eating.",
    "EAT_END": "The lion finished eating.",
}


def describe_event(event: dict[str, Any]) -> str:
    """Explain one of the seventeen public collar events."""
    token = event["token"]
    if token not in _DESCRIPTIONS:
        raise ValueError(f"Unknown collar event token: {token}")
    return _DESCRIPTIONS[token]


def serializable_events(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Produce one chronological, readable record per event for day.json.

    Stable IDs are reused in the daily log and report event batches. The current
    true-position zone is public context; hidden bars and traffic are not events.
    """
    return [
        {
            "id": f"E{index:03d}",
            "t": event["t"],
            "token": event["token"],
            "description": describe_event(event),
            "zone": event.get("zone"),
        }
        for index, event in enumerate(sort_events(events), start=1)
    ]


def make_event(t: datetime, token: str, zone: str | None) -> dict[str, Any]:
    """Return a serializable collar event, rejecting accidental new tokens."""
    if token not in TOKENS:
        raise ValueError(f"Unknown collar event token: {token}")
    if zone is not None and zone not in ZONE_TOKENS:
        raise ValueError(f"Unknown event zone: {zone}")
    return {"t": t.isoformat(timespec="seconds"), "token": token, "zone": zone}


def append_event(
    events: list[dict[str, Any]],
    day_start: datetime,
    elapsed_seconds: int,
    token: str,
    zone: str | None,
) -> None:
    """Append one event; sort once after simulating the full day."""
    events.append(make_event(day_start + timedelta(seconds=int(elapsed_seconds)), token, zone))


def sort_events(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stable ordering preserves causal order for events sharing a second."""
    return sorted(events, key=lambda event: event["t"])
