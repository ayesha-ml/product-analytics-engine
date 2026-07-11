import numpy as np
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

def compute_sample_size(
    p0: float,
    mde: float,
    alpha: float = 0.05,
    power: float = 0.80
) -> dict:
    """
    Calculate the required sample size per variant for a two-sample proportion test.
    """
    p1          = p0 + mde
    effect_size = proportion_effectsize(p0, p1)
    analysis    = NormalIndPower()
    
    n_per_group = analysis.solve_power(
        effect_size=effect_size,
        alpha=alpha,
        power=power,
        ratio=1.0
    )
    
    return {
        'baseline_rate':  p0,
        'treatment_rate': p1,
        'mde':            mde,
        'effect_size_h':  round(effect_size, 4),
        'n_per_group':    int(round(n_per_group)),
        'n_total':        int(round(n_per_group * 2)),
        'alpha':          alpha,
        'power':          power
    }