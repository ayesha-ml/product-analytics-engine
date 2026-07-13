import streamlit as st
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.engine.power_analysis import compute_sample_size
from src.engine.srm_check import detect_srm
from src.engine.ztest import run_ztest
from app.bq_app_client import get_client, run_query
from src.sql_loader import load_sql

# Set page config to wide mode to maximize screen space for metrics and charts
st.set_page_config(layout="wide")

st.title("Experimentation Engine")
st.markdown(
    "**Business Question:** Did our product change drive a measurable "
    "improvement in purchase conversion rate?"
)
st.markdown(
    "Three-stage frequentist pipeline: "
    "**Stage 1: Power Analysis &nbsp;|&nbsp; Stage 2: SRM Check &nbsp;|&nbsp; Stage 3: Z-Test & Decision**"
)

# ---------------------------------------------------------------------
# STAGE 1: POWER ANALYSIS
# ---------------------------------------------------------------------
with st.container(border=True):
    st.subheader("Stage 1: Pre-Test Power Analysis")
    st.caption(
        "Determines minimum sample size before an experiment launches. "
        "Running this after peeking at results invalidates the analysis."
    )
    st.write("") # Spacer

    col1, col2, col3, col4 = st.columns(4)
    p0 = col1.number_input("Baseline Rate", value=0.5306,
                           step=0.01, min_value=0.01, max_value=0.99)
    mde = col2.number_input("Min Detectable Effect", value=0.02,
                            step=0.005, min_value=0.001)
    alpha = col3.number_input("Alpha", value=0.05,
                              step=0.01, min_value=0.01, max_value=0.20)
    power = col4.number_input("Power", value=0.80,
                              step=0.05, min_value=0.50, max_value=0.99)

    power_result = compute_sample_size(p0=p0, mde=mde, alpha=alpha, power=power)

    st.write("") # Spacer
    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric("Required Per Group", f"{power_result['n_per_group']:,}")
    m_col2.metric("Total Required", f"{power_result['n_total']:,}")
    m_col3.metric("Effect Size (h)", f"{abs(power_result['effect_size_h']):.4f}")


# ---------------------------------------------------------------------
# STAGE 2: SRM CHECK
# ---------------------------------------------------------------------
with st.container(border=True):
    st.subheader("Stage 2: Sample Ratio Mismatch Check")
    st.caption("Validates that observed group sizes match the expected distribution.")
    st.write("") # Spacer

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
        with col1:
            st.markdown("**Control Group**")
            n_c = st.number_input("Control Users", value=51724, step=100)
            x_c = st.number_input("Control Conversions", value=27445, step=100)
        with col2:
            st.markdown("**Treatment Group**")
            n_t = st.number_input("Treatment Users", value=48276, step=100)
            x_t = st.number_input("Treatment Conversions", value=25511, step=100)

    total      = n_c + n_t
    expected_c = n_c / total
    expected_t = n_t / total

    srm = detect_srm(
        n_control=n_c,
        n_treatment=n_t,
        expected_split=(expected_c, expected_t)
    )

    st.write("") # Spacer
    if srm['srm_detected']:
        st.error(
            f"SRM DETECTED — chi²={srm['chi2_stat']}, p={srm['p_value']}. "
            f"Randomisation is broken. Do not proceed to Z-test."
        )
    else:
        st.success(
            f"SRM PASSED — chi²={srm['chi2_stat']:.4f}, p={srm['p_value']:.4f}. "
            f"Group split matches intended design."
        )


# ---------------------------------------------------------------------
# STAGE 3: Z-TEST & DECISION
# ---------------------------------------------------------------------
with st.container(border=True):
    st.subheader("Stage 3: Two-Sample Proportion Z-Test")
    st.caption(
        "Pooled SE for Z-statistic (assumes H₀: p_control = p_treatment). "
        "Unpooled SE for confidence interval (estimates true difference)."
    )
    st.write("") # Spacer

    if srm['srm_detected']:
        st.warning("Z-test blocked. Resolve the SRM before proceeding.")
    else:
        result = run_ztest(
            n_c=n_c, x_c=x_c,
            n_t=n_t, x_t=x_t,
            alpha=alpha
        )

        res_col1, res_col2, res_col3, res_col4 = st.columns(4)
        res_col1.metric("Control Rate", f"{result['p_control']:.3%}")
        res_col2.metric("Treatment Rate", f"{result['p_treatment']:.3%}")
        res_col3.metric("Absolute Lift", f"{result['absolute_lift']:+.3%}")
        res_col4.metric("Relative Lift", f"{result['relative_lift_pct']:+.1f}%")

        st.write("") # Spacer
        stat_col1, stat_col2, stat_col3 = st.columns(3)
        stat_col1.metric("Z-Statistic", f"{result['z_stat']:.4f}")
        stat_col2.metric("P-Value", f"{result['p_value']:.6f}")
        stat_col3.metric("95% Confidence Interval", f"[{result['ci_95'][0]:+.3%}, {result['ci_95'][1]:+.3%}]")

        st.write("") # Spacer
        st.markdown("### Decision")

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

    st.write("") # Spacer
    with st.expander("Methodology Notes"):
        st.markdown(f"""
        - **Pooled SE** used for Z-statistic: assumes $H_0$ that both groups share one true conversion rate
        - **Unpooled SE** used for 95% CI: estimates the true difference without imposing $H_0$
        - Two-tailed test at $\\alpha={alpha}$
        - **SRM detection** uses chi-square against actual design proportions ({expected_c:.3f} / {expected_t:.3f}), not hardcoded 50/50
        - **Design:** quasi-experimental signup-date split. Results describe association only, not causation.
        """)