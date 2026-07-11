from scipy.stats import chisquare


def detect_srm(
    n_control: int,
    n_treatment: int,
    expected_split: tuple = (0.5, 0.5),
    alpha: float = 0.05
) -> dict:
    
    total    = n_control + n_treatment
    expected = [total * expected_split[0], total * expected_split[1]]
    chi2, p  = chisquare([n_control, n_treatment], f_exp=expected)

    return {
        'n_control':    n_control,
        'n_treatment':  n_treatment,
        'chi2_stat':    round(chi2, 4),
        'p_value':      round(p, 6),
        'srm_detected': bool(p < alpha),
        'verdict':      'ABORT — randomisation broken' if p < alpha else 'PASS'
    }