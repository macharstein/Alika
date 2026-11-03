"""Render explicitly selected trip examples using the existing text-free map."""

import argparse
from datetime import timedelta
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import numpy as np

from . import __version__, SCHEMA_VERSION
from .config import load_config
from .features_path import smoothed_observed_prefix
from .io_utils import atomic_output, write_json
from .plotting import mpl_image, render_reports
from .simulator import simulate_day
from .trip_statistics import summarize_trips


def render_examples(run_directory, selections, destination):
    """Regenerate selected days with their saved config; retain no trajectories.

    The first selection is wandering, the second direct. Selection is explicit
    and documented, never silently replaced with more flattering examples.
    """
    run_directory, destination = Path(run_directory), Path(destination)
    manifest_path = run_directory / 'run_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if (manifest['versions']['lionsim'] != __version__
            or manifest['schema_version'] != SCHEMA_VERSION):
        raise ValueError('Example regeneration requires the original package/schema version')
    if len(selections) != 2:
        raise ValueError('Select exactly two trips: wandering, then direct')
    # Validate the saved configuration using the normal loader, including overrides.
    with TemporaryDirectory(prefix='lionsim-style-') as temporary:
        directory = Path(temporary)
        config_path = directory / 'config.json'
        config_path.write_text(json.dumps(manifest['config']))
        config = load_config(config_path)
        panels, metadata = [], []
        for label, (day_index, trip_id) in zip(('wandering', 'direct'), selections):
            if day_index not in manifest['day_indices']:
                raise ValueError(f'Day {day_index} is not in the source run')
            day = simulate_day(config, day_index=day_index, seed=manifest['seed'],
                               start_date=manifest['start_date'])
            trips = summarize_trips(day, config)
            trip = next((t for t in trips if t['trip_id'] == trip_id), None)
            if trip is None or trip['status'] != 'arrived':
                raise ValueError(f'Day {day_index} trip {trip_id} is not a completed arrival')
            checkpoint = json.loads((run_directory / 'checkpoints' / f'day_{day_index:04d}.json').read_text())
            recorded = next((t for t in checkpoint['stats']['trips'] if t['trip_id'] == trip_id), None)
            if trip != recorded:
                raise ValueError('Regenerated trip does not match its recorded statistics')
            observed = smoothed_observed_prefix(day.gps, day.gps.iloc[-1]['t_iso'], config)
            origin = observed.index[0]
            begin = origin + timedelta(minutes=trip['start_minute'])
            end = origin + timedelta(minutes=trip['end_minute'])
            segment = observed.loc[begin:end]
            image_day = SimpleNamespace(day_index=day_index, date=day.date, gps=segment)
            reports = [{'report_time': end.isoformat(), 'report_index': 1,
                        'path_up_to_index': len(segment) - 1}]
            paths = render_reports(image_day, reports, config, directory / label)
            panels.append(mpl_image.imread(paths[0]))
            hidden = day.hidden_state.loc[day.hidden_state['trip_id'] == trip_id].iloc[0]
            metadata.append({'panel': label, **trip, 'start_time': begin.isoformat(),
                             'end_time': end.isoformat(), 'mood': float(hidden['trip_mood']),
                             'planned_detours': int(hidden['trip_detour_count'])})
        left, right = metadata
        if not (left['urgency'] < right['urgency'] and left['boredom'] > right['boredom']
                and left['observed']['straightness'] < right['observed']['straightness']):
            raise ValueError('Selected trips do not have the requested contrasting styles')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with atomic_output(destination) as temporary_image:
            mpl_image.imsave(temporary_image, np.concatenate(panels, axis=1))
        provenance = {
            'package_version': __version__, 'seed': manifest['seed'],
            'source_manifest': str(manifest_path.resolve()),
            'source_manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            'smoothing_minutes': config['features_path']['smoothing_minutes'],
            'panels': metadata,
            'description': 'Left: low urgency/high boredom; right: high urgency/low boredom. '
                           'Same map extent and scale. White paths are trailing-smoothed observed GPS. '
                           'Explicitly selected illustrations, not population evidence or a causal comparison. '
                           'Times and metrics appear here only; PNG contains no text. '
                           'S8.3 acceptance failures remain unresolved.'}
        write_json(destination.with_suffix('.json'), provenance, True)
    return provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    parser.add_argument('--wandering', nargs=2, type=int, required=True, metavar=('DAY', 'TRIP'))
    parser.add_argument('--direct', nargs=2, type=int, required=True, metavar=('DAY', 'TRIP'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    render_examples(args.run_directory, [args.wandering, args.direct], args.out)


if __name__ == '__main__':
    main()
