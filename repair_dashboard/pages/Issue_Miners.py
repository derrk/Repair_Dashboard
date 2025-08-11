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

# === ADD: queue paths & helpers ===
GV_QUEUE_FILE = DATA_DIR / "gv_repairs_queue.csv"
BM_QUEUE_FILE = DATA_DIR / "bitmain_repairs_queue.csv"

# columns shared across Issues/queues
CORE_COLS = ["ip", "serial", "issue", "end_date", "days_left"]
QUEUE_EXTRA = ["assigned_to", "assigned_at", "notes"]
ALL_QUEUE_COLS = CORE_COLS + QUEUE_EXTRA

def _ensure_queue(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        pd.DataFrame(columns=ALL_QUEUE_COLS).to_csv(path, index=False)

def load_queue(path: Path) -> pd.DataFrame:
    _ensure_queue(path)
    return pd.read_csv(path)

def save_queue(dfq: pd.DataFrame, path: Path):
    dfq.to_csv(path, index=False)

def dedupe_on(dfq: pd.DataFrame, keys=("serial", "ip")) -> pd.DataFrame:
    return dfq.drop_duplicates(subset=list(keys), keep="last")


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

# ------------ Render (REPLACED) ------------
st.write(f"**{dataset_label}** — Showing **{len(df)}** miners")

# selection + optional metadata
df_view = df.copy()
if "select" not in df_view.columns:
    df_view.insert(0, "select", False)

assignee = st.text_input("Assigned to (optional)", value="")
notes = st.text_input("Notes (optional)", value="")
remove_after_move = st.checkbox("Remove from Issues after moving", value=True)

edited = st.data_editor(
    df_view,
    use_container_width=True,
    hide_index=True,
    key="issues_editor",
    column_config={
        "select": st.column_config.CheckboxColumn("Select", help="Select miners to move"),
    },
)

col_a, col_b, col_sp = st.columns([1,1,2])
move_gv = col_a.button("➡️ Move to Great Voyage Repairs", use_container_width=True)
move_bm = col_b.button("➡️ Move to Bitmain Repairs", use_container_width=True)

# read queues
gv_queue = load_queue(GV_QUEUE_FILE)
bm_queue = load_queue(BM_QUEUE_FILE)

def move_selected(target: str):
    picked = edited[edited["select"] == True].drop(columns=["select"], errors="ignore")
    if picked.empty:
        st.warning("No rows selected.")
        return

    # normalize columns for queues
    picked = picked.reindex(columns=ALL_QUEUE_COLS, fill_value="")
    picked["assigned_to"] = assignee
    picked["notes"] = notes
    picked["assigned_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if target == "gv":
        q = dedupe_on(pd.concat([gv_queue, picked], ignore_index=True))
        save_queue(q, GV_QUEUE_FILE)
        st.success(f"Moved {len(picked)} miner(s) to Great Voyage Repairs.")
    else:
        q = dedupe_on(pd.concat([bm_queue, picked], ignore_index=True))
        save_queue(q, BM_QUEUE_FILE)
        st.success(f"Moved {len(picked)} miner(s) to Bitmain Repairs.")

    # optionally remove from Issues CSV (treat as MOVE)
    if remove_after_move:
        keys = set(zip(picked["serial"].astype(str), picked["ip"].astype(str)))
        remaining = df[~df.apply(lambda r: (str(r["serial"]), str(r["ip"])) in keys, axis=1)]
        remaining.to_csv(CSV_FILE, index=False)
        st.cache_data.clear()  # refresh load_data next run

# buttons
if move_gv:
    move_selected("gv")
if move_bm:
    move_selected("bm")

# download filtered view (optional)
st.download_button(
    "📥 Download Filtered CSV",
    df.to_csv(index=False).encode("utf-8"),
    f"{dataset_label.replace(' ', '_').lower()}_filtered.csv",
    "text/csv",
)

# ============================
# Queues: move back / cross-move
# ============================

gv_now = load_queue(GV_QUEUE_FILE)
bm_now = load_queue(BM_QUEUE_FILE)

st.divider()
st.subheader("Great Voyage Repairs Queue (select to move)")
gv_view = gv_now.copy()
if "select" not in gv_view.columns:
    gv_view.insert(0, "select", False)
gv_edited = st.data_editor(
    gv_view,
    use_container_width=True,
    hide_index=True,
    key="gv_editor",
    column_config={"select": st.column_config.CheckboxColumn("Select")},
)

col_gv1, col_gv2 = st.columns(2)
gv_to_issues = col_gv1.button("⬅️ Move selected back to Issues", use_container_width=True, key="btn_gv_to_issues")
gv_to_bitmain = col_gv2.button("➡️ Move selected to Bitmain", use_container_width=True, key="btn_gv_to_bm")

st.subheader("Bitmain Repairs Queue (select to move)")
bm_view = bm_now.copy()
if "select" not in bm_view.columns:
    bm_view.insert(0, "select", False)
bm_edited = st.data_editor(
    bm_view,
    use_container_width=True,
    hide_index=True,
    key="bm_editor",
    column_config={"select": st.column_config.CheckboxColumn("Select")},
)

col_bm1, col_bm2 = st.columns(2)
bm_to_issues = col_bm1.button("⬅️ Move selected back to Issues", use_container_width=True, key="btn_bm_to_issues")
bm_to_gv = col_bm2.button("➡️ Move selected to Great Voyage", use_container_width=True, key="btn_bm_to_gv")

remove_on_transfer = st.checkbox(
    "Remove from source when transferring (MOVE instead of COPY)",
    value=True,
    help="If unchecked, rows are copied to the destination but kept in the source."
)

def _norm_cols(df_in: pd.DataFrame):
    return df_in.reindex(columns=ALL_QUEUE_COLS, fill_value="")

def _remove_from_df(df_src: pd.DataFrame, picked: pd.DataFrame):
    keys = set(zip(picked["serial"].astype(str), picked["ip"].astype(str)))
    return df_src[~df_src.apply(lambda r: (str(r["serial"]), str(r["ip"])) in keys, axis=1)]

def _append_to_issues(picked_min: pd.DataFrame):
    # drop queue-only fields before writing back to Issues
    to_write = picked_min.drop(columns=QUEUE_EXTRA, errors="ignore")
    try:
        src_all = pd.read_csv(CSV_FILE)
    except FileNotFoundError:
        src_all = pd.DataFrame(columns=to_write.columns)
    merged = dedupe_on(pd.concat([src_all, to_write], ignore_index=True))
    merged.to_csv(CSV_FILE, index=False)
    st.success(f"Moved {len(to_write)} miner(s) back to Issues.")
    st.cache_data.clear()

# GV -> (Issues | Bitmain)
if gv_to_issues or gv_to_bitmain:
    gv_sel = gv_edited[gv_edited["select"] == True].drop(columns=["select"], errors="ignore")
    if gv_sel.empty:
        st.warning("No rows selected in Great Voyage queue.")
    else:
        if gv_to_issues:
            _append_to_issues(gv_sel)
        else:
            bm_now = load_queue(BM_QUEUE_FILE)
            bm_now = dedupe_on(pd.concat([bm_now, _norm_cols(gv_sel)], ignore_index=True))
            save_queue(bm_now, BM_QUEUE_FILE)
            st.success(f"Moved {len(gv_sel)} miner(s) to Bitmain queue.")
        if remove_on_transfer:
            gv_now = _remove_from_df(gv_now, gv_sel)
            save_queue(gv_now, GV_QUEUE_FILE)

# BM -> (Issues | Great Voyage)
if bm_to_issues or bm_to_gv:
    bm_sel = bm_edited[bm_edited["select"] == True].drop(columns=["select"], errors="ignore")
    if bm_sel.empty:
        st.warning("No rows selected in Bitmain queue.")
    else:
        if bm_to_issues:
            _append_to_issues(bm_sel)
        else:
            gv_now = load_queue(GV_QUEUE_FILE)
            gv_now = dedupe_on(pd.concat([gv_now, _norm_cols(bm_sel)], ignore_index=True))
            save_queue(gv_now, GV_QUEUE_FILE)
            st.success(f"Moved {len(bm_sel)} miner(s) to Great Voyage queue.")
        if remove_on_transfer:
            bm_now = _remove_from_df(bm_now, bm_sel)
            save_queue(bm_now, BM_QUEUE_FILE)



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
