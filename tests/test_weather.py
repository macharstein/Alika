import json
import numpy as np
import pandas as pd
import pytest
from lionsim.config import load_config
from lionsim.weather import draw_weather, ambient_measurements
from lionsim.simulator import simulate_day, _DaySimulation
from lionsim.reports import build_reports, target_rows
from lionsim.io_utils import write_day


def forced_weather(name):
    return load_config(overrides=[f'weather.probabilities.{k}={int(k==name)}' for k in ('clear','hot','overcast','rain')])


def test_weather_draw_frequencies_and_heat_ranges():
    config = load_config(); rng = np.random.default_rng(88)
    samples = [draw_weather(rng, config['weather']) for _ in range(5000)]
    for name, probability in config['weather']['probabilities'].items():
        assert abs(sum(s[0]==name for s in samples)/len(samples)-probability) < .025
        low, high = config['weather']['heat_ranges'][name]
        assert all(low <= heat <= high for category, heat in samples if category==name)


def test_observable_weather_temperature_and_saved_true_values(tmp_path):
    config=forced_weather('rain'); day=simulate_day(config, seed=71)
    reports=build_reports(day, config); rows=target_rows(day,reports)
    write_day(day,reports,tmp_path,prefer_parquet=False)
    payload=json.loads((tmp_path/'day.json').read_text())
    assert payload['weather']=='rain'
    assert all(r['weather']=='rain' and np.isfinite(r['ambient_temp_c']) for r in rows)
    assert all(np.isfinite(r['ambient_temp_c']) for r in payload['reports'])
    assert 'ambient_temp_c_true' in day.hidden_state
    assert day.gps.ambient_temp_c.iloc[180]==reports[0]['ambient_temp_c']
    other=simulate_day(config,seed=71)
    pd.testing.assert_frame_equal(day.gps,other.gps)
    assert day.events==other.events


def test_ambient_smoothing_is_causal():
    c=load_config(); a=np.linspace(.2,1,80)
    true, full=ambient_measurements(a,1,c['bars'],c['weather'],np.random.default_rng(2))
    _, short=ambient_measurements(a[:30],1,c['bars'],c['weather'],np.random.default_rng(2))
    np.testing.assert_array_equal(full[:30],short)
    assert true.min()>=12 and true.max()<=42


def test_rain_expected_traffic_and_nap_effects():
    simulations={name:[_DaySimulation(forced_weather(name),i,17,'2026-01-01',np.random.SeedSequence(i)) for i in range(1,101)] for name in ('clear','rain')}
    assert np.mean([len(s.car_seconds) for s in simulations['rain']]) < .4*np.mean([len(s.car_seconds) for s in simulations['clear']])
    assert np.mean([s.shade_departure for s in simulations['rain']]) > np.mean([s.shade_departure for s in simulations['clear']])
    assert np.mean([s.midday_wake-s.shade_departure for s in simulations['rain']]) < np.mean([s.midday_wake-s.shade_departure for s in simulations['clear']])


@pytest.mark.parametrize('override',['weather.probabilities.rain=-0.1','weather.ambient_noise_sd_c=-1','weather.rain.traffic_multiplier=2'])
def test_weather_config_rejects_invalid(override):
    with pytest.raises(ValueError): load_config(overrides=[override])
