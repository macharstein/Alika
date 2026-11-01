"""Configuration integration checks: CLI expressions and invalid simulations."""

from __future__ import annotations

import json

import pytest

from lionsim.config import Config, load_config


def test_dotted_overrides_support_lists_and_json_values() -> None:
    config = load_config(overrides=[
        "goal.periods.0.priors.Den=2.75",
        "randomness.latent_ranges.start_hunger=[0.2,0.7]",
        "map.zones.Den.center.0=2.1",
        "output.prefer_parquet=false",
        "images.path_color=#AAAAAA",
    ])
    assert config["goal"]["periods"][0]["priors"]["Den"] == 2.75
    assert config["randomness"]["latent_ranges"]["start_hunger"] == [0.2, 0.7]
    assert config["map"]["zones"]["Den"]["center"] == [2.1, 8.0]
    assert config["output"]["prefer_parquet"] is False
    assert config["images"]["path_color"] == "#AAAAAA"


def test_partial_json_merges_before_overrides(tmp_path) -> None:
    path = tmp_path / "custom.json"
    path.write_text(json.dumps({"randomness": {"gps_noise_sd_m": 22.0},
                                "output": {"prefer_parquet": False}}))
    config = load_config(path, ["randomness.gps_noise_sd_m=18.0"])
    assert config["randomness"]["gps_noise_sd_m"] == 18.0
    assert config["output"]["prefer_parquet"] is False
    assert config["randomness"]["bar_noise_sd"] == 0.005


def test_configs_and_snapshots_do_not_share_mutable_defaults() -> None:
    first, second = Config(), Config()
    snapshot = first.to_dict()
    snapshot["map"]["zones"]["Den"]["center"][0] = 9.0
    first["randomness"]["gps_noise_sd_m"] = 30.0
    assert first["map"]["zones"]["Den"]["center"][0] == 2.0
    assert second["randomness"]["gps_noise_sd_m"] == 15.0


def test_nonstandard_report_intervals_are_supported() -> None:
    config = load_config(overrides=[
        'time.report_times=["07:30","12:15","22:30","05:00"]'
    ])
    assert len(config["time"]["report_times"]) == 4


@pytest.mark.parametrize(("expression", "message"), [
    ("randomness.softmax_temperature=0", "must be positive"),
    ("randomness.gps_dropout_probability=1.1", "must lie in"),
    ("randomness.latent_ranges.start_hunger=[0.8,0.2]", "invalid ordered bounds"),
    ("behaviours.catnap_minutes_range=[1,2.5]", "integer"),
    ("randomness.bar_noise_sd=NaN", "finite number"),
    ("map.zones.Den.radius=3.0", "outside"),
    ("map.zones.Shade.center=[2.0,8.0]", "overlap"),
    ("map.zones.Plain.x=[8.0,1.0]", "increase strictly"),
    ("map.zones.Den=null", "must be an object"),
    ("images.zone_alpha=1.01", "must lie in"),
    ("images.path_color=white", "RRGGBB"),
    ("road_response.approach_probability=1.1", "must lie in"),
    ("road_response.reaction_delay_minutes_range=[0,2]", "invalid ordered bounds"),
    ("road_response.watch_minutes_range=[12,3]", "invalid ordered bounds"),
    ("time.step_minutes=2", "requires"),
    ('time.report_times=["11:00","08:00","05:00"]', "chronological"),
    ('time.report_times=["08:00","08:00","05:00"]', "unique"),
    ('time.report_times=["08:00","11:00"]', "end at"),
    ("tourists.start=06:00", "latest initial wake"),
    ("tourists.end=15:00", "end later"),
    ("goal.periods.0.end=08:00", "cover every clock minute"),
    ("goal.periods.0.priors.Den=null", "finite number"),
    ("chase.duration_seconds_range=[5,40]", "inside outcome_delay"),
    ("images.contact_sheet_rows=1", "at least as many cells"),
    ("missing.parameter=2", "Unknown configuration key"),
    ("goal.periods.99.priors.Den=2", "Invalid list index"),
    ("randomness.gps_noise_sd_m", "dotted.key=value"),
])
def test_invalid_configurations_fail_early(expression: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        load_config(overrides=[expression])


def test_unknown_partial_json_key_is_not_silently_ignored(tmp_path) -> None:
    path = tmp_path / "typo.json"
    path.write_text('{"randomness":{"gps_noise_sd_mm":20}}')
    with pytest.raises(ValueError, match="Unknown configuration key"):
        load_config(path)
