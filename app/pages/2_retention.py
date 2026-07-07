# app/pages/2_retention.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from app.bq_app_client import get_client, run_query
from src.sql_loader import load_sql

st.title("Retention Analytics")
st.markdown("**Business Question:** Are we keeping the customers we acquire?")

client = get_client()

with st.spinner("Loading cohort data..."):
    df_cohort = run_query(client, load_sql('cohort_retention.sql'))

with st.spinner("Loading revenue data..."):
    df_revenue = run_query(client, load_sql('monthly_revenue.sql'))

for col, m in zip(['m1_rate','m2_rate','m3_rate','m6_rate'],
                  ['m1','m2','m3','m6']):
    df_cohort[col] = (df_cohort[m] / df_cohort['m0'] * 100).round(1)

df_cohort['cohort_label'] = df_cohort['cohort_month'].astype(str).str[:7]
df_revenue['month']        = pd.to_datetime(df_revenue['month'])

avg_m1     = df_cohort['m1_rate'].mean()
avg_m3     = df_cohort['m3_rate'].mean()
latest_mom = df_revenue['mom_growth_pct'].dropna().iloc[-1]

col1, col2, col3 = st.columns(3)
col1.metric("Avg Month-1 Retention", f"{avg_m1:.1f}%")
col2.metric("Avg Month-3 Retention", f"{avg_m3:.1f}%")
col3.metric("Latest MoM Growth",     f"{latest_mom:.1f}%")

st.divider()

fig_heat = px.imshow(
    df_cohort[['m1_rate','m2_rate','m3_rate','m6_rate']].values,
    labels=dict(x="Period", y="Cohort", color="Retention %"),
    x=['Month 1','Month 2','Month 3','Month 6'],
    y=df_cohort['cohort_label'].tolist(),
    color_continuous_scale='Blues',
    title='Cohort Retention Rate by Acquisition Month (%)'
)
fig_heat.update_layout(height=600)
st.plotly_chart(fig_heat, use_container_width=True)

st.divider()

fig_rev = go.Figure()
fig_rev.add_trace(go.Bar(
    x=df_revenue['month'],
    y=df_revenue['revenue'],
    name='Monthly Revenue',
    marker_color='steelblue',
    opacity=0.7
))
fig_rev.add_trace(go.Scatter(
    x=df_revenue['month'],
    y=df_revenue['mom_growth_pct'],
    name='MoM Growth %',
    yaxis='y2',
    line=dict(color='orange', width=2),
    mode='lines+markers'
))
fig_rev.update_layout(
    title='Monthly Revenue and MoM Growth Rate',
    yaxis=dict(title='Revenue ($)'),
    yaxis2=dict(
        title='MoM Growth %',
        overlaying='y',
        side='right',
        zeroline=True,
        zerolinecolor='red'
    ),
    legend=dict(x=0, y=1.1, orientation='h'),
    height=450
)
st.plotly_chart(fig_rev, use_container_width=True)

st.divider()

st.subheader("Diagnosis")
st.warning(
    f"Average Month-1 retention of {avg_m1:.1f}% indicates near-zero repeat "
    f"purchase behavior. The business is acquisition-dependent — revenue growth "
    f"is driven entirely by new customer volume, not loyalty. Structural "
    f"recommendation: invest in post-purchase retention mechanics before "
    f"scaling paid acquisition."
)