"""Real-trip examples preserve map rendering and recorded provenance."""

import json

import numpy as np
import pytest
from matplotlib.figure import Figure
from matplotlib.image import imread
from matplotlib.text import Text

from lionsim import __version__, SCHEMA_VERSION
from lionsim.config import load_config
from lionsim.simulator import simulate_day
from lionsim.style_examples import render_examples
from lionsim.trip_statistics import summarize_trips


@pytest.fixture
def source(tmp_path):
    # Fixed v6 fixture IDs with the same geometry/style criteria as the old examples.
    config = load_config(overrides=['images.size_px=120',
        'movement_style.attraction_intercept=0.6', 'movement_style.attraction_urgency_weight=0.8',
        'movement_style.speed_intercept=0.85', 'movement_style.speed_urgency_weight=0.3',
        'movement_style.detour_probability_scale=0.7', 'movement_style.detour_urgency_weight=0',
        'movement_style.departure_alignment_weight=0', 'movement_style.detour_offset_km_range=[0.4,1.0]'])
    manifest = {'config': config.to_dict(), 'versions': {'lionsim': __version__},
                'schema_version': SCHEMA_VERSION, 'day_indices': [8, 9],
                'seed': 42, 'start_date': '2026-01-01'}
    (tmp_path / 'run_manifest.json').write_text(json.dumps(manifest))
    (tmp_path / 'checkpoints').mkdir()
    for day_index in manifest['day_indices']:
        day = simulate_day(config, day_index=day_index)
        checkpoint = {'stats': {'trips': summarize_trips(day, config)}}
        (tmp_path / 'checkpoints' / f'day_{day_index:04d}.json').write_text(json.dumps(checkpoint))
    return tmp_path


def test_examples_are_text_free_repeatable_and_match_recorded_trips(source, monkeypatch):
    savefig = Figure.savefig
    rendered = []

    def inspect(figure, *args, **kwargs):
        assert not any(t.get_text() for t in figure.findobj(Text))
        axis = figure.axes[0]
        assert not axis.axison and axis.get_legend() is None
        assert axis.get_xlim() == (0, 10) and axis.get_ylim() == (0, 10)
        assert len(axis.patches) == 8 and len(axis.lines) == 1
        rendered.append(len(axis.lines[0].get_xdata()))
        return savefig(figure, *args, **kwargs)

    monkeypatch.setattr(Figure, 'savefig', inspect)
    output = source / 'examples.png'
    first = render_examples(source, [(8, 6), (9, 4)], output)
    original = output.read_bytes()
    assert first == render_examples(source, [(8, 6), (9, 4)], output)
    assert original == output.read_bytes()
    left, right = first['panels']
    assert left['urgency'] <= .3 and left['boredom'] >= .7
    assert right['urgency'] >= .7 and right['boredom'] <= .3
    assert left['observed']['max_perpendicular_distance_km'] > .4
    assert left['observed']['straightness'] < .6 < .95 < right['observed']['straightness']
    assert left['planned_detours'] == 1 and right['planned_detours'] == 0
    assert rendered[:2] == [p['end_minute'] - p['start_minute'] + 1 for p in first['panels']]
    pixels = imread(output)
    assert pixels.shape == (120, 240, 4)
    # The Road reaches the top edge, so only empty map corners must be black.
    np.testing.assert_array_equal(pixels[0, [0, 119, 120, 239], :3], 0)
    assert np.any(pixels[:, :120, :3] > .9) and np.any(pixels[:, 120:, :3] > .9)
    metadata = json.loads(output.with_suffix('.json').read_text())
    assert metadata == first and 'start_time' in metadata['panels'][0]
    assert 'x_km' not in output.with_suffix('.json').read_text()


def test_changed_source_and_wrong_version_do_not_publish_examples(source):
    output = source / 'examples.png'
    checkpoint = source / 'checkpoints' / 'day_0008.json'
    record = json.loads(checkpoint.read_text())
    next(t for t in record['stats']['trips'] if t['trip_id'] == 6)['urgency'] = .99
    checkpoint.write_text(json.dumps(record))
    with pytest.raises(ValueError, match='does not match'):
        render_examples(source, [(8, 6), (9, 4)], output)
    assert not output.exists()
    manifest_path = source / 'run_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['versions']['lionsim'] = '4.5.0'
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='original package/schema'):
        render_examples(source, [(8, 6), (9, 4)], output)
    assert not output.exists()
