# app.py
import streamlit as st
from modules import victoria_api, excel_io, logic

st.set_page_config(page_title="Miner Repair Dashboard", layout="wide")
st.title("🔧 Miner Repair Dashboard")

# Load data
with st.spinner("Loading data from VictoriaMetrics and Excel..."):
    miner_info = victoria_api.get_miner_info()
    warranty_df = excel_io.load_warranty_inventory()
    repair_backlog_df = logic.get_repair_backlog(miner_info, warranty_df)

# Tabs
tabs = st.tabs(["Backlog Overview", "Log a Repair", "Parts Inventory", "Projections"])

# Tab 1: Backlog Overview
with tabs[0]:
    st.subheader("Repair Backlog Overview")
    logic.display_backlog_summary(repair_backlog_df)

# Tab 2: Log a Repair
with tabs[1]:
    st.subheader("Log a New Repair")
    logic.display_repair_form(warranty_df)

# Tab 3: Parts Inventory
with tabs[2]:
    st.subheader("Parts Usage and Inventory")
    logic.display_parts_inventory(warranty_df)

# Tab 4: Projections
with tabs[3]:
    st.subheader("Repair Rate Projections")
    logic.display_projections(repair_backlog_df, warranty_df)
