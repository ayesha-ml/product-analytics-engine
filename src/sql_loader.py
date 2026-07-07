# src/sql_loader.py
import os

def load_sql(filename: str) -> str:
    """Load a SQL file from src/queries/"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, 'src', 'queries', filename)
    with open(path, 'r') as f:
        return f.read()