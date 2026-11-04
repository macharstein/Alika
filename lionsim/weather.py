"""Daily observable weather and causal temperature measurements."""
import numpy as np
import pandas as pd


def draw_weather(rng, options):
    names = list(options['probabilities'])
    category = str(rng.choice(names, p=[options['probabilities'][name] for name in names]))
    return category, float(rng.uniform(*options['heat_ranges'][category]))


def ambient_measurements(ambient, heat, bars, options, rng):
    low, high = options['ambient_c_range']
    scaled = (np.asarray(ambient) * heat - bars['ambient_min']) / (bars['ambient_max'] - bars['ambient_min'])
    true = low + (high - low) * np.clip(scaled, 0, 1)
    smooth = pd.Series(true).rolling(options['smoothing_minutes'], min_periods=1).mean().to_numpy()
    return true, smooth + rng.normal(0, options['ambient_noise_sd_c'], len(true))
