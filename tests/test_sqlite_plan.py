import json
from datetime import date, timedelta
from pathlib import Path


def test_committed_split_plan():
    plan = json.loads(Path('data/split_plan.json').read_text())
    assert plan['package_version'] == '6.0.0'
    assert plan['schema'] == 'lionsim-v6'
    assert plan['image_size'] == 1000
    previous = date(2026, 1, 1)
    for name, days, seed in [('train', 1825, 7001), ('val', 1095, 7002), ('test', 730, 7003)]:
        part = plan['splits'][name]
        assert part['days'] == days and part['seed'] == seed
        assert seed not in plan['forbidden_seeds']
        assert date.fromisoformat(part['start_date']) == previous
        assert date.fromisoformat(part['end_date']) == previous + timedelta(days=days - 1)
        previous += timedelta(days=days)
