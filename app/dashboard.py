import streamlit as st

st.set_page_config(
    page_title="Product Analytics & Experimentation Engine",
    layout="wide"
)

st.title("Product Analytics & Experimentation Engine")
st.markdown("##### Built on Google BigQuery · TheLook eCommerce Public Dataset")

st.divider()

st.markdown("""
This platform demonstrates the core analytical workflow of a growth
data scientist — from raw clickstream events to statistical inference
to ML-driven customer prioritisation. All analysis runs live against
Google BigQuery.
""")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Funnel Analysis")
    st.markdown("""
    **Business question:** Where are users dropping off in the purchase journey?

    Aggregates 2.4M raw clickstream events into session-level funnel
    milestones using SQL window functions. Identifies the two primary
    leakage points driving lost revenue.
    """)

    st.subheader("Retention Analytics")
    st.markdown("""
    **Business question:** Are we keeping the customers we acquire?

    Builds a monthly cohort retention matrix across 91 acquisition cohorts
    using DATE_DIFF and ROW_NUMBER. Pairs with MoM revenue trend analysis
    using LAG() to separate seasonal patterns from structural churn.
    """)

with col2:
    st.subheader("Experimentation Engine")
    st.markdown("""
    **Business question:** Did our product change drive a measurable improvement?

    Three-stage frequentist pipeline: power analysis, SRM detection via
    chi-square, and a two-sample Z-test with correct pooled/unpooled
    standard error handling. Outputs a SHIP / ABORT / INCONCLUSIVE decision.
    """)

    st.subheader("Customer Segmentation")
    st.markdown("""
    **Business question:** Which customers are worth investing in?

    RFM scoring via NTILE quintiles in BigQuery, scaled with RobustScaler
    to handle monetary outliers, clustered with K-Means into four
    actionable segments with revenue-weighted action recommendations.
    """)

st.divider()

st.markdown("""
| Module | Primary Technique | Key Finding |
|---|---|---|
| Funnel | Session-grain funnel aggregation | 36.6% cart abandonment, 36.7% checkout drop-off |
| Retention | Monthly cohort matrix | 2.5% avg M1 retention — acquisition-dependent growth |
| Experimentation | Pooled Z-test + SRM detection | INCONCLUSIVE — p=0.493, genuine null at 5x required n |
| Segmentation | RobustScaler + K-Means (K=4) | 2,222 At Risk customers hold $1.1M revenue at stake |
""")