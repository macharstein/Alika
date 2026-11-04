import csv
import json
from collections import Counter

import numpy as np
import pytest

from lionsim.config import load_config
from lionsim.simulator import simulate_day, _DaySimulation
from lionsim.events import TOKENS
from lionsim.reports import build_reports, target_rows
from lionsim.validate import validate_day


def config_for(category):
    return load_config(overrides=[f'day_types.probabilities.{k}={int(k==category)}' for k in ('normal','prey_rich','rival')])


def test_day_type_and_jitter_draws_are_bounded_and_independent():
    config=load_config(); counts=Counter(); conditional={k:Counter() for k in config['weather']['probabilities']}
    for index, sequence in enumerate(np.random.SeedSequence(190).spawn(1200)):
        sim=_DaySimulation(config,index+1,190,'2026-01-01',sequence)
        counts[sim.day_type]+=1;conditional[sim.weather][sim.day_type]+=1
        assert all(-20 <= v <= 20 for v in sim.period_jitter.values())
        assert sim.hunt_ready_minute>=sim.offset('18:30')
    for name,p in config['day_types']['probabilities'].items():
        assert abs(counts[name]/1200-p)<.04
        for subset in conditional.values(): assert abs(subset[name]/sum(subset.values())-p)<.10


@pytest.fixture(scope='module')
def type_days():
    return {name:[simulate_day(config_for(name),day_index=i,seed=811) for i in range(1,41)] for name in ('normal','prey_rich','rival')}


def test_prey_rich_earlier_chases_and_rival_more_entries(type_days):
    def chase(day):
        return next((int(e['t'][11:13])*60+int(e['t'][14:16]) for e in day.events if e['token']=='CHASE_START'),None)
    means={name:np.mean([t for d in days if (t:=chase(d)) is not None]) for name,days in type_days.items()}
    assert means['prey_rich'] < means['normal'] - 5
    entries={name:np.mean([sum(e['token'].startswith('ENTER_') for e in d.events) for d in days]) for name,days in type_days.items()}
    assert entries['rival'] > entries['normal'] + .3
    for name,days in type_days.items():
        for day in days:
            assert validate_day(day,config_for(name))['valid'], validate_day(day,config_for(name))['errors']
            assert all(e['t'][11:16]<'22:00' for e in day.events if e['token'] in ('CHASE_START','ENTER_HUNT'))
            if name=='prey_rich': assert sum(e['token']=='CHASE_START' for e in day.events)<=4


def test_day_type_never_in_public_context_and_resume(tmp_path):
    from lionsim.run import build_parser, run
    parser=build_parser()
    directory=run(parser.parse_args(['--stats-only','--stats-days','2','--keep-files','--chunk-size','1','--out',str(tmp_path)]))
    run(parser.parse_args(['--resume',str(directory)]))
    rows=list(csv.DictReader((directory/'targets.csv').open()))
    assert 'day_type' not in rows[0] and {'weather','ambient_temp_c'}<=rows[0].keys()
    payload=json.loads((directory/'days/day_0001/day.json').read_text())
    assert 'day_type' not in payload and payload['ground_truth_latents']['day_type'] in ('normal','prey_rich','rival')
    assert all('day_type' not in report for report in payload['reports'])
    assert len(TOKENS)==17
    manifest=json.loads((directory/'run_manifest.json').read_text())
    assert manifest['versions']['lionsim']=='6.0.0' and manifest['schema_version']=='lionsim-v6'
    manifest['schema_version']='lionsim-v5'
    (directory/'run_manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='current schema'): run(parser.parse_args(['--resume',str(directory)]))


def test_new_randomness_values_and_original_noise_unchanged():
    c=load_config()
    assert c['learnability']['softmax_temperature']==.85
    assert c['randomness']['period_prior_scale']==.8
    assert c['randomness']['gps_noise_sd_m']==8
    assert c['randomness']['bar_noise_sd']==.005
