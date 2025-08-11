from pathlib import Path
import pandas as pd
import streamlit as st
import ipaddress
from datetime import datetime

# ---- Path setup (fixed) ----
BASE_DIR = Path(__file__).resolve().parent          # repair_dashboard/pages
PROJECT_ROOT = BASE_DIR.parent                      # repair_dashboard
DATA_DIR = PROJECT_ROOT / "data"                    # repair_dashboard/data

DATASETS = {
    "Block 2 Issues": DATA_DIR / "Block_2_Issue_Miners.csv",
    "Block 3 Issues": DATA_DIR / "Block_3_Issue_Miners.csv",
}

st.title("⚙️ Issue Miners")

dataset_label = st.selectbox("Select dataset (CSV)", list(DATASETS.keys()))
CSV_FILE = DATASETS[dataset_label]

# Optional: quick sanity check (remove later)
# st.write("Looking for:", CSV_FILE)
# st.write("Exists?", CSV_FILE.exists())

@st.cache_data
def load_data(csv_path: Path):
    df = pd.read_csv(csv_path)

    EXP_COL = "end_date"
    df[EXP_COL] = pd.to_datetime(df[EXP_COL], errors="coerce")

    today = pd.Timestamp("today").normalize()
    days = (df[EXP_COL] - today).dt.days
    df["days_left"] = days.clip(lower=0).fillna(0).astype(int)

    df[EXP_COL] = df[EXP_COL].dt.date
    return df

df = load_data(CSV_FILE)


# ------------ Issue filter ------------
issue_filters = {
    "All Issues": "",
    "Hashboard (J)": "J",
    "Overheat (P)": "P",
    "Fan (F)": "F",
    "Network (N)": "N",
}
issue_choice = st.radio("Filter by Issue Type", list(issue_filters.keys()), horizontal=True)
issue_prefix = issue_filters[issue_choice]
if issue_prefix:
    df = df[df["issue"].astype(str).str.startswith(issue_prefix, na=False)]

# ------------ Building filter (CIDR) ------------
BUILDING_NETWORKS = {
    "DC 21": ipaddress.ip_network("10.211.0.0/19"),
    "DC 22": ipaddress.ip_network("10.212.0.0/19"),
    "DC 23": ipaddress.ip_network("10.213.0.0/19"),
    "DC 24": ipaddress.ip_network("10.214.0.0/19"),
}
b_choice = st.selectbox("Filter by Building (IP range)", ["All Buildings"] + list(BUILDING_NETWORKS.keys()))

def ip_in_building(ip_str: str, network: ipaddress._BaseNetwork) -> bool:
    try:
        return ipaddress.ip_address(ip_str.strip()) in network
    except Exception:
        return False

if b_choice != "All Buildings":
    net = BUILDING_NETWORKS[b_choice]
    df = df[df["ip"].astype(str).apply(lambda x: ip_in_building(x, net))]

# ------------ Warranty toggles ------------
in_warranty_only = st.checkbox("Hide Out of Warranty Miners", value=False)
if in_warranty_only:
    df = df[df["days_left"] > 0]

# ------------ Render ------------
st.write(f"**{dataset_label}** — Showing **{len(df)}** miners")
st.dataframe(df, use_container_width=True)

st.download_button(
    "📥 Download Filtered CSV",
    df.to_csv(index=False).encode("utf-8"),
    f"{dataset_label.replace(' ', '_').lower()}_filtered.csv",
    "text/csv",
)


# import pandas as pd
# import streamlit as st
# import ipaddress
# from datetime import datetime
# from pathlib import Path
# import glob

# # ------------ Config ------------
# DATA_DIR = Path("repair_dashboard/data")
# # Map nice labels to file globs (or hardcode exact files if you prefer)
# DATASETS = {
#     "Block 2 Issues": DATA_DIR / "Block 2 Issue Miners.csv",
#     "Block 3 Issues": DATA_DIR / "Block 3 Issue Miners.csv",  # add more as you create them
# }

# st.title("⚙️ Issue Miners")

# # ------------ File picker ------------
# # If you’d rather auto-discover, you can do: files = sorted(glob.glob(str(DATA_DIR / "*Issue*.csv")))
# dataset_label = st.selectbox("Select dataset (CSV)", list(DATASETS.keys()))
# CSV_FILE = str(DATASETS[dataset_label])

# # ------------ Load data ------------
# @st.cache_data
# def load_data(csv_path: str):
#     df = pd.read_csv(csv_path)

#     EXP_COL = "end_date"          # make sure this matches your column name
#     IP_COL  = "ip"                # adjust if needed
#     ISSUE_COL = "issue"           # adjust if needed

#     # Parse date for math, then compute days_left
#     df[EXP_COL] = pd.to_datetime(df[EXP_COL], errors="coerce")
#     today = pd.Timestamp("today").normalize()
#     days = (df[EXP_COL] - today).dt.days
#     df["days_left"] = days.clip(lower=0).fillna(0).astype(int)

#     # Strip time for display
#     df[EXP_COL] = df[EXP_COL].dt.date

#     # Standardize expected columns (optional: rename to consistent casing)
#     return df

# df = load_data(CSV_FILE)

# # ------------ Issue filter ------------
# issue_filters = {
#     "All Issues": "",
#     "Hashboard (J)": "J",
#     "Overheat (P)": "P",
#     "Fan (F)": "F",
#     "Network (N)": "N",
# }
# issue_choice = st.radio("Filter by Issue Type", list(issue_filters.keys()), horizontal=True)
# issue_prefix = issue_filters[issue_choice]
# if issue_prefix:
#     df = df[df["issue"].astype(str).str.startswith(issue_prefix, na=False)]

# # ------------ Building filter (CIDR) ------------
# BUILDING_NETWORKS = {
#     "DC 21": ipaddress.ip_network("10.211.0.0/19"),
#     "DC 22": ipaddress.ip_network("10.212.0.0/19"),
#     "DC 23": ipaddress.ip_network("10.213.0.0/19"),
#     "DC 24": ipaddress.ip_network("10.214.0.0/19"),
# }
# b_choice = st.selectbox("Filter by Building (IP range)", ["All Buildings"] + list(BUILDING_NETWORKS.keys()))

# def ip_in_building(ip_str: str, network: ipaddress._BaseNetwork) -> bool:
#     try:
#         return ipaddress.ip_address(ip_str.strip()) in network
#     except Exception:
#         return False

# if b_choice != "All Buildings":
#     net = BUILDING_NETWORKS[b_choice]
#     df = df[df["ip"].astype(str).apply(lambda x: ip_in_building(x, net))]

# # ------------ Warranty toggles ------------
# in_warranty_only = st.checkbox("Hide Out of Warranty Miners", value=False)
# if in_warranty_only:
#     df = df[df["days_left"] > 0]

# # ------------ Render ------------
# st.write(f"**{dataset_label}** — Showing **{len(df)}** miners")
# st.dataframe(df, use_container_width=True)

# st.download_button(
#     "📥 Download Filtered CSV",
#     df.to_csv(index=False).encode("utf-8"),
#     f"{dataset_label.replace(' ', '_').lower()}_filtered.csv",
#     "text/csv",
# )
