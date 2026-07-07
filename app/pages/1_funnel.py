# app/pages/1_funnel.py
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from app.bq_app_client import get_client, run_query
from src.sql_loader import load_sql

st.title("Funnel Analysis")
st.markdown("**Business Question:** Where are we losing users in the purchase journey?")

client = get_client()

with st.spinner("Loading funnel data..."):
    df_funnel = run_query(client, load_sql('clickstream_funnel_leakage.sql'))

total = len(df_funnel)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Sessions", f"{total:,}")
col2.metric("Reached Cart",
    f"{df_funnel['reached_cart'].mean()*100:.1f}%")
col3.metric("Completed Purchase",
    f"{df_funnel['reached_purchase'].mean()*100:.1f}%")
col4.metric("Cart to Purchase Rate",
    f"{df_funnel['reached_purchase'].sum()/max(df_funnel['reached_cart'].sum(),1)*100:.1f}%")

st.divider()

stages = ['reached_home','reached_department','reached_product',
          'reached_cart','reached_purchase']
labels = ['Home','Department','Product','Cart','Purchase']
counts = [int(df_funnel[s].sum()) for s in stages]

fig_funnel = go.Figure(go.Funnel(
    y=labels,
    x=counts,
    textinfo="value+percent initial",
    marker=dict(color=['#1f4e79','#2e75b6','#4472c4','#70ad47','#ed7d31'])
))
fig_funnel.update_layout(
    title="Conversion Funnel — Sessions by Stage",
    height=450
)
st.plotly_chart(fig_funnel, use_container_width=True)

st.divider()

abandon_counts = df_funnel['abandonment_stage'].value_counts().reset_index()
abandon_counts.columns = ['stage','count']
abandon_counts['pct'] = (abandon_counts['count'] / total * 100).round(1)

fig_bar = px.bar(
    abandon_counts,
    x='stage', y='pct',
    text='pct',
    title='Session Abandonment Distribution (%)',
    color='stage',
    color_discrete_sequence=px.colors.qualitative.Set2
)
fig_bar.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
fig_bar.update_layout(showlegend=False, yaxis_title='% of Sessions', xaxis_title='')
st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

purchase_pct     = df_funnel['reached_purchase'].mean() * 100
cart_pct         = df_funnel['reached_cart'].mean() * 100
cart_to_purchase = df_funnel['reached_purchase'].sum() / max(df_funnel['reached_cart'].sum(), 1) * 100

st.subheader("Diagnosis")
st.info(
    f"{purchase_pct:.1f}% of sessions result in a completed purchase. "
    f"{cart_pct:.1f}% reach the cart, but only {cart_to_purchase:.1f}% of those "
    f"convert — meaning {100-cart_to_purchase:.1f}% of high-intent cart sessions "
    f"are lost before purchase completes. Primary growth lever: improve checkout "
    f"conversion before scaling acquisition spend."
)