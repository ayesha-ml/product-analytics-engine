# src/engine/ztest.py
import numpy as np
from scipy.stats import norm


def run_ztest(
    n_c: int,
    x_c: int,
    n_t: int,
    x_t: int,
    alpha: float = 0.05
) -> dict:
    """
    Two-sample proportion Z-test with correct standard error handling.

    Standard error usage:
    - POOLED SE   → Z-statistic only. Null hypothesis assumes p_c == p_t
                    so we pool both groups into one rate estimate.
    - UNPOOLED SE → Confidence interval only. CI estimates the true
                    difference between two distinct rates without
                    imposing the null hypothesis assumption.
    Mixing these two is the most common Z-test implementation error.

    Parameters
    ----------
    n_c   : control group total users
    x_c   : control group conversions
    n_t   : treatment group total users
    x_t   : treatment group conversions
    alpha : significance level, two-tailed (default 0.05)

    Returns
    -------
    dict with rates, lift, z_stat, p_value, CI, significance verdict
    """
    p_c  = x_c / n_c
    p_t  = x_t / n_t
    lift = p_t - p_c

    # Pooled proportion under H0: p_c == p_t
    p_pool    = (x_c + x_t) / (n_c + n_t)
    se_pooled = np.sqrt(p_pool * (1 - p_pool) * (1/n_c + 1/n_t))
    z_stat    = lift / se_pooled
    p_value   = 2 * (1 - norm.cdf(abs(z_stat)))

    # Unpooled SE for confidence interval — does NOT assume H0
    se_unpooled = np.sqrt(p_c*(1-p_c)/n_c + p_t*(1-p_t)/n_t)
    z_crit      = norm.ppf(1 - alpha/2)
    ci_lower    = lift - z_crit * se_unpooled
    ci_upper    = lift + z_crit * se_unpooled

    return {
        'p_control':         round(p_c, 6),
        'p_treatment':       round(p_t, 6),
        'absolute_lift':     round(lift, 6),
        'relative_lift_pct': round(lift / p_c * 100, 2),
        'z_stat':            round(z_stat, 4),
        'p_value':           round(p_value, 6),
        'ci_95':             (round(ci_lower, 6), round(ci_upper, 6)),
        'significant':       bool(p_value < alpha and ci_lower > 0)
    }