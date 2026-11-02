"""Controlled scenarios exercise causal behaviour, independent of rare seeds."""

from __future__ import annotations

from datetime import datetime

import pytest

from lionsim.config import Config, load_config
from lionsim.events import ZONE_TOKENS
from lionsim.simulator import DayResult, simulate_day
from lionsim.validate import validate_day


def _hunting_config(*extra: str) -> Config:
    """Arrange a lion already visiting Hunt when its evening window opens.

    Strong configurable priors remove destination ambiguity. A high encounter
    rate exercises chases without asserting a particular random event count.
    Noise-free hunger isolates the eligibility threshold from noisy bar drift.
    """
    overrides = [
        "randomness.latent_ranges.start_hunger=[1.0,1.0]",
        "randomness.latent_ranges.hunt_threshold=[0.3,0.3]",
        "randomness.latent_ranges.prey_density=[1.0,1.0]",
        "randomness.bar_noise_sd=0",
        "randomness.score_noise_sd=0",
        "bars.hunger_rest_per_hour=0",
        "bars.hunger_active_per_hour=0",
        "behaviours.groom_mean_minutes=1",
        "behaviours.groom_lognormal_sigma=0",
        "behaviours.rest_minutes_range=[1,1]",
        "behaviours.visit_minutes_range=[1,1]",
        "behaviours.fail_rest_minutes_range=[10,10]",
        "behaviours.prey_encounters_per_hour=600",
    ]
    for index in range(len(load_config()["goal"]["periods"])):
        for name in ZONE_TOKENS:
            value = 100 if name == "Hunting ground" else -100
            overrides.append(f"goal.periods.{index}.priors.{name}={value}")
    return load_config(overrides=overrides + list(extra))


def _simulate(config: Config) -> DayResult:
    day = simulate_day(config, seed=314159)
    validation = validate_day(day, config)
    assert validation["valid"], validation["errors"]
    return day


def _event_time(event: dict) -> datetime:
    return datetime.fromisoformat(event["t"])


