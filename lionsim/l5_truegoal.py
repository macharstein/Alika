"""LEAKY analysis-only hidden current-goal alignment. Never export model inputs."""
import pandas as pd


def true_goal_at_report(hidden, report_time, zone_names):
    times = pd.to_datetime(hidden['t_iso'])
    if times.duplicated().any() or not times.is_monotonic_increasing:
        raise ValueError('Hidden timestamps must be unique and ordered')
    rows = hidden.loc[times == pd.Timestamp(report_time), 'goal']
    if len(rows) != 1:
        raise ValueError('Missing exact hidden current-goal timestamp')
    goal = rows.iloc[0]
    if goal not in zone_names:
        raise ValueError(f'Unknown hidden current goal: {goal}')
    return str(goal)
