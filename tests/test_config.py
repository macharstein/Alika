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
    assert config["learnability"]["latent_ranges"]["start_hunger"] == [0.2, 0.7]
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


def test_canonical_learnability_paths_and_legacy_overrides_are_equivalent(tmp_path):
    expressions = [
        'learnability.softmax_temperature=0.9',
        'learnability.behaviour.goal_commitment=false',
        'learnability.behaviour.fatigue_interrupt_threshold=0.08',
        'learnability.behaviour.night_nap_min_minutes=30',
        'learnability.behaviour.night_nap_max_cycles=2',
        'learnability.activity.catnap_minutes_range=[30,60]',
        'learnability.activity.hunt_end=21:30',
        'learnability.latent_ranges.heat.0=0.85',
        'learnability.chase_base_probability=0.3',
        'learnability.chase.probability_clip=[0.1,0.5]',
    ]
    from lionsim.config import LEARNABILITY_ALIASES
    legacy = []
    for expression in expressions:
        for old, new in LEARNABILITY_ALIASES.items():
            if expression.startswith(new + '.') or expression.startswith(new + '='):
                expression = old + expression[len(new):]
                break
        legacy.append(expression)
    canonical = load_config(overrides=expressions)
    assert load_config(overrides=legacy).to_dict() == canonical.to_dict()
    saved = tmp_path / 'canonical.json'
    saved.write_text(json.dumps(canonical.to_dict()))
    assert load_config(saved).to_dict() == canonical.to_dict()
    assert not {'behaviour', 'behaviours', 'chase'} & canonical.to_dict().keys()
    assert 'latent_ranges' not in canonical['randomness']
    assert load_config(overrides=['learnability.softmax_temperature=0.8', 'randomness.softmax_temperature=0.9'])['learnability']['softmax_temperature'] == .9
    assert load_config(overrides=['randomness.softmax_temperature=0.9', 'learnability.softmax_temperature=0.8'])['learnability']['softmax_temperature'] == .8


def test_legacy_file_migration_canonical_precedence_and_comments(tmp_path):
    legacy = tmp_path / 'old.json'
    legacy.write_text(json.dumps({'behaviour': {'goal_commitment': False, 'night_nap_max_cycles': 2},
                                 'randomness': {'softmax_temperature': .9},
                                 'learnability': {'softmax_temperature': .8, 'behaviour': {'goal_commitment': True}}}))
    config = load_config(legacy)
    assert config['learnability']['softmax_temperature'] == .8
    assert config['learnability']['behaviour']['goal_commitment'] is True
    assert config['learnability']['behaviour']['night_nap_max_cycles'] == 2
    options = config['learnability']
    assert all(isinstance(options['_comments'][name], str) for name in options if not name.startswith('_'))


@pytest.mark.parametrize('expression', [
    'learnability.softmax_temperature=0',
    'learnability.behaviour.goal_commitment=1',
    'learnability.behaviour.night_nap_min_minutes=0',
    'learnability.activity.hunt_end=18:00',
    'learnability.latent_ranges.heat=[2,1]',
    'learnability.chase.probability_clip=[0,2]',
    'learnability.oracle_rollouts=0',
    'learnability.oracle_days=0',
    'learnability.oracle_noise_relative_tolerance=2',
])
def test_invalid_canonical_learnability_settings_fail(expression):
    with pytest.raises(ValueError):
        load_config(overrides=[expression])