def _minute(day: DayResult, event: dict) -> int:
    start = datetime.fromisoformat(day.gps.iloc[0]["t_iso"])
    return int((_event_time(event) - start).total_seconds() // 60)


def test_catch_routes_to_feeding_then_terminal_sleep():
    config = _hunting_config(
        "chase.probability_clip=[1.0,1.0]",
        "tourists.end=23:00",
    )
    day = _simulate(config)
    meaningful = [event for event in day.events if event["token"] != "CAR_PASSED"]
    tokens = [event["token"] for event in meaningful]
    catch_index = tokens.index("CATCH")
    assert tokens[catch_index - 1] == "CHASE_START"
    feed_index = tokens.index("ENTER_FEED", catch_index)
    eat_index = tokens.index("EAT_START", feed_index)
    end_index = tokens.index("EAT_END", eat_index)
    assert meaningful[eat_index]["zone"] == "Feeding spot"
    assert tokens[end_index:] == ["EAT_END", "FELL_ASLEEP"]
    sleep = meaningful[end_index + 1]
    assert sleep["zone"] == "Feeding spot"
    after_sleep = day.hidden_state.iloc[_minute(day, sleep) + 1:]
    assert not after_sleep.empty
    assert (after_sleep["behaviour"] == "sleeping").all()
    assert (after_sleep["zone"] == "Feeding spot").all()
    assert (day.hidden_state.loc[day.hidden_state["behaviour"] == "eating", "zone"] == "Feeding spot").all()


@pytest.fixture(scope="module")
def failed_hunts() -> tuple[Config, DayResult]:
    config = _hunting_config("chase.probability_clip=[0.0,0.0]")
    return config, _simulate(config)


def test_failed_chases_rest_for_full_duration_then_resume(failed_hunts):
    config, day = failed_hunts
    starts = [event for event in day.events if event["token"] == "CHASE_START"]
    failures = [event for event in day.events if event["token"] == "FAIL"]
    assert len(failures) >= 2
    assert len(failures) == len(starts)
    assert not any(event["token"] in ("CATCH", "EAT_START", "EAT_END") for event in day.events)
    rest_minutes = config["learnability"]["activity"]["fail_rest_minutes_range"][0]
    for failure, next_start in zip(failures[:-1], starts[1:]):
        first_rest_row = _minute(day, failure) + 1
        recovery = day.hidden_state.iloc[first_rest_row:first_rest_row + rest_minutes]
        assert len(recovery) == rest_minutes
        assert (recovery["behaviour"] == "resting").all()
        assert (_event_time(next_start) - _event_time(failure)).total_seconds() >= rest_minutes * 60
        assert day.hidden_state.iloc[_minute(day, next_start)]["behaviour"] == "hunting"


def test_hunger_below_threshold_prevents_stalking_even_in_hunting_ground():
    config = _hunting_config(
        "randomness.latent_ranges.start_hunger=[0.1,0.1]",
        "randomness.latent_ranges.hunt_threshold=[0.5,0.5]",
    )
    day = _simulate(config)
    assert not (day.hidden_state["zone"] == "Hunting ground").any()
    assert (day.hidden_state["hunger"] == 0.1).all()
    assert not (day.hidden_state["behaviour"] == "hunting").any()
    assert not any(event["token"] in ("CHASE_START", "CATCH", "FAIL") for event in day.events)


def test_hunting_stops_at_22_even_when_hunger_and_prey_remain_high(failed_hunts):
    _, day = failed_hunts
    cutoff = datetime.fromisoformat(f"{day.date}T22:00:00")
    starts = [event for event in day.events if event["token"] == "CHASE_START"]
    assert starts
    assert all(_event_time(event) < cutoff for event in starts)
    assert all(_event_time(event) < cutoff for event in day.events if event["token"] == "ENTER_HUNT")
    night = day.hidden_state[day.hidden_state["t_iso"] >= cutoff.isoformat(timespec="seconds")]
    assert len(night) == 7 * 60
    assert not (night["behaviour"] == "hunting").any()
    assert (night["hunger"] > day.latents["hunt_threshold"]).all()


def test_committed_trip_survives_destination_redraws_until_a_logged_interrupt():
    import numpy as np
    from lionsim.simulator import _DaySimulation
    config = load_config(overrides=['randomness.bar_noise_sd=0'])
    sim = _DaySimulation(config, 1, 42, '2026-01-01', np.random.SeedSequence(42))
    sim.minute = sim.offset('08:00')
    sim.position = np.array([6.0, 6.0])
    sim.raw_zone = None
    sim.mode, sim.goal = 'walking', 'Kopje'
    sim.bars[:] = [.5, .8, .5, .8, .5]
    for _ in range(10):
        sim._transitions()
        assert sim.goal == 'Kopje' and sim.mode == 'walking'
        assert sim.abandoned_goal_this_minute is None
        sim.minute += 1
    sim.bars[2] = 1
    sim._transitions()
    assert sim.goal == 'Shade'
    assert sim.abandoned_goal_this_minute == 'Kopje'
    assert sim.abandoned_reason_this_minute == 'temperature'


def test_full_day_trip_changes_have_reasons_and_validator_rejects_missing_reason():
    from copy import deepcopy
    config = load_config(overrides=["road_response.enabled=false"])
    candidates = []
    for index in range(1, 11):
        day = simulate_day(config, day_index=index, seed=42)
        hidden = day.hidden_state
        previous = hidden.shift(1)
        abandoned = ((previous['movement_intent'] == 'travel')
                     & (previous['goal'] != hidden['zone'])
                     & (previous['goal'] != hidden['goal']))
        assert hidden.loc[abandoned, 'abandoned_trip_reason'].notna().all()
        assert (hidden.loc[abandoned, 'abandoned_goal'] == previous.loc[abandoned, 'goal']).all()
        if abandoned.any():
            candidates.append((day, hidden.index[abandoned][0]))
    assert candidates
    day, abandoned_index = candidates[0]
    broken = deepcopy(day)
    broken.hidden_state.loc[abandoned_index, 'abandoned_trip_reason'] = None
    validation = validate_day(broken, config)
    assert not validation['valid']
    assert any('no logged reason' in error for error in validation['errors'])


@pytest.mark.parametrize('cycles', [1, 2, 3])
def test_night_catnaps_enforce_minimum_real_duration_and_maximum_cycles(cycles):
    config = _hunting_config('chase.probability_clip=[0,0]',
                             'learnability.activity.catnap_minutes_range=[1,1]',
                             f'learnability.behaviour.night_nap_max_cycles={cycles}')
    day = _simulate(config)
    night_start = datetime.fromisoformat(f'{day.date}T22:00:00')
    end = datetime.fromisoformat(day.gps.iloc[-1]['t_iso'])
    sleeps = [e for e in day.events if e['token'] == 'FELL_ASLEEP' and _event_time(e) >= night_start]
    wakes = [e for e in day.events if e['token'] == 'WOKE_UP' and _event_time(e) >= night_start]
    assert 1 <= len(sleeps) <= cycles
    assert len(wakes) <= len(sleeps)
    minimum = config['learnability']['behaviour']['night_nap_min_minutes']
    for sleep in sleeps:
        wake_time = next((_event_time(w) for w in wakes if _event_time(w) > _event_time(sleep)), end)
        assert (wake_time - _event_time(sleep)).total_seconds() >= minimum * 60
        start_minute = _minute(day, sleep)
        assert (day.hidden_state.iloc[start_minute:start_minute + minimum]['behaviour'] == 'sleeping').all()


def test_no_short_terminal_nap_when_only_minimum_ticks_remain():
    import numpy as np
    from lionsim.simulator import _DaySimulation
    config = load_config()
    sim = _DaySimulation(config, 1, 42, '2026-01-01', np.random.SeedSequence(42))
    sim.minute = sim.day_minutes - config['learnability']['behaviour']['night_nap_min_minutes']
    sim.mode, sim.goal, sim.until = 'night_walk', 'Plain', sim.minute
    sim._transitions()
    assert sim.mode == 'night_rest'
    assert not any(e['token'] == 'FELL_ASLEEP' for e in sim.events)


def test_night_patrols_add_late_entries_without_breaking_catch_sleep_or_cutoff():
    late_non_feast = non_feast = 0
    for index in range(1, 41):
        day = simulate_day(load_config(), day_index=index, seed=42)
        assert validate_day(day, load_config())['valid']
        entries = [e for e in day.events if e['token'].startswith('ENTER_')]
        cutoff = datetime.fromisoformat(f'{day.date}T22:00:00')
        late = datetime.fromisoformat(f'{day.date}T23:00:00')
        assert not any(e['token'] in ('ENTER_HUNT','CHASE_START') and _event_time(e) >= cutoff for e in day.events)
        ends = [e for e in day.events if e['token']=='EAT_END']
        if ends:
            assert not any(_event_time(e) > _event_time(ends[0]) for e in entries)
        else:
            non_feast += 1
            late_non_feast += any(_event_time(e) > late for e in entries)
        sleeps = [e for e in day.events if e['token']=='FELL_ASLEEP' and _event_time(e) >= cutoff]
        assert len(sleeps) <= 4
    assert non_feast > 10
    assert late_non_feast / non_feast > .5


def test_water_trip_is_not_diverted_from_one_cooling_destination_to_another():
    import numpy as np
    from lionsim.simulator import _DaySimulation
    sim = _DaySimulation(load_config(), 1, 42, '2026-01-01', np.random.SeedSequence(42))
    sim.minute = sim.offset('16:30')
    sim.midday_slept = True
    sim.position = np.array([6., 6.])
    sim.raw_zone = None
    sim.mode, sim.goal = 'walking', 'Waterhole'
    sim.bars[:] = [.5, .8, 1., .8, .5]
    sim._scheduled_interrupts()
    assert sim.goal == 'Waterhole'
    assert sim.abandoned_reason_this_minute is None
