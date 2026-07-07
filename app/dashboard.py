# app/dashboard.py
import streamlit as st

st.set_page_config(
    page_title="TheLook Analytics",
    layout="wide"
)

st.title("Product Analytics & Experimentation Engine")
st.markdown("""
Built on Google BigQuery TheLook eCommerce public dataset.
Navigate using the sidebar to explore each analytical module.

| Page | Module | Business Question |
|---|---|---|
| Funnel | Clickstream Analytics | Where are users dropping off? |
| Retention | Cohort Analytics | Are we keeping our customers? |
""")