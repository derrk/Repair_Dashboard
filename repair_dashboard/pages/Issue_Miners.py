import pandas as pd
import streamlit as st
import ipaddress
from datetime import datetime 

CSV_FILE = r"C:\Users\DerrikPollock\OneDrive - Iris Energy\Desktop\Projects\Python\repair_dashboard\data\Block 2 Issue Miners.csv"  # update path if needed  # your file with columns: Miner IP, serial, issue, days left of warranty, warranty expiration date

# ---- Load data (cached) ----
@st.cache_data
def load_data():
    df = pd.read_csv(CSV_FILE)

    EXP_COL = "end_date"  # change if needed

    # 1) Parse to datetime (keep as datetime64 for math)
    df[EXP_COL] = pd.to_datetime(df[EXP_COL], errors="coerce")

    # 2) Calculate days_left dynamically
    today = pd.Timestamp("today").normalize()
    days = (df[EXP_COL] - today).dt.days
    df["days_left"] = days.clip(lower=0).fillna(0).astype(int)

    # 3) Convert to date for display (removes time portion)
    df[EXP_COL] = df[EXP_COL].dt.date

    return df



df = load_data()



# ---- Issue filter (prefix-based) ----
issue_filters = {
    "All Issues": "",
    "Hashboard (J)": "J",
    "Overheat (P)": "P",
    "Fan (F)": "F",
    "Network (N)": "N",
}

st.title("⚙️ Issue Miners")

issue_choice = st.radio("Filter by Issue Type", list(issue_filters.keys()))
issue_prefix = issue_filters[issue_choice]

if issue_prefix:
    df = df[df["issue"].astype(str).str.startswith(issue_prefix, na=False)]

# ---- Building ranges (CIDR) ----
BUILDING_NETWORKS = {
    "DC 21": ipaddress.ip_network("10.211.0.0/19"),  # 10.211.0.0 - 10.211.31.255
    # Add more buildings as you define them:
    "DC 22": ipaddress.ip_network("10.212.0.0/19"),
    "DC 23": ipaddress.ip_network("10.213.0.0/19"),
    "DC 24": ipaddress.ip_network("10.214.0.0/19")
}

building_options = ["All Buildings"] + list(BUILDING_NETWORKS.keys())
b_choice = st.selectbox("Filter by Building (IP range)", building_options)

def ip_in_building(ip_str: str, network: ipaddress._BaseNetwork) -> bool:
    try:
        return ipaddress.ip_address(ip_str.strip()) in network
    except Exception:
        return False

if b_choice != "All Buildings":
    net = BUILDING_NETWORKS[b_choice]
    df = df[df["ip"].astype(str).apply(lambda x: ip_in_building(x, net))]

# assumes df already has an int 'days_left' column from load_data()
in_warranty_only = st.checkbox("Hide Out of Warranty Miners", value=False)

if in_warranty_only:
    df = df[df["days_left"] > 0]


st.write(f"Showing **{len(df)}** miners")
st.dataframe(df, use_container_width=True)

# Optional: download filtered results
st.download_button(
    "📥 Download Filtered CSV",
    df.to_csv(index=False).encode("utf-8"),
    "filtered_miners.csv",
    "text/csv",
)



