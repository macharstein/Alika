"""Exact state continuation and Monte Carlo oracle contracts."""

from datetime import timedelta

import numpy as np
import pandas as pd
import pytest

from lionsim.config import load_config
from lionsim.reports import build_reports, report_offsets_minutes
from lionsim.simulator import _DaySimulation, simulate_day


def simulation(seed=42):
    return _DaySimulation(load_config(), 1, seed, '2026-01-01',
                          np.random.SeedSequence(seed).spawn(1)[0])


def test_original_rng_resume_reproduces_entire_day_at_every_report():
    config = load_config()
    original = simulate_day(config)
    running = simulation()
    for offset in report_offsets_minutes(config)[:-1]:
        running.advance_to(offset)
        snapshot = running.snapshot()
        resumed = _DaySimulation.resume(snapshot).run()
        assert resumed.events == original.events
        assert resumed.traffic_times == original.traffic_times
        assert resumed.latents == original.latents
        assert resumed.seed_info == original.seed_info
        pd.testing.assert_frame_equal(resumed.gps, original.gps)
        pd.testing.assert_frame_equal(resumed.hidden_state, original.hidden_state)
        assert build_reports(resumed, config) == build_reports(original, config)
        assert snapshot.next_minute == offset
        assert len(snapshot.history['behaviours']) == offset
        boundary = (snapshot.start + timedelta(minutes=offset)).isoformat()
        assert all(event['t'] < boundary for event in snapshot.events)


def test_snapshots_and_restores_do_not_share_mutable_state():
    running = simulation()
    running.advance_to(600)
    saved = running.snapshot()
    resumed = _DaySimulation.resume(saved)
    resumed.position[:] = 0
    resumed.bars[:] = 0
    resumed.latents['heat'] = 10
    resumed.events.clear()
    resumed.history['goals'].clear()
    resumed.rng.random(10)
    assert saved.events == running.events
    assert saved.history['goals'] == running.history['goals']
    assert saved.latents == running.latents
    np.testing.assert_array_equal(saved.bars, running.bars)
    assert saved.rng.bit_generator.state == running.rng.bit_generator.state
    with pytest.raises(ValueError):
        running.advance_to(599)
    with pytest.raises(ValueError):
        running.advance_to(1441)
