"""Causal road excursions, protected activities, and state-dependent motion."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lionsim.config import load_config
from lionsim.simulator import _DaySimulation, simulate_day
from lionsim.validate import validate_day


def controlled_simulation(*overrides):
    config = load_config(overrides=[
        "road_response.approach_probability=1",
        "behaviour.goal_commitment=false",
        "behaviour.road_entry_traffic_decay=0",
        "behaviour.road_entry_probability=0",
        "road_response.avoidance_probability=0",
        "road_response.reaction_delay_minutes_range=[2,2]",
        "road_response.watch_minutes_range=[4,4]",
        "movement.patrol_speed_noise_sd=0",
        "randomness.walk_heading_sd_degrees=0",
        *overrides,
    ])
    sim = _DaySimulation(config, 1, 42, "2026-01-01", np.random.SeedSequence(42))
    sim.minute = 660  # 16:00; use a point outside all zones, west of the road.
    sim.position = np.array([7.9, 5.0])
    sim.heading = -np.pi / 2  # A response has to turn, not just continue east.
    sim.raw_zone = None
    sim.mode, sim.goal, sim.until = "walking", "Plain", 700
    sim.bars[:] = [0.5, 0.8, 0.4, 0.9, 0.8]
    return sim


def test_car_causes_delayed_approach_watch_and_return_without_road_entry():
    sim = controlled_simulation()
    trigger_second = sim.minute * 60 + 45
    initial = sim.position.copy()
    original_heading = sim.heading
    sim._consider_car_response(trigger_second)
    assert sim.mode == "walking"
    np.testing.assert_array_equal(sim.position, initial)
    sim.minute += 1
    assert not sim._advance_road_response()
    assert sim.mode == "walking"
    sim.minute += 1
    assert sim._advance_road_response()
    assert sim.mode == "road_approach"
    assert sim.road_trigger_second == trigger_second
    # Nearest boundary and standoff: no trip to the road's centre is needed.
    np.testing.assert_allclose(sim.road_target, [8.62, 5.0])
    assert sim._activity() == "walking"
    approach_distances = []
    watch_started = None
    for _ in range(100):
        old = sim.position.copy()
        if sim.mode in ("road_approach", "road_retreat"):
            sim._move_road_response()
            approach_distances.append(sim._road_distance())
        elif sim.mode == "road_watch":
            assert sim._activity() == "resting"
            if watch_started is None:
                watch_started = sim.minute
        assert np.linalg.norm(sim.position - old) <= sim.movement["patrol_speed_kmh_range"][1] / 60 + 1e-12
        assert not sim._contains("Road", sim.position)
        sim.minute += 1
        if not sim._advance_road_response():
            break
    assert watch_started is not None
    assert sim.minute - watch_started == 4
    assert min(approach_distances) < 0.23
    assert sim.heading != original_heading
    assert sim.mode == "walking" and sim.goal == "Plain"
    assert sim.road_trigger_second is None
    assert not sim.events  # Preserve the original 18-token collar vocabulary.
    sim._consider_car_response(sim.minute * 60)
    assert sim.road_pending is None  # Recovery/cooldown prevents endless detours.


@pytest.mark.parametrize("mode", [
    "initial_sleep", "midday_sleep", "catnap", "final_sleep", "grooming",
    "drinking", "hunting", "fail_rest", "eating", "night_walk",
])
def test_car_does_not_interrupt_protected_activities(mode):
    sim = controlled_simulation()
    sim.mode = mode
    sim._consider_car_response(sim.minute * 60 + 10)
    assert sim.road_pending is None
    assert sim.mode == mode


@pytest.mark.parametrize("override", [
    "road_response.enabled=false",
    "road_response.minimum_boredom=1",
    "road_response.minimum_energy=1",
    "road_response.minimum_mood=1",
    "road_response.detection_distance_km=0.1",
    "road_response.approach_probability=0",
])
def test_approach_depends_on_perception_and_current_state(override):
    sim = controlled_simulation(override)
    sim._consider_car_response(sim.minute * 60 + 10)
    assert sim.road_pending is None


def test_pending_response_is_cancelled_if_a_protected_activity_started():
    sim = controlled_simulation()
    sim._consider_car_response(sim.minute * 60 + 10)
    sim.mode = "drinking"
    sim.minute += 2
    assert not sim._advance_road_response()
    assert sim.mode == "drinking" and sim.road_pending is None


def test_catch_prevents_diversion_on_the_way_to_feeding():
    sim = controlled_simulation()
    sim.caught = True
    sim.goal = "Feeding spot"
    sim._consider_car_response(sim.minute * 60 + 10)
    assert sim.road_pending is None


def test_low_mood_car_retreat_increases_distance_then_resumes_goal():
    sim = controlled_simulation("road_response.avoidance_probability=1")
    sim.bars[4] = 0.1
    sim.heading = np.pi
    distance_before = sim._road_distance()
    sim._consider_car_response(sim.minute * 60 + 10)
    sim.minute += 2
    assert sim._advance_road_response()
    assert sim.mode == "road_retreat"
    for _ in range(50):
        sim._move_road_response()
        sim.minute += 1
        if not sim._advance_road_response():
            break
    assert sim._road_distance() >= distance_before + 0.4
    assert sim.goal == "Plain" and sim.mode == "walking"


def test_recent_heard_cars_trigger_avoidance_but_future_cars_do_not():
    sim = controlled_simulation("road_response.avoidance_probability=1",
                                "road_response.approach_probability=0",
                                "road_response.avoidance_car_count=3")
    first_second = sim.minute * 60
    # Hundreds of future cars are present in the schedule, but cannot be sensed.
    sim.car_seconds = np.arange(first_second + 1000, first_second + 1500)
    for offset in (5, 20):
        sim._consider_car_response(first_second + offset)
        assert sim.road_pending is None
    sim._consider_car_response(first_second + 40)
    assert sim.road_pending["kind"] == "road_retreat"


def test_old_car_exposure_expires():
    sim = controlled_simulation("road_response.avoidance_probability=1",
                                "road_response.approach_probability=0",
                                "road_response.avoidance_car_count=2")
    first = sim.minute * 60
    sim._consider_car_response(first)
    sim.minute += sim.road_config["memory_minutes"] + 1
    sim._consider_car_response(sim.minute * 60)
    assert sim.heard_car_seconds == [sim.minute * 60]
    assert sim.road_pending is None


def test_circular_road_uses_nearest_boundary():
    sim = controlled_simulation()
    sim.geometry["Road"].update(shape="circle", center=[9.0, 5.0], radius=0.3)
    boundary, normal = sim._nearest_road_boundary()
    np.testing.assert_allclose(boundary, [8.7, 5.0])
    np.testing.assert_allclose(normal, [-1, 0])


def test_road_escape_at_map_edge_uses_a_feasible_boundary():
    sim = controlled_simulation()
    sim.position = np.array([9.0, 0.01])
    boundary, normal = sim._nearest_road_boundary()
    target = boundary + normal * sim.road_config["approach_standoff_km"]
    assert target[1] == pytest.approx(0.01)
    assert not sim._contains("Road", target)
    assert np.all(target >= 0) and np.all(target <= 10)
    # Also support a circular road touching the world boundary.
    sim.geometry["Road"].update(shape="circle", center=[9.0, 0.3], radius=0.3)
    boundary, normal = sim._nearest_road_boundary()
    target = boundary + normal * sim.road_config["approach_standoff_km"]
    assert not sim._contains("Road", target)
    assert np.all(target >= -1e-12) and np.all(target <= 10 + 1e-12)


def test_patrol_pace_encodes_energy_heat_and_boredom_within_speed_bounds():
    sim = controlled_simulation()
    sim.bars[:] = [0.5, 0.5, 0.5, 0.5, 0.5]
    baseline = sim._patrol_speed()
    for index, value, faster in [(1, 0.9, True), (2, 0.9, False), (3, 0.9, True)]:
        sim.bars[:] = [0.5, 0.5, 0.5, 0.5, 0.5]
        sim.bars[index] = value
        speed = sim._patrol_speed()
        assert (speed > baseline) is faster
    sim.movement["patrol_speed_noise_sd"] = 10
    samples = np.array([sim._patrol_speed() for _ in range(100)])
    low, high = sim.movement["patrol_speed_kmh_range"]
    assert samples.min() >= low and samples.max() <= high


def test_full_day_has_no_anticipation_and_diagnostics_follow_actual_car():
    config = load_config()
    active = simulate_day(config, seed=42)
    disabled = simulate_day(load_config(overrides=["road_response.enabled=false"]), seed=42)
    first_car = pd.Timestamp(active.traffic_times[0])
    before = pd.to_datetime(active.hidden_state.t_iso) <= first_car
    pd.testing.assert_frame_equal(active.hidden_state.loc[before], disabled.hidden_state.loc[before])
    count = int(before.sum())
    # GPS observation RNG is drawn after the trajectory; compare true positions.
    np.testing.assert_array_equal(active.gps.loc[:count - 1, ["x_true_km", "y_true_km"]],
                                  disabled.gps.loc[:count - 1, ["x_true_km", "y_true_km"]])
    assert not disabled.hidden_state.movement_intent.str.startswith("road_").any()
    responding = active.hidden_state[active.hidden_state.movement_intent.str.startswith("road_")]
    # Commitment can suppress curiosity on a particular day.
    assert (pd.to_datetime(responding.road_trigger_t_iso) < pd.to_datetime(responding.t_iso)).all()
    car_times = set(active.traffic_times)
    assert set(responding.road_trigger_t_iso) <= car_times
    assert validate_day(active, config)["valid"]


def test_default_batch_has_mixed_responses_and_preserves_invariants():
    config = load_config()
    response_days = 0
    kinds = set()
    for index in range(1, 13):
        day = simulate_day(config, day_index=index, seed=42)
        road = day.hidden_state.movement_intent.str.startswith("road_")
        response_days += int(road.any())
        kinds.update(day.hidden_state.loc[road, "movement_intent"])
        assert validate_day(day, config)["valid"]
    assert 1 < response_days < 12
    assert {"road_approach", "road_retreat"} <= kinds
