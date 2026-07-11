import streamlit as st
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.engine.power_analysis import compute_sample_size
from src.engine.srm_check import detect_srm
from src.engine.ztest import run_ztest
from app.bq_app_client import get_client, run_query
from src.sql_loader import load_sql

st.title("Experimentation Engine")
st.markdown(
    "**Business Question:** Did our product change drive a measurable "
    "improvement in purchase conversion rate?"
)
st.markdown(
    "Three-stage frequentist pipeline: "
    "**1. Power Analysis  2. SRM Check  3.Z-Test and Decision**"
)

st.divider()

# Power Analysis
st.subheader("Stage 1: Pre-Test Power Analysis")
st.caption(
    "Determines minimum sample size before an experiment launches. "
    "Running this after peeking at results invalidates the analysis."
)

col1, col2, col3, col4 = st.columns(4)
p0    = col1.number_input("Baseline Rate",         value=0.5306,
                           step=0.01, min_value=0.01, max_value=0.99)
mde   = col2.number_input("Min Detectable Effect", value=0.02,
                           step=0.005, min_value=0.001)
alpha = col3.number_input("Alpha",                 value=0.05,
                           step=0.01, min_value=0.01, max_value=0.20)
power = col4.number_input("Power",                 value=0.80,
                           step=0.05, min_value=0.50, max_value=0.99)

power_result = compute_sample_size(p0=p0, mde=mde, alpha=alpha, power=power)

col1, col2, col3 = st.columns(3)
col1.metric("Required Per Group", f"{power_result['n_per_group']:,}")
col2.metric("Total Required",     f"{power_result['n_total']:,}")
col3.metric("Effect Size (h)",    f"{abs(power_result['effect_size_h']):.4f}")

st.divider()

#  SRM Check 
st.subheader("Stage 2: Sample Ratio Mismatch Check")
st.caption(
    "Validates that observed group sizes match the intended split. "
)

use_live = st.toggle("Load live experiment data from BigQuery", value=False)

if use_live:
    client = get_client()
    with st.spinner("Querying experiment groups..."):
        df = run_query(client, load_sql('experiment_groups.sql'))
    st.dataframe(df, use_container_width=True, hide_index=True)
    ctrl = df[df['experiment_group'] == 'control'].iloc[0]
    trt  = df[df['experiment_group'] == 'treatment'].iloc[0]
    n_c  = int(ctrl['total_users'])
    x_c  = int(ctrl['conversions'])
    n_t  = int(trt['total_users'])
    x_t  = int(trt['conversions'])
else:
    col1, col2 = st.columns(2)
    n_c = col1.number_input("Control Users",        value=51724, step=100)
    x_c = col1.number_input("Control Conversions",  value=27445, step=100)
    n_t = col2.number_input("Treatment Users",       value=48276, step=100)
    x_t = col2.number_input("Treatment Conversions", value=25511, step=100)

total      = n_c + n_t
expected_c = n_c / total
expected_t = n_t / total

srm = detect_srm(
    n_control=n_c,
    n_treatment=n_t,
    expected_split=(expected_c, expected_t)
)

if srm['srm_detected']:
    st.error(
        f"SRM DETECTED — chi²={srm['chi2_stat']}, p={srm['p_value']}. "
        f"Randomisation is broken. Do not proceed to Z-test."
    )
else:
    st.success(
        f"SRM PASSED — chi²={srm['chi2_stat']}, p={srm['p_value']}. "
        f"Group split matches intended design."
    )

st.divider()

#Z-Test
st.subheader("Stage 3: Two-Sample Proportion Z-Test")
st.caption(
    "Pooled SE for Z-statistic (assumes H₀: p_control = p_treatment). "
    "Unpooled SE for confidence interval (estimates true difference). "
    "These are not interchangeable."
)

if srm['srm_detected']:
    st.warning(
        "Z-test blocked. Resolve the SRM before proceeding."
    )
else:
    result = run_ztest(
        n_c=n_c, x_c=x_c,
        n_t=n_t, x_t=x_t,
        alpha=alpha
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Control Rate",   f"{result['p_control']:.3%}")
    col2.metric("Treatment Rate", f"{result['p_treatment']:.3%}")
    col3.metric("Absolute Lift",  f"{result['absolute_lift']:+.3%}")
    col4.metric("Relative Lift",  f"{result['relative_lift_pct']:+.1f}%")

    col1, col2, col3 = st.columns(3)
    col1.metric("Z-Statistic", f"{result['z_stat']:.4f}")
    col2.metric("P-Value",     f"{result['p_value']:.6f}")
    col3.metric("95% CI",
        f"[{result['ci_95'][0]:+.3%}, {result['ci_95'][1]:+.3%}]")

    st.divider()

    #Decision 
    st.subheader("Decision")

    sample_adequate = min(n_c, n_t) >= power_result['n_per_group']

    if not sample_adequate:
        st.warning(
            f"INCONCLUSIVE — Sample below requirement. "
            f"Need {power_result['n_per_group']:,} per group, "
            f"have {int(min(n_c, n_t)):,}. Continue running."
        )
    elif result['significant'] and result['absolute_lift'] > 0:
        st.success(
            f"SHIP — Significant positive lift of "
            f"{result['absolute_lift']:+.3%} "
            f"({result['relative_lift_pct']:+.1f}% relative). "
            f"Safe to roll out to 100% of users."
        )
    elif result['significant'] and result['absolute_lift'] < 0:
        st.error(
            f"ABORT — Treatment significantly worse than control "
            f"({result['absolute_lift']:+.3%}). Roll back immediately."
        )
    else:
        st.warning(
            f"INCONCLUSIVE — P-value {result['p_value']:.4f} does not "
            f"meet significance threshold of {alpha}. "
            f"No reliable difference detected between cohorts."
        )

    with st.expander("Methodology"):
        st.markdown(f"""
        - Pooled SE used for Z-statistic: assumes H₀ that both groups
          share one true conversion rate
        - Unpooled SE used for 95% CI: estimates the true difference
          without imposing H₀
        - Two-tailed test at α={alpha}
        - SRM detection uses chi-square against actual design proportions
          ({expected_c:.3f} / {expected_t:.3f}), not hardcoded 50/50
        - Design: quasi-experimental signup-date split. Results describe
          association only, not causation.
        """)