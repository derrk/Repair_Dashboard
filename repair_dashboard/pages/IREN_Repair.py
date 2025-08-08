import streamlit as st
import pandas as pd
from datetime import date

# Init local repair log if none
LOG_FILE = "repair_log.csv"

def load_log():
    try:
        return pd.read_csv(LOG_FILE)
    except:
        return pd.DataFrame(columns=[
            "Date", "Serial", 
        ])