# app/bq_app_client.py
import streamlit as st
import pydata_google_auth
from google.cloud import bigquery

@st.cache_resource
def get_client():
    credentials = pydata_google_auth.get_user_credentials(
        scopes=["https://www.googleapis.com/auth/bigquery"],
    )
    return bigquery.Client(
        project="thelook-analytics-engine",
        credentials=credentials
    )

@st.cache_data(ttl=3600)
def run_query(_client, sql: str):
    df = _client.query(sql).to_dataframe()
    df.columns = df.columns.str.lower()
    return df