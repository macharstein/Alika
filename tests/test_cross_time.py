"""Latent-to-observable links use fixed seeds and directional tolerances."""
import numpy as np
from lionsim.config import load_config
from lionsim.simulator import _DaySimulation, simulate_day
from lionsim.reports import build_reports
from lionsim.stats import summarize_for_stats, build_stats_report


def state(*overrides):
    c = load_config(overrides=list(overrides))
    return _DaySimulation(c, 1, 42, '2026-01-01', np.random.SeedSequence(42))


def test_hunger_wake_shift_preserves_initial_wake_clip():
    low = state('learnability.latent_ranges.start_hunger=[0.1,0.1]', 'randomness.wake_time_sd_minutes=0')
    high = state('learnability.latent_ranges.start_hunger=[1,1]', 'randomness.wake_time_sd_minutes=0')
    assert 20 * 60 < low.wake_seconds - high.wake_seconds <= 30 * 60
    assert 0 <= high.wake_seconds <= low.wake_seconds <= 120 * 60


def test_prey_increases_scouting_pause_and_advances_hunt_readiness():
    low = state('learnability.latent_ranges.prey_density=[0.5,0.5]')
    high = state('learnability.latent_ranges.prey_density=[1.5,1.5]')
    for sim in (low, high):
        sim.minute = sim.offset('08:00')
        sim.goal = sim.raw_zone = 'Kopje'
        sim.arrive()
        assert sim.mode == 'scouting'
    assert high.until - low.until > 60
    assert high.hunt_ready_minute < low.hunt_ready_minute
    for sim in (low, high):
        sim.minute = sim.offset('22:00')
        assert not sim._can_hunt()


def test_measured_links_have_expected_directions_in_fixed_seed_batch():
    config = load_config()
    records = []
    for index in range(1, 41):
        day = simulate_day(config, day_index=index, seed=42)
        records.append(summarize_for_stats(day, build_reports(day, config), config))
    correlations = build_stats_report(records, config)['correlations']
    assert correlations['prey_density_vs_kopje_dwell']['count'] >= 20
    assert correlations['prey_density_vs_kopje_dwell']['value'] > .2
    assert correlations['prey_density_vs_first_chase_time']['value'] < -.15
    assert correlations['start_hunger_vs_wake_time']['value'] < -.15
    assert correlations['heat_vs_shade_entry_time']['value'] < -.2
