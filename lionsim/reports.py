"""Collar reports, traffic context, and strictly future next-zone targets."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from .config import Config
from .events import ZONE_TOKENS, serializable_events, sort_events
from .zones import ZoneMap

if TYPE_CHECKING:
    from .simulator import DayResult


END_OF_DAY = "END_OF_DAY"
TARGET_CLASSES = (*ZONE_TOKENS.values(), END_OF_DAY)


def report_offsets_minutes(config: Config) -> list[int]:
    """Convert ordered report clock times into offsets from the day start.

    A report at the start clock time belongs to the next morning, so its offset
    is 1440 rather than zero.
    """
    hour, minute = map(int, config["time"]["day_start"].split(":"))
    start_clock = hour * 60 + minute
    duration = config["time"]["day_minutes"]
    offsets = []
    for clock in config["time"]["report_times"]:
        hour, minute = map(int, clock.split(":"))
        offset = (hour * 60 + minute - start_clock) % duration
        offsets.append(offset or duration)
    return offsets


def build_reports(day: DayResult, config: Config) -> list[dict[str, Any]]:
    """Build report prefixes without exposing any future context as input.

    The first batch includes events at the day start. Subsequent batches use
    (previous report, current report], including events exactly at the current
    report once. ``path_up_to_index`` includes the exact report-boundary fix;
    optional cumulative paths contain observed fixes only. Target labels inspect
    later entries in the same day and are excluded from the final report.
    """
    start = datetime.fromisoformat(f"{day.date}T{config['time']['day_start']}:00")
    end = start + timedelta(minutes=config["time"]["day_minutes"])
    zone_map = ZoneMap(config)
    public_events = serializable_events(day.events)
    event_times = [datetime.fromisoformat(event["t"]) for event in public_events]
    entries = [event for event in public_events if event["token"] in ZONE_TOKENS.values()
               and start <= datetime.fromisoformat(event["t"]) < end]
    entry_times = [datetime.fromisoformat(event["t"]) for event in entries]
    traffic_times = sorted(datetime.fromisoformat(t) for t in getattr(day, "traffic_times", [])
                           if start <= datetime.fromisoformat(t) < end)
    event_begin = bisect_left(event_times, start)
    traffic_begin = bisect_left(traffic_times, start)
    embed = config["output"].get("embed_cumulative_path_in_reports", False)
    path = [[str(t), float(x), float(y)] for t, x, y in
            day.gps[["t_iso", "x_km", "y_km"]].itertuples(index=False, name=None)] if embed else []
    reports: list[dict[str, Any]] = []
    for report_index, offset in enumerate(report_offsets_minutes(config), start=1):
        report_time = start + timedelta(minutes=offset)
        event_end = bisect_right(event_times, report_time)
        traffic_end = bisect_right(traffic_times, report_time)
        last = day.gps.iloc[offset]
        report: dict[str, Any] = {
            "report_index": report_index,
            "report_time": report_time.isoformat(timespec="seconds"),
            "new_events": public_events[event_begin:event_end],
            "path_up_to_index": int(last["minute_index"]),
            "current_zone": zone_map.lookup(float(last["x_true_km"]), float(last["y_true_km"])),
            "traffic_count_since_last_report": traffic_end - traffic_begin,
            "traffic_count_last_hour": traffic_end - bisect_right(traffic_times, report_time - timedelta(hours=1)),
        }
        if embed:
            report["path"] = path[:offset + 1]
        if report_time < end:
            next_index = bisect_right(entry_times, report_time)
            report["next_zone_target"] = entries[next_index]["token"] if next_index < len(entries) else END_OF_DAY
            report["time_to_next_zone_min"] = ((entry_times[next_index] - report_time).total_seconds() / 60
                                                if next_index < len(entries) else None)
        reports.append(report)
        event_begin = event_end
        traffic_begin = traffic_end
    return reports


def target_rows(day: DayResult, reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the seven usable supervised targets with only report-time inputs."""
    events = sort_events(day.events)
    times = [datetime.fromisoformat(event["t"]) for event in events]
    rows = []
    for report in reports:
        if "next_zone_target" not in report:
            continue
        timestamp = datetime.fromisoformat(report["report_time"])
        last = bisect_right(times, timestamp) - 1
        rows.append({
            "day": int(day.day_index), "report_index": int(report["report_index"]),
            "report_time_bucket": timestamp.strftime("%H:%M"),
            "current_zone": report["current_zone"],
            "last_event": events[last]["token"] if last >= 0 else None,
            "next_zone_target": report["next_zone_target"],
        })
    return rows
