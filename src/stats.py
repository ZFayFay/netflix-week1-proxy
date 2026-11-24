"""Small statistics helpers used by the notebook: bootstrap intervals and a Wilson interval."""

import numpy as np
from scipy.stats import norm, spearmanr

N_RESAMPLES = 4000
SEED = 2026


def spearman(x, y):
    """Spearman rank correlation between two columns. 1 means exactly the same order."""
    return float(spearmanr(x, y)[0])


def bootstrap_distribution(table, statistic, n_resamples=N_RESAMPLES, seed=SEED):
    """Recompute a statistic on resampled tables and return all the values.

    Each resample draws len(table) rows with replacement, so a title can appear twice.
    `statistic` takes a table and returns one number. The seed is fixed so that every
    run of the notebook gives the same intervals.
    """
    random = np.random.default_rng(seed)
    n_rows = len(table)
    values = np.empty(n_resamples)
    for i in range(n_resamples):
        row_numbers = random.integers(0, n_rows, n_rows)
        resample = table.iloc[row_numbers]
        values[i] = statistic(resample)
    return values


def percentile_interval(values, level=0.95):
    """Return the central interval of a set of bootstrap values, for example 2.5% to 97.5%."""
    tail = (1 - level) / 2
    low = np.nanpercentile(values, 100 * tail)
    high = np.nanpercentile(values, 100 * (1 - tail))
    return float(low), float(high)


def bootstrap_interval(table, statistic, n_resamples=N_RESAMPLES, seed=SEED, level=0.95):
    """Percentile bootstrap interval for one statistic of one table.

    For a paired comparison, pass a statistic that returns the difference between two
    quantities computed on the same resample. Both then see the same titles each time.
    """
    values = bootstrap_distribution(table, statistic, n_resamples, seed)
    return percentile_interval(values, level)


def bootstrap_difference_interval(table_a, table_b, statistic, n_resamples=N_RESAMPLES, level=0.95):
    """Interval for statistic(table_a) minus statistic(table_b), for two separate groups.

    The two groups hold different titles, so each is resampled on its own, with its own seed.
    """
    values_a = bootstrap_distribution(table_a, statistic, n_resamples, SEED)
    values_b = bootstrap_distribution(table_b, statistic, n_resamples, SEED + 1)
    return percentile_interval(values_a - values_b, level)


def wilson_interval(successes, n, level=0.95):
    """Wilson score interval for a proportion. It behaves well when the count is small."""
    z = norm.ppf(1 - (1 - level) / 2)
    proportion = successes / n
    denominator = 1 + z**2 / n
    center = (proportion + z**2 / (2 * n)) / denominator
    spread = z * np.sqrt(proportion * (1 - proportion) / n + z**2 / (4 * n**2))
    half_width = spread / denominator
    return float(center - half_width), float(center + half_width)


def interval_text(low, high, decimals=2):
    """Format an interval as text, for example '0.89 to 0.97'."""
    return f"{low:.{decimals}f} to {high:.{decimals}f}"
